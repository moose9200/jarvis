"""T1-11/A — auth + user CRUD coverage for `backend/routers/users.py`.

Exercises register / login / me / set_industry / oauth-code. Skips the
GDPR delete + export routes (already covered by `test_users_gdpr.py`).

Pattern follows `test_users_gdpr.py`: a dedicated sqlite DB with
`StaticPool` so the test thread and the request thread see the same
rows, plus FastAPI dependency overrides for `get_db` and (for
authenticated routes) `get_current_user`. We use REAL JWTs minted via
the production `_create_token` helper for the round-trip flows so the
test exercises the same auth path the live UI hits.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models import IntelBrief, User, UserContext, UserSettings
from rate_limit import limiter
from routers.users import (
    ALGORITHM,
    SECRET_KEY,
    _create_token,
    _hash,
    get_current_user,
)


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def auth_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def client(auth_db):
    """TestClient with `get_db` overridden + slowapi reset.

    `get_current_user` is NOT pinned here — individual tests either:
      - send a real Bearer token (mints via `_create_token`) — exercises
        the JWT path end-to-end
      - pin `get_current_user` themselves with `_seed_authed_user`
    """
    limiter.reset()
    app.dependency_overrides[get_db] = lambda: auth_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        limiter.reset()


def _seed_authed_user(db, *, user_id: int = 1, email: str = "alice@example.com") -> User:
    """Seed a user + pin `get_current_user` to return them. Returns the
    row for the test to inspect."""
    u = User(id=user_id, email=email, password_hash=_hash("Strong#123"), industry="d2c")
    db.add(u)
    db.commit()
    db.refresh(u)
    app.dependency_overrides[get_current_user] = lambda: u
    return u


# ── POST /api/users/register ─────────────────────────────────────────


def test_register_creates_user_and_returns_jwt(client, auth_db):
    r = client.post("/api/users/register", json={
        "email": "new@example.com",
        "password": "Strong#123",
        "industry": "tattoo supplies",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    # Token must round-trip through jose with our SECRET
    payload = jose_jwt.decode(body["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["email"] == "new@example.com"

    row = auth_db.query(User).filter_by(email="new@example.com").first()
    assert row is not None
    assert row.industry == "tattoo supplies"
    # Password must NEVER be stored in plaintext
    assert row.password_hash != "Strong#123"


def test_register_duplicate_email_400(client, auth_db):
    auth_db.add(User(email="dup@example.com", password_hash=_hash("x"), industry="x2"))
    auth_db.commit()
    # industry must be >= 2 chars to clear Pydantic validation — otherwise
    # we get 422 before the duplicate-email check ever runs.
    r = client.post("/api/users/register", json={
        "email": "dup@example.com",
        "password": "Strong#123",
        "industry": "x2",
    })
    assert r.status_code == 400
    assert "already" in r.json().get("detail", "").lower()


def test_register_provisions_defaults(client, auth_db):
    """A brand-new user must get UserSettings, UserContext, and (if they
    gave an industry) a default IntelBrief — so /me, /context, and the
    intel-briefs panel never 404 on first login."""
    r = client.post("/api/users/register", json={
        "email": "fresh@example.com",
        "password": "Strong#123",
        "industry": "piercing",
    })
    assert r.status_code == 200, r.text
    user = auth_db.query(User).filter_by(email="fresh@example.com").first()
    assert user is not None

    assert auth_db.query(UserSettings).filter_by(user_id=user.id).count() == 1
    assert auth_db.query(UserContext).filter_by(user_id=user.id).count() == 1
    briefs = auth_db.query(IntelBrief).filter_by(user_id=user.id).all()
    assert len(briefs) == 1
    assert briefs[0].topic == "piercing"


# ── POST /api/users/login ────────────────────────────────────────────


def test_login_happy_path_returns_jwt(client, auth_db):
    auth_db.add(User(email="login@example.com", password_hash=_hash("Strong#123"), industry="x"))
    auth_db.commit()
    r = client.post("/api/users/login", json={
        "email": "login@example.com",
        "password": "Strong#123",
    })
    assert r.status_code == 200, r.text
    payload = jose_jwt.decode(r.json()["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["email"] == "login@example.com"


def test_login_wrong_password_401(client, auth_db):
    auth_db.add(User(email="wp@example.com", password_hash=_hash("Strong#123"), industry="x"))
    auth_db.commit()
    r = client.post("/api/users/login", json={
        "email": "wp@example.com",
        "password": "wrongpassword",
    })
    assert r.status_code == 401


def test_login_nonexistent_email_401(client, auth_db):
    r = client.post("/api/users/login", json={
        "email": "ghost@example.com",
        "password": "anything",
    })
    assert r.status_code == 401


# ── GET /api/users/me — JWT round-trip ───────────────────────────────


def test_me_requires_jwt_401(client):
    """No Authorization header → 401. Sanity check that the auth gate
    actually fires when we DON'T override `get_current_user`."""
    r = client.get("/api/users/me")
    assert r.status_code == 401


