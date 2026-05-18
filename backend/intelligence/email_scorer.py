import re
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models import SenderProfile, EmailHistory

URGENT_RX = re.compile(r"\b(urgent|asap|today|tomorrow|deadline|now|emergency|critical|important)\b", re.I)


def _hours_since(s: str) -> float:
    if not s:
        return 48.0
    try:
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0)
    except Exception:
        return 24.0


class EmailScorer:
    COLD_START_TOTAL = 50

    def __init__(self, db: Session):
        self.db = db
        self._total = db.query(EmailHistory).count()

    def _relationship(self, sender: str) -> float:
        prof = self.db.query(SenderProfile).filter_by(sender=sender.lower()).first()
        if not prof:
            return 0.3
        return prof.relationship_weight

    def _recency(self, received: str) -> float:
        h = _hours_since(received)
        if h < 1:
            return 1.0
        if h < 6:
            return 0.85
        if h < 24:
            return 0.6
        if h < 48:
            return 0.35
        return 0.1

    def _urgency(self, subject: str, snippet: str) -> float:
        text = f"{subject} {snippet}"
        hits = len(URGENT_RX.findall(text))
        if hits == 0:
            return 0.1
        return min(1.0, 0.4 + 0.2 * hits)

    def _thread_depth(self, thread_id: str) -> float:
        if not thread_id:
            return 0.1
        cnt = self.db.query(EmailHistory).filter_by(thread_id=thread_id).count()
        return min(1.0, cnt / 5.0)

    def score(self, email: dict) -> float:
        if self._total < self.COLD_START_TOTAL:
            # Cold start: recency + urgency dominate
            return round(self._recency(email.get("received", "")) * 0.6 + self._urgency(email.get("subject", ""), email.get("snippet", "")) * 0.4, 3)
        sender = email.get("from", "").lower()
        rel = self._relationship(sender)
        rec = self._recency(email.get("received", ""))
        urg = self._urgency(email.get("subject", ""), email.get("snippet", ""))
        td = self._thread_depth(email.get("thread_id", ""))
        return round(rel * 0.4 + rec * 0.3 + urg * 0.2 + td * 0.1, 3)
