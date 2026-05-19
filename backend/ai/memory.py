import os
from typing import List, Dict
from sqlalchemy.orm import Session
from openai import OpenAI
from models import ConversationTurn, ConversationSummary

WINDOW = 20
GROQ_BASE = "https://api.groq.com/openai/v1"
COMPRESSION_MODEL = os.getenv("AI_COMPRESSION_MODEL", "llama-3.1-8b-instant")


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
        api_key = os.getenv("GROQ_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "")
        base_url = GROQ_BASE if os.getenv("GROQ_API_KEY") else None
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=COMPRESSION_MODEL,
            max_tokens=400,
            messages=[
                {"role": "system", "content": "Compress this conversation into a terse factual summary. Keep names, dates, decisions, open follow-ups. Drop pleasantries."},
                {"role": "user", "content": transcript},
            ],
        )
        summary_text = resp.choices[0].message.content or ""
        self.db.add(ConversationSummary(summary=summary_text, up_to_turn_id=to_summarize[-1].id))
        self.db.commit()
