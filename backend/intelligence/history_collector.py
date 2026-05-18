from datetime import datetime
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
    def __init__(self, db: Session):
        self.db = db

    async def collect(self) -> int:
        items = []
        items += await GmailConnector(self.db).fetch(max_results=50)
        items += await OutlookMailConnector(self.db).fetch(top=50)

        added = 0
        for e in items:
            sender = e.get("from", "").lower()
            if not sender:
                continue
            exists = (
                self.db.query(EmailHistory)
                .filter_by(sender=sender, subject=e.get("subject", ""))
                .first()
            )
            if exists:
                continue
            rec = EmailHistory(
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
        rows = self.db.query(EmailHistory).all()
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
            prof = self.db.query(SenderProfile).filter_by(sender=sender).first()
            if not prof:
                prof = SenderProfile(sender=sender)
                self.db.add(prof)
            prof.email_count = count
            prof.reply_rate = replies / max(1, count)
            prof.avg_reply_latency = avg_lat
            prof.relationship_weight = relationship
            prof.last_updated = datetime.utcnow()
        self.db.commit()
