"""Intel synthesis — fetch from sources + ask the user's AI provider to
produce a tight, scannable industry briefing.

Public entrypoint: run_brief(db, brief, user_id) — persists an IntelBriefRun
row, returns the run dict. Safe to call from HTTP handlers OR Celery tasks.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ai.exceptions import NoAPIKeyError
from ai.jarvis_ai import JarvisAI
from ai.providers.base import AIMessage
from ai.tiers import estimate_cost
from models import IntelBrief, IntelBriefRun, TokenUsage

from .fetchers import fetch_hn, fetch_reddit

logger = logging.getLogger("jarvis.intel.synth")

MAX_ITEMS_PER_SOURCE = 20
MAX_OUTPUT_TOKENS = 1200


def _build_prompt(topic: str, items: list[dict], custom: str | None) -> str:
    """Build the synthesis prompt. Concise so we don't burn tokens."""
    if custom:
        # User-provided template — substitute {topic} + give them the items
        template = custom.replace("{topic}", topic).replace("{industry}", topic)
        items_str = _format_items(items)
        return f"{template}\n\n--- DATA ---\n{items_str}"

    items_str = _format_items(items)
    return (
        f"You are JARVIS. Produce a tight industry briefing about \"{topic}\" "
        f"based ONLY on the items below from Reddit + Hacker News. Format:\n"
        f"\n"
        f"## What's loud right now\n"
        f"3-5 bullets of trending threads or stories. Each: 1 line summary + source.\n"
        f"\n"
        f"## Who's getting attention\n"
        f"People, companies, or products mentioned more than once. Brief context.\n"
        f"\n"
        f"## Surprise / contrarian takes\n"
        f"Any thread that challenges conventional wisdom in this industry.\n"
        f"\n"
        f"## Action items for the boss\n"
        f"2-3 things they should consider doing this week based on this signal.\n"
        f"\n"
        f"Be terse. No filler. Cite each claim with [source]. If a section has "
        f"nothing real, write \"nothing notable\" rather than padding.\n"
        f"\n"
        f"--- DATA ---\n{items_str}"
    )


def _format_items(items: list[dict]) -> str:
    lines = []
    for i, it in enumerate(items[:60]):
        title = (it.get("title") or "").strip()[:200]
        src = it.get("source", "?")
        score = it.get("score", 0)
        comments = it.get("comments", 0)
        summary = (it.get("summary") or "").strip()[:300]
        bit = f"[{i+1}] ({src} · ↑{score} · {comments}c) {title}"
        if summary:
            bit += f"\n    {summary}"
        lines.append(bit)
    return "\n".join(lines) if lines else "(no items fetched)"


async def run_brief(db: Session, brief: IntelBrief, user_id: int) -> dict:
    """Execute a brief end-to-end. Records IntelBriefRun row + TokenUsage.

    Returns the serialized run dict so the caller can render it immediately.
    On AI failure, the run is marked status=failed with an error message
    (the brief itself is left intact for retry)."""
    run = IntelBriefRun(
        brief_id=brief.id,
        user_id=user_id,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    sources = brief.sources_json or {}
    items: list[dict] = []
    counts: dict[str, int] = {}

    # ── Fetch in parallel ────────────────────────────────────────────────
    tasks = []
    if sources.get("reddit"):
        for sub in sources["reddit"][:5]:
            tasks.append(("reddit", sub, fetch_reddit(sub, MAX_ITEMS_PER_SOURCE)))
    if sources.get("hn"):
        q = sources.get("hn_query") or brief.topic
        tasks.append(("hn", q, fetch_hn(q, MAX_ITEMS_PER_SOURCE)))

    if tasks:
        results = await asyncio.gather(*(t[2] for t in tasks), return_exceptions=True)
        for (kind, key, _), res in zip(tasks, results):
            if isinstance(res, list):
                items.extend(res)
                tag = f"{kind}:{key}"
                counts[tag] = counts.get(tag, 0) + len(res)

    if not items:
        run.status = "failed"
        run.error = "No items fetched from any source."
        run.finished_at = datetime.utcnow()
        db.commit()
        return _serialize_run(run)

    # Sort by score so the top items come first (LLM weights early tokens more)
    items.sort(key=lambda x: x.get("score", 0), reverse=True)
    items = items[:60]

    # ── Synthesize ───────────────────────────────────────────────────────
    try:
        ai = JarvisAI(db, user_id)
    except NoAPIKeyError as e:
        run.status = "failed"
        run.error = f"No {e.provider} API key configured. Add one in Settings → AI Keys."
        run.finished_at = datetime.utcnow()
        db.commit()
        return _serialize_run(run)

    prompt = _build_prompt(brief.topic, items, brief.prompt_template)

    try:
        resp = await ai.provider.complete(
            messages=[AIMessage(role="user", content=prompt)],
            system=(
                "You are JARVIS, the user's personal AI assistant. "
                "Produce concise, scannable industry briefings. Cite sources."
            ),
            tools=None,
            model=ai.model,
            max_tokens=MAX_OUTPUT_TOKENS,
            thinking_budget=None,
        )
    except Exception as ex:
        logger.exception("intel synth failed")
        run.status = "failed"
        run.error = str(ex)[:500]
        run.finished_at = datetime.utcnow()
        db.commit()
        return _serialize_run(run)

    cost = estimate_cost(
        provider=ai.provider_name,
        tier=ai.tier if ai.tier in ("eco", "intelligent", "scientist") else "intelligent",
        input_tokens=resp.input_tokens,
        output_tokens=resp.output_tokens,
    )

    # Record the model call in the standard usage ledger so it shows up
    # in /api/tokens/today right next to chat costs.
    db.add(TokenUsage(
        user_id=user_id,
        date=datetime.utcnow().date().isoformat(),
        provider=ai.provider_name,
        model=ai.model,
        input_tokens=resp.input_tokens,
        output_tokens=resp.output_tokens,
        cache_read_tokens=resp.cache_read_tokens,
        cache_write_tokens=resp.cache_write_tokens,
        cost_usd=cost,
    ))

    run.status = "done"
    run.output_text = resp.text or ""
    run.sources_summary = counts
    run.cost_usd = cost
    run.finished_at = datetime.utcnow()
    brief.last_run_at = datetime.utcnow()

    db.commit()
    db.refresh(run)
    return _serialize_run(run)


def _serialize_run(r: IntelBriefRun) -> dict:
    return {
        "id": r.id,
        "brief_id": r.brief_id,
        "status": r.status,
        "output_text": r.output_text,
        "sources_summary": r.sources_summary,
        "error": r.error,
        "cost_usd": r.cost_usd,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
    }
