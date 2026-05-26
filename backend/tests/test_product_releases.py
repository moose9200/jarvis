"""Tests for the Phase 1 industry product-release watcher.

Covers the two gaps that landed in the close-Phase-1 commit:

1. Decision dedupe — `run_watch_cycle` must produce at most ONE
   pending Decision row per (user, site), even when called multiple
   times. Repeated calls should refresh the existing row in place
   (title, ai_suggestion, context_json, created_at) rather than stack
   new rows.

2. `get_product_releases` AI tool dispatch — filters by site,
   `since_hours` time window, and respects the hard cap on `limit`.

We test the units directly (no TestClient / HTTP round-trip) so we
don't have to override the production `get_db` dependency. The
`db` fixture from `conftest.py` gives us a sqlite in-memory engine
with the full ORM schema, which is plenty for these checks.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from ai.tools import dispatch
from intel.product_watcher import NormalisedProduct, run_watch_cycle
from models import Decision, ProductRelease, User


def _stub_product(ext_id: str, title: str) -> NormalisedProduct:
    return NormalisedProduct(
        external_id=ext_id,
        handle=f"handle-{ext_id}",
        title=title,
        vendor="TestVendor",
        product_type="STUD",
        tags=["test"],
        price="9.99",
        image_url="https://cdn.example/img.jpg",
        url=f"https://example.com/products/handle-{ext_id}",
        created_at_remote=datetime.utcnow(),
        published_at_remote=datetime.utcnow(),
    )


def _make_user(db, uid: int = 1) -> User:
    """Seed a User row. Required so the FK on ProductRelease /
    Decision is satisfied."""
    # User model has bcrypt-hashed password — for tests we just need
    # an id, so insert with minimal columns via raw add.
    u = User(id=uid, email=f"user{uid}@test.com", password_hash="x", industry="jewellery")
    db.add(u)
    db.commit()
    return u


# ── 1. Dedupe: two run_watch_cycle calls → ONE pending Decision ────────────


def test_watch_cycle_dedupes_decision_per_site(db):
    _make_user(db, uid=1)

    products = [_stub_product("p1", "Gold Stud"), _stub_product("p2", "Silver Hoop")]

    async def stub_fetch(domain, **_):  # noqa: ARG001
        return products

    with patch("intel.product_watcher.fetch_shopify_products", new=stub_fetch):
        # First cycle — INSERT
        asyncio.run(run_watch_cycle(db, user_id=1, sites=["example.com"]))
        first = (
            db.query(Decision)
            .filter_by(user_id=1, source="product_release")
            .all()
        )
        assert len(first) == 1
        assert first[0].status == "pending"
        first_created_at = first[0].created_at
        first_id = first[0].id

        # Second cycle — should UPDATE existing row, not INSERT
        # We need to flip surfaced_to_user back to False so the
        # `unsurfaced` branch fires (in real life this would happen
        # because NEW products land between cycles; here we simulate
        # that by un-surfacing the same products).
        for r in db.query(ProductRelease).filter_by(site_domain="example.com"):
            r.surfaced_to_user = False
        db.commit()

        asyncio.run(run_watch_cycle(db, user_id=1, sites=["example.com"]))
        second = (
            db.query(Decision)
            .filter_by(user_id=1, source="product_release")
            .all()
        )
        assert len(second) == 1, "dedupe failed — got duplicate Decision rows"
        assert second[0].id == first_id, "should have UPDATED the existing row, not inserted a new one"
        # created_at bumped so it floats to top of inbox
        assert second[0].created_at >= first_created_at


# ── 2. AI tool dispatch ────────────────────────────────────────────────────


def test_get_product_releases_filters_by_since_hours(db):
    _make_user(db, uid=2)
    now = datetime.utcnow()

    # Old product (15 days back), inside the default 168h (7d) → out
    db.add(
        ProductRelease(
            user_id=2,
            site_domain="example.com",
            external_product_id="old",
            title="Old Stud",
            url="https://example.com/products/old",
            first_seen_at=now - timedelta(days=15),
            last_seen_at=now - timedelta(days=15),
        )
    )
    # Recent product (30 min ago) → in for since_hours=1
    db.add(
        ProductRelease(
            user_id=2,
            site_domain="example.com",
            external_product_id="new",
            title="Fresh Hoop",
            url="https://example.com/products/new",
            first_seen_at=now - timedelta(minutes=30),
            last_seen_at=now - timedelta(minutes=30),
        )
    )
    db.commit()

    res = asyncio.run(dispatch("get_product_releases", {"since_hours": 1}, db, user_id=2))
    assert isinstance(res, list)
    titles = [r["title"] for r in res]
    assert titles == ["Fresh Hoop"]


def test_get_product_releases_filters_by_site(db):
    _make_user(db, uid=3)
    now = datetime.utcnow()
    for site, title in [("a.com", "A-prod"), ("b.com", "B-prod")]:
        db.add(
            ProductRelease(
                user_id=3,
                site_domain=site,
                external_product_id=f"x-{site}",
                title=title,
                url=f"https://{site}/products/x",
                first_seen_at=now,
                last_seen_at=now,
            )
        )
    db.commit()

    res = asyncio.run(
        dispatch("get_product_releases", {"site": "b.com", "since_hours": 24}, db, user_id=3)
    )
    titles = [r["title"] for r in res]
    assert titles == ["B-prod"]


def test_get_product_releases_respects_hard_cap(db):
    _make_user(db, uid=4)
    now = datetime.utcnow()
    for i in range(75):
        db.add(
            ProductRelease(
                user_id=4,
                site_domain="example.com",
                external_product_id=f"p{i}",
                title=f"Item {i}",
                url=f"https://example.com/products/p{i}",
                first_seen_at=now - timedelta(minutes=i),
                last_seen_at=now,
            )
        )
    db.commit()

    res = asyncio.run(
        dispatch("get_product_releases", {"limit": 999, "since_hours": 24}, db, user_id=4)
    )
    assert len(res) == 50  # hard cap from the dispatch code


def test_get_product_releases_returns_empty_without_user(db):
    res = asyncio.run(dispatch("get_product_releases", {}, db, user_id=None))
    assert res == []
