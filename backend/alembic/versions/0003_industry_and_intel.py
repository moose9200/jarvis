"""industry on user + intel_briefs + intel_brief_runs

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-20

Adds:
  - users.industry (nullable text) — free-form industry label required at
    signup. Powers default Intel Briefs.
  - intel_briefs       — saved periodic monitors ("Industry chatter", etc.)
  - intel_brief_runs   — execution history with synthesized output stored
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users.industry — nullable so existing rows survive; backfill happens
    # opportunistically when a user next opens Settings.
    op.add_column("users", sa.Column("industry", sa.String(), nullable=True))

    op.create_table(
        "intel_briefs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("prompt_template", sa.Text(), nullable=True),
        sa.Column("sources_json", sa.JSON(), nullable=True),
        sa.Column("frequency_minutes", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_intel_briefs_user_id", "intel_briefs", ["user_id"])

    op.create_table(
        "intel_brief_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("brief_id", sa.Integer(), sa.ForeignKey("intel_briefs.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=True, server_default="pending"),
        sa.Column("output_text", sa.Text(), nullable=True),
        sa.Column("sources_summary", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True, server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_intel_brief_runs_brief_id", "intel_brief_runs", ["brief_id"])
    op.create_index("ix_intel_brief_runs_user_id", "intel_brief_runs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_intel_brief_runs_user_id", "intel_brief_runs")
    op.drop_index("ix_intel_brief_runs_brief_id", "intel_brief_runs")
    op.drop_table("intel_brief_runs")

    op.drop_index("ix_intel_briefs_user_id", "intel_briefs")
    op.drop_table("intel_briefs")

    op.drop_column("users", "industry")