def test_me_returns_current_user_with_valid_jwt(client, auth_db):
    """Mint a real JWT for a seeded user, send it as Bearer, expect the
    /me payload to come back. Exercises the production JWT-decode path."""
    user = User(email="me@example.com", password_hash=_hash("Strong#123"), industry="d2c")
    auth_db.add(user)
    auth_db.commit()
    auth_db.refresh(user)

    token = _create_token(user.id, user.email)
    r = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == user.id
    assert body["email"] == user.email
    assert body["industry"] == "d2c"


def test_me_rejects_expired_jwt_401(client, auth_db):
    """A token with an `exp` claim in the past must come back 401 — proves
    the signature isn't the only thing being checked."""
    user = User(id=42, email="exp@example.com", password_hash=_hash("x"), industry="x")
    auth_db.add(user)
    auth_db.commit()

    expired_payload = {
        "sub": "42",
        "email": "exp@example.com",
        "exp": datetime.utcnow() - timedelta(minutes=5),
    }
    expired_token = jose_jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
    r = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert r.status_code == 401


def test_me_rejects_garbled_jwt_401(client):
    r = client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert r.status_code == 401


# ── PUT /api/users/me/industry ───────────────────────────────────────


def test_set_industry_updates_and_returns_user(client, auth_db):
    user = _seed_authed_user(auth_db, user_id=7, email="industry@example.com")
    # Wipe the seeded industry so we can prove the route writes one
    user.industry = None
    auth_db.commit()

    r = client.put("/api/users/me/industry", json={"industry": "jewellery wholesale"})
    assert r.status_code == 200, r.text
    assert r.json()["industry"] == "jewellery wholesale"

    auth_db.expire_all()
    assert auth_db.query(User).get(7).industry == "jewellery wholesale"


def test_set_industry_provisions_brief_after_first_industry_set(client, auth_db):
    """First-time industry set on a legacy user must seed the default
    IntelBrief — same as register's `_provision_defaults`."""
    user = _seed_authed_user(auth_db, user_id=8, email="legacy@example.com")
    user.industry = None
    auth_db.commit()
    # No briefs yet
    assert auth_db.query(IntelBrief).filter_by(user_id=8).count() == 0

    r = client.put("/api/users/me/industry", json={"industry": "tattoo supplies"})
    assert r.status_code == 200, r.text

    auth_db.expire_all()
    briefs = auth_db.query(IntelBrief).filter_by(user_id=8).all()
    assert len(briefs) == 1
    assert briefs[0].topic == "tattoo supplies"


# ── POST /api/users/oauth-code ───────────────────────────────────────


def test_oauth_code_mint_returns_string(client, auth_db):
    """The endpoint hands back a single-use code that the frontend can
    safely embed in an OAuth /start URL. We just verify the shape — the
    `oauth_code.issue`/`consume` cycle has its own tests."""
    _seed_authed_user(auth_db, user_id=11, email="oauth@example.com")
    r = client.post("/api/users/oauth-code")
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body.get("code"), str)
    assert len(body["code"]) >= 16  # codes are reasonably long
