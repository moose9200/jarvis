"""Celebrity / influencer mention endpoints — surface noise discovered by
the mention watcher (backend/intel/mention_watcher.py).

  GET  /api/mentions             paginated, newest-first
  GET  /api/mentions/sources     distinct sources + per-source counts
  POST /api/mentions/refresh     run a watch cycle now (synchronous,
                                  returns stats); useful for manual
                                  test + admin reruns

All endpoints are scoped to the current user. Cross-tenant leakage is
prevented by the user_id filter on every query.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from intel.mention_watcher import run_mention_cycle
from models import Mention, User
from routers.users import get_current_user

router = APIRouter()


def _serialize(r: Mention) -> dict:
    return {
        "id": r.id,
        "source": r.source,
        "title": r.title,
        "url": r.url,
        "summary": r.summary,
        "author": r.author,
        "published_at": r.published_at.isoformat() if r.published_at else None,
        "first_seen_at": r.first_seen_at.isoformat() if r.first_seen_at else None,
    }


@router.get("/mentions")
def list_mentions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    source: Optional[str] = Query(None, description="Filter by source string"),
    since_hours: Optional[int] = Query(
        None,
        ge=1,
        le=720,
        description="Only rows first seen in the last N hours",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List mentions discovered for the current user, newest-first."""
    q = db.query(Mention).filter(Mention.user_id == current_user.id)
    if source:
        q = q.filter(Mention.source == source)
    if since_hours:
        cutoff = datetime.utcnow() - timedelta(hours=since_hours)
        q = q.filter(Mention.first_seen_at >= cutoff)
    total = q.count()
    rows = (
        q.order_by(Mention.first_seen_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_serialize(r) for r in rows],
    }


@router.get("/mentions/sources")
def list_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Distinct sources + row counts for the current user."""
    pairs = (
        db.query(Mention.source, func.count(Mention.id))
        .filter(Mention.user_id == current_user.id)
        .group_by(Mention.source)
        .order_by(func.count(Mention.id).desc())
        .all()
    )
    return {
        "sources": [{"source": s, "count": int(c)} for s, c in pairs],
    }


class RefreshIn(BaseModel):
    queries: Optional[list[str]] = None  # defaults to per-industry pack


@router.post("/mentions/refresh")
def refresh_now(
    payload: RefreshIn | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run a mention cycle synchronously for the current user. Useful
    for the UI's "Refresh now" button, manual smoke tests, and admin
    reruns. Idempotent — already-seen URLs are no-ops."""
    queries = payload.queries if (payload and payload.queries) else None
    result = asyncio.run(
        run_mention_cycle(db, user_id=current_user.id, queries=queries)
    )
    return result
