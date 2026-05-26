"""Product-release endpoints — surface new products discovered by the
industry watcher (backend/intel/product_watcher.py).

  GET  /api/product-releases             paginated, newest-first
  GET  /api/product-releases/sites       list of watched sites + counts
  POST /api/product-releases/refresh     run a watch cycle now (synchronous,
                                          returns stats); useful for manual
                                          test + admin reruns

All endpoints are scoped to the current user. Cross-tenant leakage is
prevented by the user_id filter on every query.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from intel.product_watcher import WATCHED_SITES, run_watch_cycle
from models import ProductRelease, User
from routers.users import get_current_user

router = APIRouter()


def _serialize(r: ProductRelease) -> dict:
    return {
        "id": r.id,
        "site_domain": r.site_domain,
        "external_product_id": r.external_product_id,
        "handle": r.handle,
        "title": r.title,
        "vendor": r.vendor,
        "product_type": r.product_type,
        "tags": r.tags or [],
        "price": r.price,
        "image_url": r.image_url,
        "url": r.url,
        "created_at_remote": r.created_at_remote.isoformat() if r.created_at_remote else None,
        "published_at_remote": r.published_at_remote.isoformat() if r.published_at_remote else None,
        "first_seen_at": r.first_seen_at.isoformat() if r.first_seen_at else None,
        "last_seen_at": r.last_seen_at.isoformat() if r.last_seen_at else None,
    }


@router.get("/product-releases")
def list_product_releases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    site: Optional[str] = Query(None, description="Filter by site domain"),
    since_hours: Optional[int] = Query(None, ge=1, le=720, description="Only rows first seen in the last N hours"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List products discovered for the current user, newest-first."""
    q = db.query(ProductRelease).filter(ProductRelease.user_id == current_user.id)
    if site:
        q = q.filter(ProductRelease.site_domain == site)
    if since_hours:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=since_hours)
        q = q.filter(ProductRelease.first_seen_at >= cutoff)
    total = q.count()
    rows = (
        q.order_by(ProductRelease.first_seen_at.desc())
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


@router.get("/product-releases/sites")
def list_sites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Watched sites + per-site row counts for the current user. Includes
    the canned defaults even if the user has no rows yet, so the UI can
    show "no data yet" instead of an empty list."""
    counts = dict(
        db.query(ProductRelease.site_domain, func.count(ProductRelease.id))
        .filter(ProductRelease.user_id == current_user.id)
        .group_by(ProductRelease.site_domain)
        .all()
    )
    out = []
    for d in WATCHED_SITES:
        out.append({"domain": d, "count": int(counts.get(d, 0))})
    # Any extra sites the user has rows for but that aren't in defaults
    for d, c in counts.items():
        if d not in {x["domain"] for x in out}:
            out.append({"domain": d, "count": int(c)})
    return {"sites": out, "defaults": WATCHED_SITES}


class RefreshIn(BaseModel):
    sites: Optional[list[str]] = None  # defaults to WATCHED_SITES


@router.post("/product-releases/refresh")
def refresh_now(
    payload: RefreshIn | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run a watch cycle synchronously for the current user. Useful for the
    UI's "Refresh now" button, manual smoke tests, and admin reruns. Idempotent.
    """
    sites = payload.sites if (payload and payload.sites) else None
    result = asyncio.run(run_watch_cycle(db, user_id=current_user.id, sites=sites))
    return result
