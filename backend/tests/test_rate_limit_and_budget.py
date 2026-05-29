"""Tests for the daily-token-budget enforcer in JarvisAI.

Covers T1-02 (close-Phase-1 plan): UserSettings.daily_token_budget was
previously tracked but never enforced. We now run a pre-call guard at
the top of JarvisAI.respond() that raises TokenBudgetExceededError
before any provider call when today's accumulated input+output tokens
already hit the budget. The chat router catches that and returns 429.

Two paths:

  1. Over-budget today → respond() must raise BEFORE the provider
     stub is called (i.e., never charge the user for the request).
  2. Under-budget → respond() runs normally and returns the stub's
     reply.

We use the in-memory sqlite `db` fixture from conftest.py and mock
the provider via patching `get_provider` (the factory) so JarvisAI
doesn't try to hit a real vendor SDK.
"""
from __future__ import annotations

import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.exceptions import TokenBudgetExceededError
from ai.jarvis_ai import JarvisAI
from ai.providers.base import AIResponse
from models import TokenUsage, User, UserSettings


# ── Helpers ───────────────────────────────────────────────────────────


def _seed_user(db, user_id: int, daily_token_budget: int) -> None:
    """Create a User + UserSettings row with the requested budget.
    BYOAK fields stay null — JarvisAI falls back to the env var,
    which the test sets to a dummy string."""
    db.add(User(id=user_id, email=f"u{user_id}@test.com", password_hash="x", industry="d2c"))
    db.add(
        UserSettings(
            user_id=user_id,
            ai_provider="anthropic",
            default_model="intelligent",
            daily_token_budget=daily_token_budget,
        )
    )
    db.commit()


def _seed_usage(db, user_id: int, input_tokens: int, output_tokens: int) -> None:
    db.add(
        TokenUsage(
            user_id=user_id,
            date=date.today().isoformat(),
            provider="anthropic",
            model="claude-sonnet-4-6",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0,
        )
    )
    db.commit()


def _mock_provider() -> MagicMock:
    """A provider stub whose `complete()` returns a trivial AIResponse.
    JarvisAI calls `get_provider(name, key)` which we patch to return
    this object."""
    p = MagicMock()
    p.complete = AsyncMock(
        return_value=AIResponse(
            text="ok",
            input_tokens=1,
            output_tokens=1,
            stop_reason="end_turn",
        )
    )
    return p


# ── Tests ─────────────────────────────────────────────────────────────


def test_budget_enforcer_raises_when_over_limit(db, monkeypatch):
    """When today's input+output >= daily_token_budget, respond() must
    raise TokenBudgetExceededError BEFORE the provider is touched."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")

    _seed_user(db, user_id=1, daily_token_budget=10)
    _seed_usage(db, user_id=1, input_tokens=7, output_tokens=5)  # 12 > 10

    provider = _mock_provider()
    with patch("ai.jarvis_ai.get_provider", return_value=provider):
        client = JarvisAI(db, user_id=1)

        with pytest.raises(TokenBudgetExceededError) as exc:
            asyncio.run(client.respond("hello"))

    # Carries budget + used for the router's 429 detail message
    assert exc.value.budget == 10
    assert exc.value.used == 12
    # Provider must NOT have been called — we deny BEFORE the call
    provider.complete.assert_not_called()


def test_budget_allows_under_limit(db, monkeypatch):
    """When today's input+output < daily_token_budget, respond() runs
    normally and returns the provider's reply."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")

    _seed_user(db, user_id=2, daily_token_budget=100_000)
    _seed_usage(db, user_id=2, input_tokens=5, output_tokens=5)  # 10 << 100k

    provider = _mock_provider()
    with patch("ai.jarvis_ai.get_provider", return_value=provider):
        client = JarvisAI(db, user_id=2)
        out = asyncio.run(client.respond("hello"))

    assert out["text"] == "ok"
    provider.complete.assert_awaited_once()


def test_budget_zero_means_unlimited(db, monkeypatch):
    """A budget of 0 should be treated as 'no limit' so legacy users
    whose settings row pre-dates the budget feature aren't blocked."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")

    _seed_user(db, user_id=3, daily_token_budget=0)
    _seed_usage(db, user_id=3, input_tokens=999_999, output_tokens=999_999)

    provider = _mock_provider()
    with patch("ai.jarvis_ai.get_provider", return_value=provider):
        client = JarvisAI(db, user_id=3)
        out = asyncio.run(client.respond("hello"))

    assert out["text"] == "ok"
    provider.complete.assert_awaited_once()
