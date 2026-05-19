import os
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import anthropic
from models import ConversationTurn, ConversationSummary

WINDOW = 20
COMPRESSION_MODEL = os.getenv("AI_COMPRESSION_MODEL", "claude-haiku-4-5")


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
        last_summary = self._q(ConversationSummary).order_by(ConversationSummary.id.desc()).first()
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
        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        resp = await client.messages.create(
            model=COMPRESSION_MODEL,
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": f"Compress this conversation into a terse factual summary. Keep names, dates, decisions, open follow-ups. Drop pleasantries.\n\n{transcript}",
            }],
        )
        summary_text = resp.content[0].text if resp.content else ""
        self.db.add(ConversationSummary(
            summary=summary_text,
            up_to_turn_id=to_summarize[-1].id,
            user_id=self.user_id,
        ))
        self.db.commit()
