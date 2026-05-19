"""User context CRUD — the persona injected into every JARVIS prompt."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserContext
from routers.users import get_current_user

router = APIRouter()


class ContextIn(BaseModel):
    """All fields optional — patch semantics."""
    about_me: Optional[str] = Field(None, max_length=4000)
    communication_style: Optional[str] = Field(None, max_length=2000)
    priorities: Optional[str] = Field(None, max_length=2000)
    team_members: Optional[list[dict]] = None      # [{name, role, relationship}]
    business_context: Optional[str] = Field(None, max_length=4000)


def _ensure(db: Session, user_id: int) -> UserContext:
    ctx = db.query(UserContext).filter_by(user_id=user_id).first()
    if not ctx:
        ctx = UserContext(user_id=user_id)
        db.add(ctx)
        db.commit()
        db.refresh(ctx)
    return ctx


def _serialize(ctx: UserContext) -> dict:
    return {
        "about_me": ctx.about_me,
        "communication_style": ctx.communication_style,
        "priorities": ctx.priorities,
        "team_members": ctx.team_members,
        "business_context": ctx.business_context,
        "updated_at": ctx.updated_at.isoformat() if ctx.updated_at else None,
    }


@router.get("/context")
def get_context(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _serialize(_ensure(db, current_user.id))


@router.put("/context")
def put_context(
    payload: ContextIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ctx = _ensure(db, current_user.id)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(ctx, k, v)
    ctx.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ctx)
    return _serialize(ctx)
