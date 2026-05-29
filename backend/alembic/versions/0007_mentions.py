"""mentions table for celebrity / influencer / press mention monitoring

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-29

Adds the `mentions` table used by the Phase 3 celebrity / influencer
watcher (backend/intel/mention_watcher.py +
backend/tasks/mention_watcher.py).

One row per (user_id, url). The unique constraint keeps re-fetches
idempotent — the watcher upserts on every run, and only surfaces a
Decision row the first time a URL is observed for a user.

Sources captured today: Google News RSS, generic trade-press RSS feeds,
and Reddit hot.json filtered for celebrity-noise keywords. X (paid),
Instagram, and TikTok are explicitly out of scope.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mentions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("author", sa.String(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "surfaced_to_user",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.UniqueConstraint("url", "user_id", name="uq_mentions_url_user"),
    )
    op.create_index("ix_mentions_user_id", "mentions", ["user_id"])
    op.create_index("ix_mentions_url", "mentions", ["url"])
    op.create_index("ix_mentions_first_seen_at", "mentions", ["first_seen_at"])
    op.create_index(
        "ix_mentions_surfaced_to_user", "mentions", ["surfaced_to_user"]
    )


def downgrade() -> None:
    op.drop_index("ix_mentions_surfaced_to_user", table_name="mentions")
    op.drop_index("ix_mentions_first_seen_at", table_name="mentions")
    op.drop_index("ix_mentions_url", table_name="mentions")
    op.drop_index("ix_mentions_user_id", table_name="mentions")
    op.drop_table("mentions")
