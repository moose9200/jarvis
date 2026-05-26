"""backfill industry briefs + fix user 15 industry

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-26

Two coupled data fixes for the Phase 1 industry monitor:

1. User 15 was created with industry='na' (placeholder during early
   testing) but is actually a jewellery account. Correct the row so
   the per-user product-watcher fan-out (tasks/product_watcher.py
   INDUSTRY_KEYWORDS gate) picks them up.

2. Auto-provisioned IntelBriefs (name='Industry chatter') predate the
   jewellery/piercing/tattoo keyword groups added to
   intel.fetchers.default_sources_for_industry on 2026-05-26. Their
   sources_json still references the OLD generic defaults
   (Entrepreneur/smallbusiness/startups, etc). We re-derive the
   expected sources for each affected brief and update only those that
   still match a known canned default — user-customised briefs (any
   reddit list NOT in CANNED_OLD_DEFAULTS) are left alone.

Idempotent. The user-15 guard (`AND industry='na'`) and the
'matches a canned old default' guard both make re-runs no-ops.

Down-migration cannot be inferred (we don't store prior values), so
downgrade() is a logged no-op.
"""
from __future__ import annotations

import json
import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.0006")

# Sets of reddit subreddit lists that we know were produced by an
# older version of default_sources_for_industry (i.e. the user did
# NOT customise — safe to overwrite). Each entry is a frozenset so we
# can compare regardless of order.
CANNED_OLD_DEFAULTS: list[frozenset[str]] = [
    frozenset({"Entrepreneur", "smallbusiness", "startups"}),         # base / fallback
    frozenset({"SaaS", "startups", "Entrepreneur"}),                  # saas
    frozenset({"ecommerce", "shopify", "smallbusiness"}),             # ecommerce / d2c
    frozenset({"skincareaddiction", "ecommerce", "smallbusiness"}),   # botanical / skincare
    frozenset({"fintech", "startups", "personalfinance"}),            # fintech
    frozenset({"LocalLLaMA", "MachineLearning", "OpenAI"}),           # ai
    frozenset({"webdev", "programming", "javascript"}),               # developer
    frozenset({"marketing", "advertising", "growthhacking"}),         # marketing
    frozenset({"RealEstate", "realestateinvesting", "Entrepreneur"}), # real estate
    frozenset({"healthcare", "medicine", "wellness"}),                # health
]


def upgrade() -> None:
    bind = op.get_bind()

    # ── Step 1: fix user 15 industry (idempotent via guard) ────────────────
    bind.execute(
        sa.text(
            "UPDATE users SET industry = 'jewellery' "
            "WHERE id = 15 AND industry = 'na'"
        )
    )

    # ── Step 2: backfill auto-provisioned briefs that still use a canned
    # old default. Imported here (not at module top) so the migration stays
    # runnable even if intel.fetchers moves later — fail-soft.
    try:
        from intel.fetchers import default_sources_for_industry
    except Exception:
        logger.warning("0006: could not import default_sources_for_industry — skipping brief backfill")
        return

    rows = bind.execute(
        sa.text(
            """
            SELECT ib.id, ib.sources_json, u.industry
            FROM intel_briefs ib
            JOIN users u ON u.id = ib.user_id
            WHERE ib.name = 'Industry chatter'
            """
        )
    ).fetchall()

    updated = 0
    for brief_id, sources_json, industry in rows:
        if not industry:
            continue
        # sources_json may come back as a dict (psycopg2 + JSON column)
        # or a string depending on driver — normalise both.
        if isinstance(sources_json, str):
            try:
                sources_json = json.loads(sources_json)
            except json.JSONDecodeError:
                continue
        if not isinstance(sources_json, dict):
            continue

        current_reddit = sources_json.get("reddit") or []
        if not isinstance(current_reddit, list):
            continue
        current_set = frozenset(current_reddit)

        # Only touch briefs whose current reddit list matches one of the
        # known canned defaults — protects user-customised briefs.
        if current_set not in CANNED_OLD_DEFAULTS:
            continue

        new_sources = default_sources_for_industry(industry)
        if frozenset(new_sources.get("reddit") or []) == current_set:
            continue  # already matches the new default — no-op

        bind.execute(
            sa.text(
                "UPDATE intel_briefs SET sources_json = :sj WHERE id = :id"
            ),
            {"sj": json.dumps(new_sources), "id": brief_id},
        )
        updated += 1

    logger.info("0006: backfilled %d intel_briefs", updated)


def downgrade() -> None:
    # Cannot reverse a data backfill without storing prior values.
    # This migration is forward-only; a fresh downgrade would leave the
    # briefs in their post-backfill state, which is harmless.
    logger.info("0006: downgrade is a no-op — data backfill cannot be reversed")
