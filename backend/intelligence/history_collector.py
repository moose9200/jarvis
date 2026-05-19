from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from models import EmailHistory, SenderProfile
from connectors.gmail import GmailConnector
from connectors.outlook_mail import OutlookMailConnector


def _parse_dt(s: str) -> datetime:
    if not s:
        return datetime.utcnow()
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=None)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return datetime.utcnow()


class HistoryCollector:
    def __init__(self, db: Session, user_id: Optional[int] = None):
        self.db = db
        self.user_id = user_id

    async def collect(self) -> int:
        items = []
        items += await GmailConnector(self.db, self.user_id).fetch(max_results=50)
        items += await OutlookMailConnector(self.db, self.user_id).fetch(top=50)

        added = 0
        for e in items:
            sender = e.get("from", "").lower()
            if not sender:
                continue
            q = self.db.query(EmailHistory).filter_by(sender=sender, subject=e.get("subject", ""))
            if self.user_id is not None:
                q = q.filter_by(user_id=self.user_id)
            if q.first():
                continue
            rec = EmailHistory(
                user_id=self.user_id,
                sender=sender,
                subject=e.get("subject", "")[:500],
                received_at=_parse_dt(e.get("received", "")),
                opened=0 if e.get("unread", False) else 1,
                thread_id=e.get("thread_id"),
            )
            self.db.add(rec)
            added += 1
        self.db.commit()
        self._rebuild_profiles()
        return added

    def _rebuild_profiles(self):
        q = self.db.query(EmailHistory)
        if self.user_id is not None:
            q = q.filter_by(user_id=self.user_id)
        rows = q.all()
        by_sender: dict[str, list[EmailHistory]] = {}
        for r in rows:
            by_sender.setdefault(r.sender, []).append(r)
        for sender, lst in by_sender.items():
            count = len(lst)
            opens = sum(r.opened for r in lst)
            replies = sum(r.replied for r in lst)
            latencies = [r.reply_latency_seconds for r in lst if r.reply_latency_seconds]
            avg_lat = sum(latencies) / len(latencies) if latencies else 0
            relationship = min(1.0, (opens / max(1, count)) * 0.5 + (replies / max(1, count)) * 0.5)
            pq = self.db.query(SenderProfile).filter_by(sender=sender)
            if self.user_id is not None:
                pq = pq.filter_by(user_id=self.user_id)
            prof = pq.first()
            if not prof:
                prof = SenderProfile(sender=sender, user_id=self.user_id)
                self.db.add(prof)
            prof.email_count = count
            prof.reply_rate = replies / max(1, count)
            prof.avg_reply_latency = avg_lat
            prof.relationship_weight = relationship
            prof.last_updated = datetime.utcnow()
        self.db.commit()
