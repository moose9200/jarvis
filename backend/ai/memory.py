"""Per-user conversation memory + automatic compression.

Stores raw turns in `conversation_turns`, summaries in `conversation_summaries`.
When transcript grows beyond 2x WINDOW, the oldest excess turns are summarized
into a single ConversationSummary row via the cheapest model on the user's
chosen provider.
"""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from models import ConversationSummary, ConversationTurn, UserSettings

logger = logging.getLogger("jarvis.memory")

WINDOW = 20


class ConversationMemory:
    def __init__(self, db: Session, user_id: Optional[int] = None):
        self.db = db
        self.user_id = user_id

    def _q(self, model):
        q = self.db.query(model)
        if self.user_id is not None:
            q = q.filter_by(user_id=self.user_id)
        return q

    def append(self, role: str, content: str) -> ConversationTurn:
        row = ConversationTurn(role=role, content=content, user_id=self.user_id)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def window(self) -> List[Dict[str, str]]:
        rows = self._q(ConversationTurn).order_by(ConversationTurn.id.desc()).limit(WINDOW).all()
        rows.reverse()
        return [{"role": r.role, "content": r.content} for r in rows]

    def summaries(self) -> str:
        rows = self._q(ConversationSummary).order_by(ConversationSummary.id.asc()).all()
        return "\n\n".join(r.summary for r in rows)

    async def maybe_compress(self):
        total = self._q(ConversationTurn).count()
        if total <= WINDOW * 2:
            return

        last_summary = (
            self._q(ConversationSummary).order_by(ConversationSummary.id.desc()).first()
        )
        start_after = last_summary.up_to_turn_id if last_summary else 0
        to_summarize = (
            self._q(ConversationTurn)
            .filter(ConversationTurn.id > start_after)
            .order_by(ConversationTurn.id.asc())
            .limit(total - WINDOW)
            .all()
        )
        if not to_summarize:
            return

        transcript = "\n".join(f"{t.role}: {t.content}" for t in to_summarize)
        summary_text = await self._summarize(transcript)
        if not summary_text:
            return

        self.db.add(
            ConversationSummary(
                summary=summary_text,
                up_to_turn_id=to_summarize[-1].id,
                user_id=self.user_id,
            )
        )
        self.db.commit()

    async def _summarize(self, transcript: str) -> str:
        """Run the cheapest model on the user's provider to produce a terse
        factual summary. Routed through the provider abstraction — never
        imports `anthropic` directly."""
        from .providers.base import AIMessage
        from .providers.factory import get_provider

        # Pick user's provider + key; fall back to anthropic/env
        provider_name = "anthropic"
        api_key = ""
        if self.user_id is not None:
            settings = (
                self.db.query(UserSettings).filter_by(user_id=self.user_id).first()
            )
            if settings:
                provider_name = settings.ai_provider or "anthropic"
                from crypto import decrypt
                enc = getattr(settings, f"{provider_name}_api_key_encrypted", None)
                if enc:
                    try:
                        api_key = decrypt(enc) or ""
                    except Exception:
                        api_key = ""
        if not api_key:
            api_key = os.getenv(f"{provider_name.upper()}_API_KEY", "").strip()
        if not api_key:
            logger.warning("memory compression skipped: no API key for %s", provider_name)
            return ""

        try:
            provider = get_provider(provider_name, api_key)
            cheap_model = provider.cheapest_model()
            resp = await provider.complete(
                messages=[
                    AIMessage(
                        role="user",
                        content=(
                            "Compress this conversation into a terse factual summary. "
                            "Keep names, dates, decisions, open follow-ups. Drop pleasantries.\n\n"
                            + transcript
                        ),
                    )
                ],
                system="You compress conversations into concise factual summaries.",
                tools=None,
                model=cheap_model,
                max_tokens=400,
            )
            return resp.text or ""
        except Exception:
            logger.exception("memory compression failed")
            return ""
