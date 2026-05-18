import os
from typing import List, Dict
from sqlalchemy.orm import Session
from anthropic import Anthropic
from models import ConversationTurn, ConversationSummary

WINDOW = 20
COMPRESSION_MODEL = "claude-haiku-4-5-20251001"

class ConversationMemory:
    def __init__(self, db: Session):
        self.db = db

    def append(self, role: str, content: str) -> ConversationTurn:
        row = ConversationTurn(role=role, content=content)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def window(self) -> List[Dict[str, str]]:
        rows = self.db.query(ConversationTurn).order_by(ConversationTurn.id.desc()).limit(WINDOW).all()
        rows.reverse()
        return [{"role": r.role, "content": r.content} for r in rows]

    def summaries(self) -> str:
        rows = self.db.query(ConversationSummary).order_by(ConversationSummary.id.asc()).all()
        return "\n\n".join(r.summary for r in rows)

    async def maybe_compress(self):
        total = self.db.query(ConversationTurn).count()
        if total <= WINDOW * 2:
            return
        last_summary = self.db.query(ConversationSummary).order_by(ConversationSummary.id.desc()).first()
        start_after = last_summary.up_to_turn_id if last_summary else 0
        to_summarize = (
            self.db.query(ConversationTurn)
            .filter(ConversationTurn.id > start_after)
            .order_by(ConversationTurn.id.asc())
            .limit(total - WINDOW)
            .all()
        )
        if not to_summarize:
            return
        transcript = "\n".join(f"{t.role}: {t.content}" for t in to_summarize)
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        resp = client.messages.create(
            model=COMPRESSION_MODEL,
            max_tokens=400,
            system="Compress this assistant conversation into a terse factual summary. Keep names, dates, decisions, and open follow-ups. Drop pleasantries.",
            messages=[{"role": "user", "content": transcript}],
        )
        summary_text = "".join(b.text for b in resp.content if hasattr(b, "text"))
        self.db.add(ConversationSummary(summary=summary_text, up_to_turn_id=to_summarize[-1].id))
        self.db.commit()
