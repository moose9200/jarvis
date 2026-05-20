import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session

import oauth_code
from database import get_db
from models import User
from rate_limit import limiter

router = APIRouter()

SECRET_KEY = os.getenv("JWT_SECRET", "jarvis-jwt-2026")
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
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate via Bearer header only. ?token= query param is no longer
    accepted — OAuth-redirect flows must use the one-time code exchange
    (see /api/users/oauth-code + get_oauth_user)."""
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
