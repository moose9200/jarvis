import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from main import app
from models import User
from routers.users import get_current_user


def _fake_user() -> User:
    """Stand-in user so authenticated routes return 200 without minting a
    real JWT in tests. We don't care about persistence here — these routes
    only need `current_user.id` for downstream queries."""
    return User(id=1, email="test@x.com", password_hash="x", industry="test")


@pytest.fixture()
def client():
    app.dependency_overrides[get_current_user] = _fake_user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@patch("routers.feed.NotionConnector")
@patch("routers.feed.JiraConnector")
@patch("routers.feed.LinearConnector")
@patch("routers.feed.GitHubConnector")
@patch("routers.feed.WhatsAppConnector")
@patch("routers.feed.TeamsConnector")
@patch("routers.feed.SlackConnector")
@patch("routers.feed.OutlookCalendarConnector")
@patch("routers.feed.GoogleCalendarConnector")
@patch("routers.feed.OutlookMailConnector")
@patch("routers.feed.GmailConnector")
def test_feed_aggregates_and_sorts(gm, om, gc, oc, sl, tm, wa, gh, ln, jr, nt, client):
    def make(items):
        inst = AsyncMock()
        inst.fetch = AsyncMock(return_value=items)
        return inst

    gm.return_value = make([{
        "id": "g1", "from": "a@x", "subject": "URGENT deadline", "snippet": "now",
        "received": "2026-05-19T12:00:00Z", "thread_id": "t", "unread": True, "source": "gmail",
    }])
    om.return_value = make([{
        "id": "o1", "from": "b@x", "subject": "newsletter", "snippet": "",
        "received": "2026-05-15T08:00:00Z", "thread_id": "t2", "unread": False, "source": "outlook",
    }])
    gc.return_value = make([{"id": "e1", "title": "Standup", "start": "2026-05-19T09:00:00Z", "end": "", "source": "google"}])
    oc.return_value = make([])
    sl.return_value = make([{"id": "s1", "from": "u1", "text": "hi", "channel": "general", "received": "0", "source": "slack"}])
    tm.return_value = make([])
    wa.return_value = make([])
    gh.return_value = make([{"id": "gh1", "title": "PR review", "status": "PullRequest", "url": "", "due": None, "source": "github"}])
    ln.return_value = make([{"id": "l1", "title": "DEV-1 ship it", "status": "In Progress", "due": None, "url": "", "source": "linear"}])
    jr.return_value = make([])
    nt.return_value = make([])

    r = client.get("/api/feed")
    assert r.status_code == 200
    data = r.json()
    assert len(data["events"]) == 1
    assert data["emails"][0]["id"] == "g1"
    assert data["messages"][0]["source"] == "slack"
    assert data["tasks"][0]["source"] == "linear"
    assert data["projects"][0]["source"] == "github"


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_feed_cache_short_circuits(client):
    """When Redis returns a cached payload, the connectors should NOT
    be hit at all. We confirm by patching one connector to raise on
    fetch — the request should still 200 because we never called it."""
    from routers import feed as _feed

    if _feed._cache is None:
        pytest.skip("REDIS_URL not configured in test env")

    cached_payload = {
        "events": [],
        "emails": [],
        "messages": [],
        "tasks": [],
        "projects": [],
    }
    import json as _json_inner
    _feed._cache.setex("feed:1", 30, _json_inner.dumps(cached_payload))
    try:
        with patch("routers.feed.GmailConnector") as gm:
            gm.return_value.fetch = AsyncMock(side_effect=Exception("must not be called"))
            r = client.get("/api/feed")
            assert r.status_code == 200
            data = r.json()
            assert data == cached_payload
            # If we got here without raising, the connector mock was not invoked.
            gm.return_value.fetch.assert_not_called()
    finally:
        _feed._cache.delete("feed:1")
