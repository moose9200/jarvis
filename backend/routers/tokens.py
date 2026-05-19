"""Token usage + cost endpoints. Powers Settings → Usage and the floating
TokenMonitor UI (Step 12)."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import TokenUsage, User, UserSettings
from routers.users import get_current_user

router = APIRouter()


def _today_key() -> str:
    return date.today().isoformat()


def _aggregate(rows) -> dict:
    return {
        "input": sum(r.input_tokens or 0 for r in rows),
        "output": sum(r.output_tokens or 0 for r in rows),
        "cache_read": sum(r.cache_read_tokens or 0 for r in rows),
        "cache_write": sum(r.cache_write_tokens or 0 for r in rows),
        "thinking": sum(r.thinking_tokens or 0 for r in rows),
        "cost_usd": round(sum(r.cost_usd or 0.0 for r in rows), 6),
        "calls": len(rows),
    }


@router.get("/tokens/today")
def today(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Today's usage totals + budget headroom."""
    rows = (
        db.query(TokenUsage)
        .filter(TokenUsage.user_id == current_user.id, TokenUsage.date == _today_key())
        .all()
    )
    agg = _aggregate(rows)
    settings = db.query(UserSettings).filter_by(user_id=current_user.id).first()
    budget = settings.daily_token_budget if settings else 100_000
    used = agg["input"] + agg["output"]
    pct = round(100.0 * used / budget, 1) if budget else 0.0
    return {
        "date": _today_key(),
        **agg,
        "budget": budget,
        "used_total_tokens": used,
        "used_pct": pct,
    }


@router.get("/tokens/history")
def history(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Daily totals over the last N days (default 7). Used for sparkline."""
    cutoff = (date.today() - timedelta(days=days - 1)).isoformat()
    rows = (
        db.query(
            TokenUsage.date.label("date"),
            func.sum(TokenUsage.input_tokens).label("input"),
            func.sum(TokenUsage.output_tokens).label("output"),
            func.sum(TokenUsage.cost_usd).label("cost_usd"),
            func.count(TokenUsage.id).label("calls"),
        )
        .filter(TokenUsage.user_id == current_user.id, TokenUsage.date >= cutoff)
        .group_by(TokenUsage.date)
        .order_by(TokenUsage.date.asc())
        .all()
    )
    return {
        "days": days,
        "series": [
            {
                "date": r.date,
                "input": int(r.input or 0),
                "output": int(r.output or 0),
                "cost_usd": round(float(r.cost_usd or 0.0), 6),
                "calls": int(r.calls or 0),
            }
            for r in rows
        ],
    }


@router.get("/tokens/session")
def session_recent(
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Most-recent N calls — useful for in-session debugging."""
    rows = (
        db.query(TokenUsage)
        .filter(TokenUsage.user_id == current_user.id)
        .order_by(TokenUsage.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "calls": [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "provider": r.provider,
                "model": r.model,
                "input": r.input_tokens or 0,
                "output": r.output_tokens or 0,
                "cache_read": r.cache_read_tokens or 0,
                "cost_usd": round(float(r.cost_usd or 0.0), 6),
            }
            for r in rows
        ]
    }
