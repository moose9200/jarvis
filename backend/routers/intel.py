"""Intel Brief endpoints — periodic public-web monitors.

  GET    /api/intel-briefs              list user's briefs
  POST   /api/intel-briefs              create a brief
  PUT    /api/intel-briefs/{id}         update (rename, change sources, toggle active)
  DELETE /api/intel-briefs/{id}         remove brief + its runs
  POST   /api/intel-briefs/{id}/run     execute now, returns the run dict
  GET    /api/intel-briefs/{id}/runs    list past runs (most recent first)
  GET    /api/intel-briefs/runs/{rid}   fetch a specific run's full output
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from intel.fetchers import default_sources_for_industry
from intel.synth import run_brief
from models import IntelBrief, IntelBriefRun, User
from routers.users import get_current_user

router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────────────────


class BriefIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    topic: str = Field(..., min_length=2, max_length=200)
    sources_json: Optional[dict[str, Any]] = None
    prompt_template: Optional[str] = Field(None, max_length=4000)
    frequency_minutes: Optional[int] = Field(None, ge=15, le=10080)  # 15 min to 1 week
    is_active: bool = True


class BriefPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    topic: Optional[str] = Field(None, min_length=2, max_length=200)
    sources_json: Optional[dict[str, Any]] = None
    prompt_template: Optional[str] = Field(None, max_length=4000)
    frequency_minutes: Optional[int] = Field(None, ge=15, le=10080)
    is_active: Optional[bool] = None


def _serialize(b: IntelBrief) -> dict:
    return {
        "id": b.id,
        "name": b.name,
        "topic": b.topic,
        "sources_json": b.sources_json,
        "prompt_template": b.prompt_template,
        "frequency_minutes": b.frequency_minutes,
        "is_active": b.is_active,
        "last_run_at": b.last_run_at.isoformat() if b.last_run_at else None,
        "next_run_at": b.next_run_at.isoformat() if b.next_run_at else None,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }


def _serialize_run(r: IntelBriefRun) -> dict:
    return {
        "id": r.id,
        "brief_id": r.brief_id,
        "status": r.status,
        "output_text": r.output_text,
        "sources_summary": r.sources_summary,
        "error": r.error,
        "cost_usd": r.cost_usd,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
    }


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/intel-briefs")
def list_briefs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(IntelBrief)
        .filter(IntelBrief.user_id == current_user.id)
        .order_by(IntelBrief.id.asc())
        .all()
    )
    return {"briefs": [_serialize(b) for b in rows]}


@router.post("/intel-briefs")
def create_brief(
    payload: BriefIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sources = payload.sources_json or default_sources_for_industry(
        current_user.industry or payload.topic
    )
    b = IntelBrief(
        user_id=current_user.id,
        name=payload.name,
        topic=payload.topic,
        sources_json=sources,
        prompt_template=payload.prompt_template,
        frequency_minutes=payload.frequency_minutes,
        is_active=payload.is_active,
        created_at=datetime.utcnow(),
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return _serialize(b)


@router.put("/intel-briefs/{brief_id}")
def update_brief(
    brief_id: int,
    payload: BriefPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    b = (
        db.query(IntelBrief)
        .filter(IntelBrief.id == brief_id, IntelBrief.user_id == current_user.id)
        .first()
    )
    if not b:
        raise HTTPException(404, "Brief not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(b, k, v)
    db.commit()
    db.refresh(b)
    return _serialize(b)


@router.delete("/intel-briefs/{brief_id}")
def delete_brief(
    brief_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    b = (
        db.query(IntelBrief)
        .filter(IntelBrief.id == brief_id, IntelBrief.user_id == current_user.id)
        .first()
    )
    if not b:
        raise HTTPException(404, "Brief not found")
    # Delete runs too
    db.query(IntelBriefRun).filter(IntelBriefRun.brief_id == brief_id).delete()
    db.delete(b)
    db.commit()
    return {"ok": True, "deleted": brief_id}


@router.post("/intel-briefs/{brief_id}/run")
async def execute_brief(
    brief_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run the brief NOW. Returns the full run with synthesized output.
    This is a synchronous endpoint — useful for the "Refresh" button in the
    UI. Periodic execution is handled by the Celery beat schedule (deferred
    until Celery beat is wired)."""
    b = (
        db.query(IntelBrief)
        .filter(IntelBrief.id == brief_id, IntelBrief.user_id == current_user.id)
        .first()
    )
    if not b:
        raise HTTPException(404, "Brief not found")
    return await run_brief(db, b, current_user.id)


@router.get("/intel-briefs/{brief_id}/runs")
def list_runs(
    brief_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    b = (
        db.query(IntelBrief)
        .filter(IntelBrief.id == brief_id, IntelBrief.user_id == current_user.id)
        .first()
    )
    if not b:
        raise HTTPException(404, "Brief not found")
    rows = (
        db.query(IntelBriefRun)
        .filter(IntelBriefRun.brief_id == brief_id)
        .order_by(IntelBriefRun.id.desc())
        .limit(limit)
        .all()
    )
    return {"runs": [_serialize_run(r) for r in rows]}


@router.get("/intel-briefs/runs/{run_id}")
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = (
        db.query(IntelBriefRun)
        .filter(IntelBriefRun.id == run_id, IntelBriefRun.user_id == current_user.id)
        .first()
    )
    if not r:
        raise HTTPException(404, "Run not found")
    return _serialize_run(r)
