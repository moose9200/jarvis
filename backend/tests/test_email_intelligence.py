from datetime import datetime, timezone, timedelta
from models import EmailHistory, SenderProfile
from intelligence.email_scorer import EmailScorer


def _email(sender="a@b.com", subj="hello", snippet="", hours_ago=1, thread="t1"):
    received = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat().replace("+00:00", "Z")
    return {"from": sender, "subject": subj, "snippet": snippet, "received": received, "thread_id": thread}


def test_cold_start_uses_recency_and_urgency(db):
    scorer = EmailScorer(db)
    fresh_urgent = scorer.score(_email(subj="URGENT contract", hours_ago=0.5))
    stale = scorer.score(_email(subj="random", hours_ago=72))
    assert fresh_urgent > stale
    assert fresh_urgent >= 0.7


def test_warm_path_weights_relationship(db):
    for i in range(55):
        db.add(EmailHistory(
            sender=f"x{i}@b.com",
            subject="s",
            received_at=datetime.utcnow(),
            opened=1,
            thread_id="tx",
        ))
    db.add(SenderProfile(sender="vip@b.com", relationship_weight=0.95, email_count=10, reply_rate=0.9))
    db.add(SenderProfile(sender="rando@b.com", relationship_weight=0.1, email_count=1, reply_rate=0.0))
    db.commit()

    scorer = EmailScorer(db)
    vip = scorer.score(_email(sender="vip@b.com", subj="hi", hours_ago=2))
    rando = scorer.score(_email(sender="rando@b.com", subj="hi", hours_ago=2))
    assert vip > rando


def test_urgency_signal_boosts_score(db):
    scorer = EmailScorer(db)
    plain = scorer.score(_email(subj="status update", hours_ago=2))
    urgent = scorer.score(_email(subj="DEADLINE today!", hours_ago=2))
    assert urgent > plain
