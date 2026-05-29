"""Tests for the Phase 3 celebrity / influencer mention watcher.

Covers:

1. Dedupe — `run_mention_cycle` must produce at most ONE pending
   Decision row per user even when called multiple times against the
   same upstream items. The second call should only refresh the
   existing row in place. Per-URL `mentions` rows must also be
   idempotent thanks to the (url, user_id) unique constraint.

2. `get_recent_mentions` AI tool dispatch — filters by `since_hours`
   and respects the hard cap on `limit`.

Network calls are mocked: fetch_google_news, fetch_rss, and the
fetchers.fetch_reddit dependency are all swapped for deterministic
stubs so the tests run offline.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch

from ai.tools import dispatch
from intel.mention_watcher import run_mention_cycle
from models import Decision, Mention, User


def _make_user(db, uid: int = 1, industry: str = "jewellery") -> User:
    u = User(id=uid, email=f"user{uid}@test.com", password_hash="x", industry=industry)
    db.add(u)
    db.commit()
    return u


async def _stub_google(query: str, limit: int = 25):  # noqa: ARG001
    return [
        {
            "source": "google_news",
            "title": f"Celebrity X spotted wearing studs ({query})",
            "url": f"https://news.google.com/articles/celeb-{query.replace(' ', '-')}",
            "summary": "Press piece about a celeb wearing piercings.",
            "score": 0,
            "author": "Some Reporter",
            "created_at": None,
            "comments": 0,
        }
    ]


async def _stub_rss(feed_url: str, limit: int = 25):  # noqa: ARG001
    return [
        {
            "source": "rss:painmag.com",
            "title": "Trade press item",
            "url": "https://www.painmag.com/articles/trade-item-1",
            "summary": "An article from a trade press feed.",
            "score": 0,
            "author": None,
            "created_at": None,
            "comments": 0,
        }
    ]


async def _stub_reddit(sub: str, limit: int = 20):  # noqa: ARG001
    return [
        {
            "source": f"reddit:r/{sub}",
            "title": f"Celebrity Kardashian spotted wearing new piercings ({sub})",
            "url": f"https://reddit.com/r/{sub}/comments/abc123",
            "summary": "Some celebrity content.",
            "score": 42,
            "author": "u/redditor",
            "created_at": None,
            "comments": 7,
        }
    ]


# ── 1. Dedupe behaviour ────────────────────────────────────────────────────


def test_mention_cycle_dedupes_decision_per_user(db):
    _make_user(db, uid=1, industry="jewellery")

    with patch("intel.mention_watcher.fetch_google_news", new=_stub_google), \
         patch("intel.mention_watcher.fetch_rss", new=_stub_rss), \
         patch("intel.mention_watcher.fetch_reddit", new=_stub_reddit):
        # First cycle — INSERT
        result1 = asyncio.run(run_mention_cycle(db, user_id=1))
        assert result1["new_rows"] >= 1, "first cycle should insert new mentions"

        decisions_after_first = (
            db.query(Decision)
            .filter_by(user_id=1, source="mention")
            .all()
        )
        assert len(decisions_after_first) == 1
        assert decisions_after_first[0].status == "pending"
        first_decision_id = decisions_after_first[0].id

        # Second cycle — identical upstream items.
        # Per-URL unique constraint should prevent duplicate mentions,
        # and the Decision dedupe means we still have exactly ONE row.
        # (No new mentions → no Decision refresh, which is fine —
        # the existing row stays around for the user to action.)
        asyncio.run(run_mention_cycle(db, user_id=1))

        decisions_after_second = (
            db.query(Decision)
            .filter_by(user_id=1, source="mention")
            .all()
        )
        assert len(decisions_after_second) == 1, (
            "dedupe failed — got duplicate Decision rows for the same user"
        )
        assert decisions_after_second[0].id == first_decision_id

        # And mentions themselves should also be deduped per URL
        mention_urls = [m.url for m in db.query(Mention).filter_by(user_id=1).all()]
        assert len(mention_urls) == len(set(mention_urls)), (
            "mentions table got duplicate URLs for the same user"
        )


def test_mention_cycle_refreshes_decision_on_new_items(db):
    """If a second cycle surfaces NEW mentions, the existing Decision
    row should be UPDATED in place (id stable, created_at bumped), not
    duplicated."""
    _make_user(db, uid=2, industry="piercing")

    call_count = {"n": 0}

    async def stub_google_growing(query: str, limit: int = 25):  # noqa: ARG001
        call_count["n"] += 1
        idx = call_count["n"]
        return [
            {
                "source": "google_news",
                "title": f"Celeb story #{idx}",
                "url": f"https://news.google.com/articles/celeb-story-{idx}",
                "summary": "",
                "score": 0,
                "author": None,
                "created_at": None,
                "comments": 0,
            }
        ]

    async def empty(*_args, **_kwargs):
        return []

    with patch("intel.mention_watcher.fetch_google_news", new=stub_google_growing), \
         patch("intel.mention_watcher.fetch_rss", new=empty), \
         patch("intel.mention_watcher.fetch_reddit", new=empty):
        asyncio.run(run_mention_cycle(db, user_id=2))
        decision_first = (
            db.query(Decision).filter_by(user_id=2, source="mention").one()
        )
        first_id = decision_first.id
        first_created_at = decision_first.created_at

        # Tiny pause via timedelta substitution — we can just call again
        # since stub_google_growing returns a NEW url on call #2.
        asyncio.run(run_mention_cycle(db, user_id=2))

        decisions = (
            db.query(Decision).filter_by(user_id=2, source="mention").all()
        )
        assert len(decisions) == 1, "Decision was duplicated instead of refreshed"
        assert decisions[0].id == first_id
        assert decisions[0].created_at >= first_created_at


# ── 2. AI tool dispatch ────────────────────────────────────────────────────


def test_get_recent_mentions_filters_by_since_hours(db):
    _make_user(db, uid=3, industry="jewellery")
    now = datetime.utcnow()

    db.add(
        Mention(
            user_id=3,
            source="google_news",
            title="Ancient mention",
            url="https://news.google.com/articles/old",
            first_seen_at=now - timedelta(days=15),
        )
    )
    db.add(
        Mention(
            user_id=3,
            source="google_news",
            title="Fresh mention",
            url="https://news.google.com/articles/new",
            first_seen_at=now - timedelta(minutes=30),
        )
    )
    db.commit()

    res = asyncio.run(
        dispatch("get_recent_mentions", {"since_hours": 1}, db, user_id=3)
    )
    assert isinstance(res, list)
    titles = [r["title"] for r in res]
    assert titles == ["Fresh mention"]


def test_get_recent_mentions_respects_hard_cap(db):
    _make_user(db, uid=4, industry="tattoo")
    now = datetime.utcnow()
    for i in range(50):
        db.add(
            Mention(
                user_id=4,
                source="google_news",
                title=f"Item {i}",
                url=f"https://news.google.com/articles/item-{i}",
                first_seen_at=now - timedelta(minutes=i),
            )
        )
    db.commit()

    res = asyncio.run(
        dispatch(
            "get_recent_mentions",
            {"limit": 999, "since_hours": 24},
            db,
            user_id=4,
        )
    )
    assert len(res) == 30  # hard cap from the dispatch code


def test_get_recent_mentions_returns_empty_without_user(db):
    res = asyncio.run(dispatch("get_recent_mentions", {}, db, user_id=None))
    assert res == []
