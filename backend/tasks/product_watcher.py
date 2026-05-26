"""Celery tasks for the product-release watcher.

Public tasks:
  - run_product_watcher_for_user(user_id, sites?) — one user's watch cycle
  - run_product_watcher_for_all()                  — beat: fan out to every user
                                                     who has an industry that
                                                     looks jewellery / piercing /
                                                     tattoo (cheap heuristic
                                                     until we add per-user
                                                     watcher prefs)

The beat schedule is wired in worker.py.
"""
from __future__ import annotations

import asyncio
import logging

from worker import celery_app

logger = logging.getLogger("jarvis.tasks.product_watcher")

# Industry-keyword gate. Users whose `industry` substring-matches any of
# these get the canned watcher fired daily. Future: replace with an
# explicit per-user opt-in setting.
INDUSTRY_KEYWORDS = (
    "jewel",        # jewellery / jewelry
    "pierc",        # piercing
    "tattoo",
    "body modification",
    "bodymod",
)


@celery_app.task(name="product_watcher.run_for_user")
def run_product_watcher_for_user(user_id: int, sites: list[str] | None = None) -> dict:
    """Run one user's watch cycle. Returns stats dict from
    intel.product_watcher.run_watch_cycle."""
    from database import SessionLocal
    from intel.product_watcher import run_watch_cycle

    db = SessionLocal()
    try:
        return asyncio.run(run_watch_cycle(db, user_id=user_id, sites=sites))
    except Exception:
        logger.exception("product_watcher.run_for_user failed user_id=%s", user_id)
        return {"error": "task crashed; see worker logs"}
    finally:
        db.close()


@celery_app.task(name="product_watcher.run_for_all")
def run_product_watcher_for_all() -> dict:
    """Beat target. Iterate every user whose industry matches the canned
    keyword set and enqueue a per-user run.

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
            run_product_watcher_for_user.delay(u.id)
            enqueued += 1
        return {"enqueued": enqueued, "checked": len(users)}
    finally:
        db.close()
