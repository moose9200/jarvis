"""Celery tasks for Intel Briefs.

  - run_intel_brief(brief_id)            — execute a single brief
  - run_due_intel_briefs()               — beat-driven: pick all active briefs
                                            whose frequency window has elapsed
                                            and enqueue run_intel_brief for each

The beat schedule lives in worker.py.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from worker import celery_app

logger = logging.getLogger("jarvis.tasks.intel")


@celery_app.task(name="intel.run_brief")
def run_intel_brief(brief_id: int) -> dict:
    """Synchronous Celery wrapper around the async intel.synth.run_brief.
    Returns the serialized run dict or {error: ...} on failure."""
    # Local imports — keep Celery worker boot fast + avoid circular imports.
    from database import SessionLocal
    from intel.synth import run_brief
    from models import IntelBrief

    db = SessionLocal()
    try:
        b = db.query(IntelBrief).filter_by(id=brief_id).first()
        if not b:
            return {"error": f"brief {brief_id} not found"}
        return asyncio.run(run_brief(db, b, b.user_id))
    except Exception:
        logger.exception("intel.run_brief failed for brief_id=%s", brief_id)
        return {"error": "task crashed; see worker logs"}
    finally:
        db.close()


@celery_app.task(name="intel.run_due")
def run_due_intel_briefs() -> dict:
    """Pick every active brief whose `last_run_at + frequency_minutes` is in
    the past (or never ran) and enqueue an execution.

    Beat fires this every 10 min by default — much cheaper than firing each
    brief on its own cadence."""
    from database import SessionLocal
    from models import IntelBrief

    db = SessionLocal()
    enqueued = 0
    try:
        now = datetime.utcnow()
        briefs = (
            db.query(IntelBrief)
            .filter(IntelBrief.is_active == True)  # noqa: E712
            .all()
        )
        for b in briefs:
            if not b.frequency_minutes:
                continue
            due_at = (b.last_run_at or datetime.min) + timedelta(minutes=b.frequency_minutes)
            if due_at <= now:
                run_intel_brief.delay(b.id)
                enqueued += 1
        return {"enqueued": enqueued, "checked": len(briefs)}
    finally:
        db.close()
