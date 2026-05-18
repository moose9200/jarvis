import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from main import app


@pytest.fixture()
def client():
    return TestClient(app)


@patch("routers.chat.JarvisClaude")
def test_chat_returns_reply(MockClaude, client):
    instance = MockClaude.return_value
    instance.respond = AsyncMock(return_value="Boss, 3 priority emails.")
    r = client.post("/api/chat", json={"message": "what's my inbox look like"})
    assert r.status_code == 200
    assert r.json()["reply"].startswith("Boss")
    instance.respond.assert_awaited_once_with("what's my inbox look like")


@patch("routers.chat.JarvisClaude")
def test_chat_rejects_missing_body(MockClaude, client):
    r = client.post("/api/chat", json={})
    assert r.status_code == 422
