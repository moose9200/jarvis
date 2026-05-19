"""Decision Inbox — items awaiting user action.

Sources expected to fill this table (separately, via Celery jobs):
  - github_pr      pending PR reviews
  - shopify_order  large orders flagged for attention
  - freshdesk      urgent / aging tickets
  - linear / jira  issues marked blocked or waiting on user

Endpoints
---------
  GET    /api/decisions                  list pending (default) or any status
  POST   /api/decisions                  manual create (used by tests + tools)
  PATCH  /api/decisions/{id}             change status (approve/reject/delegate/snooze)
  DELETE /api/decisions/{id}             permanent remove
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import Decision, User
from routers.users import get_current_user

router = APIRouter()

VALID_STATUSES = {"pending", "approved", "rejected", "delegated", "snoozed", "archived"}


# ── Schemas ─────────────────────────────────────────────────────────────────


class DecisionIn(BaseModel):
    source: str = Field(..., max_length=40)             # github_pr | shopify_order | …
    source_id: Optional[str] = Field(None, max_length=200)
    title: str = Field(..., max_length=200)
    context_json: Optional[dict] = None
    ai_suggestion: Optional[str] = Field(None, max_length=4000)


class DecisionPatch(BaseModel):
    status: Optional[str] = Field(None, max_length=20)
    ai_suggestion: Optional[str] = Field(None, max_length=4000)
    snooze_hours: Optional[int] = Field(None, ge=1, le=720)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _serialize(d: Decision) -> dict:
    return {
        "id": d.id,
        "source": d.source,
        "source_id": d.source_id,
        "title": d.title,
        "context_json": d.context_json,
        "status": d.status,
        "ai_suggestion": d.ai_suggestion,
        "snoozed_until": d.snoozed_until.isoformat() if d.snoozed_until else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "decided_at": d.decided_at.isoformat() if d.decided_at else None,
    }


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/decisions")
def list_decisions(
    status: str = Query("pending", description="pending | approved | rejected | delegated | snoozed | all"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Decision).filter(Decision.user_id == current_user.id)
    if status != "all":
        if status not in VALID_STATUSES:
            raise HTTPException(400, f"Invalid status: {status}")
        # Snoozed items return to pending automatically when the timer expires
        if status == "pending":
            now = datetime.utcnow()
            from sqlalchemy import or_
            q = q.filter(
                or_(
                    Decision.status == "pending",
                    (Decision.status == "snoozed") & (Decision.snoozed_until <= now),
                )
            )
        else:
            q = q.filter(Decision.status == status)
    q = q.order_by(Decision.created_at.desc()).limit(limit)
    return {"decisions": [_serialize(d) for d in q.all()]}


@router.post("/decisions")
def create_decision(
    payload: DecisionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = Decision(
        user_id=current_user.id,
        source=payload.source,
        source_id=payload.source_id,
        title=payload.title,
        context_json=payload.context_json,
        ai_suggestion=payload.ai_suggestion,
        status="pending",
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.patch("/decisions/{decision_id}")
def patch_decision(
    decision_id: int,
    payload: DecisionPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    d = (
        db.query(Decision)
        .filter(Decision.id == decision_id, Decision.user_id == current_user.id)
        .first()
    )
    if not d:
        raise HTTPException(404, "Decision not found")

    if payload.status:
        new_status = payload.status.lower().strip()
        if new_status not in VALID_STATUSES:
            raise HTTPException(400, f"Invalid status: {new_status}")
        d.status = new_status
        if new_status == "snoozed":
            hours = payload.snooze_hours or 24
            d.snoozed_until = datetime.utcnow() + timedelta(hours=hours)
        elif new_status in ("approved", "rejected", "delegated", "archived"):
            d.decided_at = datetime.utcnow()

    if payload.ai_suggestion is not None:
        d.ai_suggestion = payload.ai_suggestion

    db.commit()
    db.refresh(d)
    return _serialize(d)


@router.delete("/decisions/{decision_id}")
def delete_decision(
    decision_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    d = (
        db.query(Decision)
        .filter(Decision.id == decision_id, Decision.user_id == current_user.id)
        .first()
    )
    if not d:
        raise HTTPException(404, "Decision not found")
    db.delete(d)
    db.commit()
    return {"ok": True, "deleted": decision_id}
