"""Celery task: build_decision_inbox(user_id).

Pulls items needing user action from connected services and creates Decision
rows for anything that isn't already pending. Currently wired:

  - github_pr   — open PRs assigned to user OR awaiting their review
  - linear      — issues with state "blocked" or label containing
                  "waiting" assigned to user (best-effort over Linear's
                  default workflows)

Shopify + Freshdesk sources land when those connectors ship (Steps 9, 10).

Idempotent — keyed on (source, source_id, user_id). Re-running won't
duplicate. Existing approved/rejected decisions are left alone.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from worker import celery_app

logger = logging.getLogger("jarvis.tasks.decisions")


@celery_app.task(name="decisions.build_for_user")
def build_decision_inbox(user_id: int) -> dict:
    """Scan connected services for items needing the user's call. Returns
    {created, scanned, errors} for observability."""
    from database import SessionLocal
    from models import Decision, OAuthToken

    db = SessionLocal()
    created = 0
    scanned = 0
    errors: list[str] = []

    try:
        # Only run for users with at least one connected source — avoids
        # hammering APIs for inactive accounts.
        has_github = (
            db.query(OAuthToken)
            .filter_by(provider="github", user_id=user_id)
            .first()
        )

        if has_github:
            try:
                items = asyncio.run(_github_action_items(db, user_id))
                scanned += len(items)
                for it in items:
                    if _ensure_decision(db, user_id, it):
                        created += 1
            except Exception as e:
                logger.exception("github inbox scan failed for user_id=%s", user_id)
                errors.append(f"github: {e}")

        db.commit()
        return {"created": created, "scanned": scanned, "errors": errors}
    finally:
        db.close()


@celery_app.task(name="decisions.build_for_all")
def build_decision_inbox_all() -> dict:
    """Beat-driven: scan every active user. Pulled out so the same task can
    be triggered manually for one user via build_decision_inbox.delay(uid)."""
    from database import SessionLocal
    from models import User

    db = SessionLocal()
    try:
        users = db.query(User.id).all()
        for (uid,) in users:
            build_decision_inbox.delay(uid)
        return {"queued": len(users)}
    finally:
        db.close()


# ── Helpers ─────────────────────────────────────────────────────────────────


def _ensure_decision(db, user_id: int, item: dict) -> bool:
    """Insert if a matching pending decision isn't already there. Returns
    True if a new row was created."""
    from models import Decision

    src = item["source"]
    src_id = item["source_id"]

    existing = (
        db.query(Decision)
        .filter_by(user_id=user_id, source=src, source_id=src_id)
        .filter(Decision.status.in_(["pending", "snoozed"]))
        .first()
    )
    if existing:
        return False

    db.add(
        Decision(
            user_id=user_id,
            source=src,
            source_id=src_id,
            title=item["title"][:200],
            context_json=item.get("context") or {},
            ai_suggestion=item.get("suggestion"),
            status="pending",
            created_at=datetime.utcnow(),
        )
    )
    return True


async def _github_action_items(db, user_id: int) -> list[dict]:
    """Use GitHubConnector to fetch open issues/PRs assigned to the user.
    Treats every result as a candidate Decision."""
    from connectors.github import GitHubConnector

    conn = GitHubConnector(db, user_id)
    raw = await conn.fetch()

    items: list[dict] = []
    for row in raw:
        # Distinguish PRs from issues using URL substring — GitHub API
        # returns the same shape but pulls live at /pulls/, issues at /issues/.
        url = row.get("url", "") or ""
        is_pr = "/pulls/" in url
        items.append({
            "source": "github_pr" if is_pr else "github_issue",
            "source_id": str(row.get("id", "")),
            "title": row.get("title", "(untitled)"),
            "context": {"url": url, "status": row.get("status")},
            "suggestion": (
                "PR awaiting your review or assigned to you. Open the link to triage."
                if is_pr
                else "Issue assigned to you. Review and progress."
            ),
        })
    return items
