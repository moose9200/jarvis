"""Tests for GDPR/CCPA account routes (T1-05 from the close-Phase-1 plan).

Two endpoints under test:
  - DELETE /api/users/me     — cascade-deletes everything user-owned
  - GET    /api/users/me/export — streams a zip of everything user-owned

The auth dependency is replaced via FastAPI's dependency-override pattern
(same approach as test_feed.py) so we don't have to mint a JWT. The
database dependency is also overridden so the route uses the same
in-memory sqlite session the test seeded.
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models import Decision, TokenUsage, User, UserSettings, OAuthToken
from rate_limit import limiter
from routers.users import get_current_user


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def gdpr_db():
    """Dedicated sqlite DB shared between the test and the FastAPI app
    via dependency override. We use `StaticPool` so every connection
    shares the SAME in-memory database — without it, the test seeds
    one DB and the request thread opens a fresh empty one."""
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
def client(gdpr_db):
    """TestClient with auth + db dependencies overridden. We seed the
    user inside each test (and re-pin the override to point at the same
    user row) — most GDPR cases need to vary which user is current.

    Also resets slowapi's storage between tests so the 3/hour DELETE and
    5/hour export limits don't carry over from previous test runs."""
    limiter.reset()
    app.dependency_overrides[get_db] = lambda: gdpr_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        limiter.reset()


def _seed_user(db, *, user_id: int = 1, email: str = "alice@example.com") -> User:
    u = User(id=user_id, email=email, password_hash="hashed", industry="d2c")
    db.add(u)
    db.commit()
    db.refresh(u)
    app.dependency_overrides[get_current_user] = lambda: u
    return u


# ── DELETE /api/users/me ─────────────────────────────────────────────


def test_delete_me_requires_email_confirm(client, gdpr_db):
    """Body must be the user's exact email. Anything else → 400, and
    the user row stays in the DB."""
    user = _seed_user(gdpr_db, user_id=11, email="alice@example.com")

    # Wrong email → 400
    r = client.request(
        "DELETE",
        "/api/users/me",
        json={"confirm": "wrong@example.com"},
    )
    assert r.status_code == 400
    assert "does not match" in r.json().get("detail", "").lower()
    # User row must still exist
    assert gdpr_db.query(User).filter_by(id=11).first() is not None

    # Right email → 200, user gone
    r = client.request(
        "DELETE",
        "/api/users/me",
        json={"confirm": "alice@example.com"},
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"deleted": True}
    gdpr_db.expire_all()
    assert gdpr_db.query(User).filter_by(id=11).first() is None


def test_delete_me_cascades(client, gdpr_db):
    """Owned child rows (UserSettings, TokenUsage, Decision) must all
    disappear when the user is deleted."""
    user = _seed_user(gdpr_db, user_id=22, email="bob@example.com")

    gdpr_db.add(UserSettings(user_id=22, daily_token_budget=50_000))
    gdpr_db.add(
        TokenUsage(
            user_id=22,
            date=date.today().isoformat(),
            provider="anthropic",
            model="claude-sonnet-4-6",
            input_tokens=10,
            output_tokens=20,
            cost_usd=0.001,
        )
    )
    gdpr_db.add(
        Decision(
            user_id=22,
            source="github_pr",
            title="Test PR",
            context_json={"x": 1},
            status="pending",
        )
    )
    gdpr_db.commit()

    # sanity: rows present
    assert gdpr_db.query(UserSettings).filter_by(user_id=22).count() == 1
    assert gdpr_db.query(TokenUsage).filter_by(user_id=22).count() == 1
    assert gdpr_db.query(Decision).filter_by(user_id=22).count() == 1

    r = client.request(
        "DELETE",
        "/api/users/me",
        json={"confirm": "bob@example.com"},
    )
    assert r.status_code == 200, r.text

    gdpr_db.expire_all()
    assert gdpr_db.query(User).filter_by(id=22).first() is None
    assert gdpr_db.query(UserSettings).filter_by(user_id=22).count() == 0
    assert gdpr_db.query(TokenUsage).filter_by(user_id=22).count() == 0
    assert gdpr_db.query(Decision).filter_by(user_id=22).count() == 0


# ── GET /api/users/me/export ─────────────────────────────────────────


def test_export_me_returns_zip(client, gdpr_db):
    """Export returns application/zip with one JSON file per owned model,
    and secrets are redacted in the dump."""
    user = _seed_user(gdpr_db, user_id=33, email="carol@example.com")

    gdpr_db.add(
        UserSettings(
            user_id=33,
            daily_token_budget=100_000,
            anthropic_api_key_encrypted="ENC:super-secret-blob",
        )
    )
    gdpr_db.add(
        OAuthToken(
            provider="gmail",
            user_id=33,
            access_token="ya29.live-access-token-do-not-leak",
            refresh_token="1//live-refresh-token",
        )
    )
    gdpr_db.add(
        Decision(
            user_id=33,
            source="shopify_order",
            title="Order #1234",
            context_json={"price": "$25"},
        )
    )
    gdpr_db.commit()

    r = client.get("/api/users/me/export")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/zip"
    assert "jarvis_export_33_" in r.headers.get("content-disposition", "")

    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = set(zf.namelist())
    # Sanity: the user row and at least the owned tables we seeded are present
    assert "User.json" in names
    assert "UserSettings.json" in names
    assert "OAuthToken.json" in names
    assert "Decision.json" in names

    # Secrets must be redacted
    user_dump = json.loads(zf.read("User.json"))
    assert user_dump[0]["email"] == "carol@example.com"
    assert user_dump[0]["password_hash"] == "<redacted>"

    settings_dump = json.loads(zf.read("UserSettings.json"))
    assert settings_dump[0]["anthropic_api_key_encrypted"] == "<redacted>"
    assert settings_dump[0]["daily_token_budget"] == 100_000  # non-secret kept

    oauth_dump = json.loads(zf.read("OAuthToken.json"))
    assert oauth_dump[0]["access_token"] == "<redacted>"
    assert oauth_dump[0]["refresh_token"] == "<redacted>"
    assert oauth_dump[0]["provider"] == "gmail"  # non-secret kept

    decisions_dump = json.loads(zf.read("Decision.json"))
    assert decisions_dump[0]["title"] == "Order #1234"
