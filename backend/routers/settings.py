"""User settings — BYOAK keys, active provider, tier, personality, budget.

All API keys are encrypted at rest via backend/crypto.py. Plaintext keys never
leave the request handler and never appear in logs.

Endpoints
---------
GET  /api/settings              — full settings snapshot (keys masked)
PUT  /api/settings/api-keys     — set/clear keys for any subset of 5 providers
POST /api/settings/test-key     — validate a key without saving (one-shot ping)
PUT  /api/settings/preferences  — change tier, response_length, personality, budget
PUT  /api/settings/active-provider — pick the active provider
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ai.providers.factory import SUPPORTED_PROVIDERS, get_provider
from crypto import decrypt, encrypt
from database import get_db
from models import User, UserSettings
from routers.users import get_current_user

logger = logging.getLogger("jarvis.settings")
router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────────────────


class APIKeysIn(BaseModel):
    """All fields optional. Set a key to a non-empty string to save, set to
    empty string "" to explicitly clear, omit to leave unchanged."""
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    github_pat: Optional[str] = None
    github_repo_url: Optional[str] = None


class TestKeyIn(BaseModel):
    provider: str = Field(..., min_length=2, max_length=20)
    api_key: str = Field(..., min_length=4, max_length=500)


class PreferencesIn(BaseModel):
    default_model: Optional[str] = Field(None, max_length=80)        # tier slug or model id
    response_length: Optional[str] = Field(None, pattern="^(brief|detailed|deep)$")
    personality_mode: Optional[str] = Field(None, max_length=40)
    daily_token_budget: Optional[int] = Field(None, ge=1000, le=100_000_000)
    budget_alert_pct: Optional[int] = Field(None, ge=1, le=100)


class ActiveProviderIn(BaseModel):
    ai_provider: str = Field(..., min_length=2, max_length=20)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _mask(plain: Optional[str]) -> Optional[str]:
    if not plain:
        return None
    if len(plain) <= 8:
        return "•" * len(plain)
    return f"{plain[:4]}{'•' * 8}{plain[-4:]}"


def _ensure_settings(db: Session, user_id: int) -> UserSettings:
    s = db.query(UserSettings).filter_by(user_id=user_id).first()
    if not s:
        s = UserSettings(user_id=user_id)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def _serialize(s: UserSettings) -> dict:
    """Returns the settings with masked keys (never plaintext)."""
    keys = {}
    for provider in SUPPORTED_PROVIDERS:
        enc = getattr(s, f"{provider}_api_key_encrypted", None)
        try:
            keys[provider] = _mask(decrypt(enc)) if enc else None
        except Exception:
            keys[provider] = None
    enc = s.elevenlabs_api_key_encrypted
    try:
        keys["elevenlabs"] = _mask(decrypt(enc)) if enc else None
    except Exception:
        keys["elevenlabs"] = None
    enc = s.github_pat_encrypted
    try:
        gh_pat = _mask(decrypt(enc)) if enc else None
    except Exception:
        gh_pat = None
    return {
        "ai_provider": s.ai_provider,
        "default_model": s.default_model,
        "response_length": s.response_length,
        "personality_mode": s.personality_mode,
        "daily_token_budget": s.daily_token_budget,
        "budget_alert_pct": s.budget_alert_pct,
        "github_repo_url": s.github_repo_url,
        "keys_set": {k: bool(v) for k, v in keys.items()} | {"github_pat": bool(gh_pat)},
        "keys_masked": keys | {"github_pat": gh_pat},
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/settings")
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = _ensure_settings(db, current_user.id)
    return _serialize(s)


@router.put("/settings/api-keys")
def put_api_keys(
    payload: APIKeysIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = _ensure_settings(db, current_user.id)

    # Map payload field -> UserSettings column
    field_map = {
        "anthropic_api_key": "anthropic_api_key_encrypted",
        "openai_api_key": "openai_api_key_encrypted",
        "groq_api_key": "groq_api_key_encrypted",
        "mistral_api_key": "mistral_api_key_encrypted",
        "google_api_key": "google_api_key_encrypted",
        "elevenlabs_api_key": "elevenlabs_api_key_encrypted",
        "github_pat": "github_pat_encrypted",
    }
    data = payload.model_dump(exclude_unset=True)
    for src, col in field_map.items():
        if src not in data:
            continue
        val = data[src]
        if val == "":
            setattr(s, col, None)
        elif val is not None:
            setattr(s, col, encrypt(val))

    if "github_repo_url" in data:
        s.github_repo_url = data["github_repo_url"] or None

    s.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    return _serialize(s)


@router.post("/settings/test-key")
async def test_key(payload: TestKeyIn):
    """Validate an API key without saving it. Returns {ok: bool, error?: str}."""
    p = payload.provider.lower().strip()
    if p not in SUPPORTED_PROVIDERS:
        raise HTTPException(400, f"Unknown provider: {p}")
    try:
        provider = get_provider(p, payload.api_key)
        ok = await provider.validate_key()
        return {"ok": bool(ok)}
    except Exception as e:
        logger.exception("test-key failed for %s", p)
        return {"ok": False, "error": str(e)[:200]}


@router.put("/settings/preferences")
def put_preferences(
    payload: PreferencesIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = _ensure_settings(db, current_user.id)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if v is not None:
            setattr(s, k, v)
    s.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    return _serialize(s)


@router.put("/settings/active-provider")
def put_active_provider(
    payload: ActiveProviderIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = payload.ai_provider.lower().strip()
    if p not in SUPPORTED_PROVIDERS:
        raise HTTPException(400, f"Unknown provider: {p}")
    s = _ensure_settings(db, current_user.id)
    s.ai_provider = p
    s.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    return _serialize(s)
