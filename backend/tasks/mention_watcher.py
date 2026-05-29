"""Celery tasks for the celebrity / influencer mention watcher.

Public tasks:
  - run_mention_watcher_for_user(user_id, queries?) — one user's cycle
  - run_mention_watcher_for_all()                   — beat: fan out to every
                                                      user whose industry
                                                      substring-matches the
                                                      INDUSTRY_KEYWORDS gate

The beat schedule is wired in worker.py.
"""
from __future__ import annotations

import asyncio
import logging

from worker import celery_app

logger = logging.getLogger("jarvis.tasks.mention_watcher")

# Industry-keyword gate — same set as tasks/product_watcher.py so the
# two Phase-N monitors fire on identical user populations.
INDUSTRY_KEYWORDS = (
    "jewel",        # jewellery / jewelry
    "pierc",        # piercing
    "tattoo",
    "body modification",
    "bodymod",
)


@celery_app.task(name="mention_watcher.run_for_user")
def run_mention_watcher_for_user(
    user_id: int, queries: list[str] | None = None
) -> dict:
    """Run one user's mention cycle. Returns stats dict from
    intel.mention_watcher.run_mention_cycle."""
    from database import SessionLocal
    from intel.mention_watcher import run_mention_cycle

    db = SessionLocal()
    try:
        return asyncio.run(
            run_mention_cycle(db, user_id=user_id, queries=queries)
        )
    except Exception:
        logger.exception(
            "mention_watcher.run_for_user failed user_id=%s", user_id
        )
        return {"error": "task crashed; see worker logs"}
    finally:
        db.close()


@celery_app.task(name="mention_watcher.run_for_all")
def run_mention_watcher_for_all() -> dict:
    """Beat target. Iterate every user whose industry matches the
    canned keyword set and enqueue a per-user run.

    Cheap: just fans out; the real work runs in `run_for_user`.
    """
    from database import SessionLocal
    from models import User

    db = SessionLocal()
    enqueued = 0
    try:
        users = db.query(User).all()
        for u in users:
            industry = (getattr(u, "industry", None) or "").lower()
            if not any(kw in industry for kw in INDUSTRY_KEYWORDS):
                continue
            run_mention_watcher_for_user.delay(u.id)
            enqueued += 1
        return {"enqueued": enqueued, "checked": len(users)}
    finally:
        db.close()
