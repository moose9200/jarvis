import io
import json
import os
import zipfile
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel, Field
from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import inspect as sa_inspect

import oauth_code
from database import get_db
from models import User
from rate_limit import limiter

router = APIRouter()

SECRET_KEY = os.environ["JWT_SECRET"]  # main.py enforces presence at boot
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

bearer_scheme = HTTPBearer(auto_error=False)


# ── Schemas ──────────────────────────────────────────────────────────────────

class RegisterIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=8, max_length=200)
    industry: str = Field(..., min_length=2, max_length=120,
                          description="Free-text industry label, e.g. 'D2C botanicals'. Required at signup.")


class LoginIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=1, max_length=200)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    industry: str | None = None
    created_at: datetime


class IndustryIn(BaseModel):
    industry: str = Field(..., min_length=2, max_length=120)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _create_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate via Bearer header only. ?token= query param is no longer
    accepted — OAuth-redirect flows must use the one-time code exchange
    (see /api/users/oauth-code + get_oauth_user).

    Stashes the resolved User on `request.state.user` so the slowapi
    keyfunc (`rate_limit._user_or_ip_key`) can key on user id rather
    than IP. Without this, users behind a shared NAT would share a
    rate-limit bucket."""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    request.state.user = user
    return user


def get_oauth_user(
    code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate via a one-time ?code= query param, used only by OAuth
    /start endpoints. The code was minted by /api/users/oauth-code, is
    single-use, expires in 60s, and never carries the JWT itself."""
    if not code:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing oauth code")
    user_id = oauth_code.consume(code)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired oauth code")
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenOut)
@limiter.limit("5/minute")
def register(request: Request, payload: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=payload.email,
        password_hash=_hash(payload.password),
        industry=payload.industry.strip(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    _provision_defaults(db, user)
    return TokenOut(access_token=_create_token(user.id, user.email))


def _provision_defaults(db: Session, user: User) -> None:
    """Set up everything a brand-new user needs on first signup:
      - default IntelBrief tied to their industry
      - default UserSettings + UserContext rows (so /me + /context don't 404)
    Each step is wrapped so a failure doesn't block the registration."""
    # Local imports to avoid circular deps during app boot
    from datetime import datetime as _dt

    from intel.fetchers import default_sources_for_industry
    from models import IntelBrief, UserContext, UserSettings

    try:
        if not db.query(UserSettings).filter_by(user_id=user.id).first():
            db.add(UserSettings(user_id=user.id))
        if not db.query(UserContext).filter_by(user_id=user.id).first():
            db.add(UserContext(user_id=user.id))
        if user.industry and not db.query(IntelBrief).filter_by(user_id=user.id).first():
            db.add(IntelBrief(
                user_id=user.id,
                name="Industry chatter",
                topic=user.industry,
                sources_json=default_sources_for_industry(user.industry),
                frequency_minutes=1440,        # daily
                is_active=True,
                created_at=_dt.utcnow(),
            ))
        db.commit()
    except Exception:
        db.rollback()


@router.post("/login", response_model=TokenOut)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=payload.email).first()
    if not user or not _verify(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenOut(access_token=_create_token(user.id, user.email))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        industry=current_user.industry,
        created_at=current_user.created_at,
    )


@router.put("/me/industry", response_model=UserOut)
def set_industry(
    payload: IndustryIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set or update the user's industry. Used by legacy users registered
    before industry became mandatory, and by the Settings → Account tab."""
    current_user.industry = payload.industry.strip()
    db.commit()
    db.refresh(current_user)
    _provision_defaults(db, current_user)
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        industry=current_user.industry,
        created_at=current_user.created_at,
    )


@router.post("/oauth-code")
def mint_oauth_code(current_user: User = Depends(get_current_user)):
    """Exchange the caller's JWT for a single-use, 60-second code that can be
    safely placed in an OAuth /start URL. Frontend redirect flows call this
    first, then navigate the browser to `/api/auth/<provider>/start?code=<code>`."""
    return {"code": oauth_code.issue(current_user.id)}


# ── GDPR — right to erasure + right to portability ──────────────────────────
#
# GDPR (EU) Art. 17 and CCPA §1798.105 both require us to delete every
# user-owned row on request, and Art. 20 / §1798.110 require us to hand
# back all of it in a machine-readable form. Both endpoints below run
# strictly per the authenticated user — no admin override.

class DeleteConfirm(BaseModel):
    """Body for DELETE /me — the user must type their own email to confirm.
    The check is exact-match against `current_user.email`, no normalization,
    no fuzzy matching. We want this to feel intentional."""
    confirm: str = Field(..., min_length=3, max_length=200)


# Tables we cascade-delete from, in dependency order (children first so
# foreign-key constraints don't fire). Names match `models.py` exactly.
# Anything ForeignKey'd to users.id should appear here.
_CASCADE_MODELS = (
    "Decision",
    "TokenUsage",
    "KnowledgeChunk",
    "FileUpload",
    "IntelBriefRun",
    "IntelBrief",
    "ProductRelease",
    "OAuthToken",
    "ConversationTurn",
    "ConversationSummary",
    "SenderProfile",
    "EmailHistory",
    "UserContext",
    "UserSettings",
    "ShopifyConfig",
    "FreshdeskConfig",
)


def _resolve_models(names):
    """Import the listed model classes from `models` lazily so test fixtures
    that monkey-patch the module still see the right class objects, and so
    we degrade gracefully if a future migration removes one."""
    import models as _m

    resolved = []
    for n in names:
        cls = getattr(_m, n, None)
        if cls is not None:
            resolved.append(cls)
    return resolved


# Per-model field redaction for export. Anything in this set is replaced
# with the literal string "<redacted>" in the JSON dump. Keep secrets out
# of any data hand-back — even an attacker who steals an export shouldn't
# get usable credentials.
_REDACTED_FIELDS = {
    "User": {"password_hash"},
    "OAuthToken": {"access_token", "refresh_token"},
    "UserSettings": {
        "anthropic_api_key_encrypted",
        "openai_api_key_encrypted",
        "groq_api_key_encrypted",
        "mistral_api_key_encrypted",
        "google_api_key_encrypted",
        "elevenlabs_api_key_encrypted",
        "github_pat_encrypted",
    },
    "ShopifyConfig": {"access_token_encrypted"},
    "FreshdeskConfig": {"api_key_encrypted"},
}


def _row_to_dict(row: Any) -> dict:
    """Serialise a SQLAlchemy row to a JSON-friendly dict. Datetimes →
    ISO 8601. Unknown types fall back to repr() so we never crash mid-zip."""
    cls_name = row.__class__.__name__
    redact = _REDACTED_FIELDS.get(cls_name, set())
    out: dict = {}
    for col in sa_inspect(row).mapper.column_attrs:
        key = col.key
        if key in redact:
            out[key] = "<redacted>"
            continue
        val = getattr(row, key, None)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
        elif isinstance(val, (str, int, float, bool, type(None), list, dict)):
            out[key] = val
        else:
            out[key] = repr(val)
    return out


@router.delete("/me")
@limiter.limit("3/hour")
def delete_me(
    request: Request,
    payload: DeleteConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GDPR right-to-erasure. Cascade-deletes every user-owned row, then
    the User row itself. Requires `confirm` body to literally equal the
    user's own email so we don't fat-finger account loss.

    Rate-limited 3/hour per user via slowapi to prevent rage-deletes (and
    the test-suite re-running this against the same user)."""
    if payload.confirm != current_user.email:
        raise HTTPException(
            status_code=400,
            detail="Confirmation does not match your email.",
        )

    user_id = current_user.id

    for cls in _resolve_models(_CASCADE_MODELS):
        try:
            db.query(cls).filter_by(user_id=user_id).delete(synchronize_session=False)
        except Exception:
            # If a model isn't FK'd to user_id (defensive), skip rather
            # than abort the cascade. The User delete below will still
            # protect FK integrity since all listed tables nullable=True
            # on user_id are emptied first.
            db.rollback()
            continue

    db.query(User).filter_by(id=user_id).delete(synchronize_session=False)
    db.commit()
    return {"deleted": True}


@router.get("/me/export")
@limiter.limit("5/hour")
def export_me(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GDPR right-to-portability. Streams a zip with one JSON file per
    user-owned model. Secrets (password hash, OAuth tokens, encrypted
    API keys) are redacted before serialisation.

    Rate-limited 5/hour to keep this endpoint from becoming a free data
    egress channel for an attacker with a stolen JWT."""
    user_id = current_user.id

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # User row first (single dict, but kept as a list for shape uniformity)
        zf.writestr("User.json", json.dumps([_row_to_dict(current_user)], indent=2))

        for cls in _resolve_models(_CASCADE_MODELS):
            try:
                rows = db.query(cls).filter_by(user_id=user_id).all()
            except Exception:
                # Best-effort: a model without user_id (shouldn't happen in
                # this list, but be defensive) gets an empty file rather
                # than aborting the whole export.
                rows = []
            zf.writestr(
                f"{cls.__name__}.json",
                json.dumps([_row_to_dict(r) for r in rows], indent=2),
            )

    buf.seek(0)
    filename = f"jarvis_export_{user_id}_{date.today().isoformat()}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
