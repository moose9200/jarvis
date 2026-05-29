"""T1-11/D — tool dispatch coverage for `ai/tools.py`.

The dispatch fan-out is the entry point every chat-tool call lands on.
We exercise it directly (no FastAPI involved) by patching the
connector classes used inside dispatch — that lets us cover the
fall-through, error, and happy-path branches without needing live
OAuth tokens.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ai.tools import dispatch
from database import Base
from models import Mention, ProductRelease, User


# ── Shared db fixture ────────────────────────────────────────────────


@pytest.fixture()
def tdb():
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


# ── send_email — gmail succeeds ──────────────────────────────────────


def test_send_email_via_gmail(tdb):
    """Gmail.send returns True → result confirms gmail path + echoes
    recipient + subject from the input (used by the persona's read-back
    rule)."""
    with patch("ai.tools.GmailConnector") as gmail_cls:
        gmail_inst = gmail_cls.return_value
        gmail_inst.send = AsyncMock(return_value=True)
        result = asyncio.run(dispatch(
            "send_email",
            {"to": "x@y.com", "subject": "hi", "body": "body"},
            tdb,
            user_id=1,
        ))
    assert result == {"sent": True, "via": "gmail", "to": "x@y.com", "subject": "hi"}


def test_send_email_falls_back_to_outlook(tdb):
    """Gmail returns False → dispatch tries Outlook → success."""
    with patch("ai.tools.GmailConnector") as gmail_cls, \
         patch("ai.tools.OutlookMailConnector") as outlook_cls:
        gmail_cls.return_value.send = AsyncMock(return_value=False)
        outlook_cls.return_value.send = AsyncMock(return_value=True)
        result = asyncio.run(dispatch(
            "send_email",
            {"to": "x@y.com", "subject": "hi", "body": "body"},
            tdb,
            user_id=1,
        ))
    assert result["sent"] is True
    assert result["via"] == "outlook"


def test_send_email_both_fail_returns_error(tdb):
    """Both connectors return False → structured error with `sent: false`
    that the guardrail relies on."""
    with patch("ai.tools.GmailConnector") as gmail_cls, \
         patch("ai.tools.OutlookMailConnector") as outlook_cls:
        gmail_cls.return_value.send = AsyncMock(return_value=False)
        outlook_cls.return_value.send = AsyncMock(return_value=False)
        result = asyncio.run(dispatch(
            "send_email",
            {"to": "x@y.com", "subject": "hi", "body": "body"},
            tdb,
            user_id=1,
        ))
    assert result["sent"] is False
    assert "error" in result


# ── get_product_releases — pure SQLAlchemy, no connectors ───────────


def test_get_product_releases_returns_user_rows_only(tdb):
    """Only the current user's ProductRelease rows are returned. Cross-
    user isolation is critical here — these come back into the chat
    context and we must not leak between users."""
    tdb.add(User(id=1, email="me@x.com", password_hash="x", industry="jewellery"))
    tdb.add(User(id=2, email="other@x.com", password_hash="x", industry="x"))
    now = datetime.utcnow()
    tdb.add(ProductRelease(
        user_id=1, external_product_id="a", site_domain="tishlyon.com",
        title="Mine release", url="u1",
        first_seen_at=now,
    ))
    tdb.add(ProductRelease(
        user_id=2, external_product_id="b", site_domain="tishlyon.com",
        title="Other release", url="u2",
        first_seen_at=now,
    ))
    tdb.commit()

    result = asyncio.run(dispatch(
        "get_product_releases",
        {"since_hours": 24, "limit": 10},
        tdb,
        user_id=1,
    ))
    titles = [r["title"] for r in result]
    assert "Mine release" in titles
    assert "Other release" not in titles


def test_get_product_releases_respects_site_filter(tdb):
    """`site` arg narrows to a single storefront domain."""
    tdb.add(User(id=1, email="me@x.com", password_hash="x", industry="jewellery"))
    now = datetime.utcnow()
    tdb.add(ProductRelease(
        user_id=1, external_product_id="a", site_domain="tishlyon.com", title="T1", url="u1",
        first_seen_at=now,
    ))
    tdb.add(ProductRelease(
        user_id=1, external_product_id="b", site_domain="other.com", title="O1", url="u2",
        first_seen_at=now,
    ))
    tdb.commit()

    result = asyncio.run(dispatch(
        "get_product_releases",
        {"site": "tishlyon.com", "since_hours": 24, "limit": 10},
        tdb,
        user_id=1,
    ))
    titles = [r["title"] for r in result]
    assert titles == ["T1"]


def test_get_product_releases_filters_by_since_hours(tdb):
    """Items older than `since_hours` must be excluded."""
    tdb.add(User(id=1, email="me@x.com", password_hash="x", industry="jewellery"))
    now = datetime.utcnow()
    old = now - timedelta(hours=200)
    tdb.add(ProductRelease(
        user_id=1, external_product_id="recent", site_domain="x.com", title="Recent", url="r",
        first_seen_at=now,
    ))
    tdb.add(ProductRelease(
        user_id=1, external_product_id="old", site_domain="x.com", title="Old", url="o",
        first_seen_at=old,
    ))
    tdb.commit()

    result = asyncio.run(dispatch(
        "get_product_releases",
        {"since_hours": 24, "limit": 50},
        tdb,
        user_id=1,
    ))
    titles = [r["title"] for r in result]
    assert "Recent" in titles
    assert "Old" not in titles


def test_get_product_releases_no_user_returns_empty(tdb):
    """Anonymous call (no user_id) returns [] without querying."""
    result = asyncio.run(dispatch(
        "get_product_releases",
        {"since_hours": 24},
        tdb,
        user_id=None,
    ))
    assert result == []


# ── get_recent_mentions — same pattern as product releases ──────────


def test_get_recent_mentions_returns_user_rows_only(tdb):
    tdb.add(User(id=1, email="me@x.com", password_hash="x", industry="piercing"))
    tdb.add(User(id=2, email="other@x.com", password_hash="x", industry="x"))
    now = datetime.utcnow()
    tdb.add(Mention(
        user_id=1, source="google_news",
        title="Celebrity loves jewellery", url="u1",
        first_seen_at=now,
    ))
    tdb.add(Mention(
        user_id=2, source="reddit",
        title="Not for me", url="u2",
        first_seen_at=now,
    ))
    tdb.commit()

    result = asyncio.run(dispatch(
        "get_recent_mentions",
        {"since_hours": 24, "limit": 10},
        tdb,
        user_id=1,
    ))
    titles = [m["title"] for m in result]
    assert "Celebrity loves jewellery" in titles
    assert "Not for me" not in titles


def test_get_recent_mentions_no_user_returns_empty(tdb):
    result = asyncio.run(dispatch(
        "get_recent_mentions", {}, tdb, user_id=None,
    ))
    assert result == []


# ── Connector fan-out — patches the class lookup table ───────────────


def test_dispatch_get_calendar_events_combines_providers(tdb):
    """get_calendar_events should call BOTH Google + Outlook calendars
    and concatenate the results."""
    with patch("ai.tools.GoogleCalendarConnector") as gc, \
         patch("ai.tools.OutlookCalendarConnector") as oc:
        gc.return_value.fetch = AsyncMock(return_value=[{"id": "g1", "source": "google"}])
        oc.return_value.fetch = AsyncMock(return_value=[{"id": "o1", "source": "outlook"}])
        result = asyncio.run(dispatch(
            "get_calendar_events", {"days": 3}, tdb, user_id=1,
        ))
    sources = {e["source"] for e in result}
    assert sources == {"google", "outlook"}
    # Confirm the kwargs were forwarded — `days=3` must hit both fetches
    gc.return_value.fetch.assert_awaited_with(days=3)
    oc.return_value.fetch.assert_awaited_with(days=3)


def test_dispatch_get_slack_messages_calls_slack_connector(tdb):
    with patch("ai.tools.SlackConnector") as sl:
        sl.return_value.fetch = AsyncMock(return_value=[{"id": "s1"}])
        result = asyncio.run(dispatch(
            "get_slack_messages", {}, tdb, user_id=1,
        ))
    assert result == [{"id": "s1"}]
    sl.return_value.fetch.assert_awaited_once()


def test_dispatch_unknown_tool_falls_through(tdb):
    """Calling an unknown tool name MUST NOT crash. Current impl returns
    a structured error dict, which the chat loop forwards to the model
    via the tool_result block — the model then surfaces the failure to
    the user instead of pretending the tool worked."""
    result = asyncio.run(dispatch("nonexistent_tool", {}, tdb, user_id=1))
    assert isinstance(result, dict)
    assert "error" in result
    assert "nonexistent_tool" in result["error"]
