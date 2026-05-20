"""rename personality_mode "caveman" → "coder" + new default "all_purpose"

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-20

JARVIS used to ship with `caveman` as the default personality (drop articles,
fragments, terse). The persona system is being renamed to "skills":
  - "caveman" is now "coder" (it was always our coder mode in disguise)
  - the new default is `all_purpose` (balanced general assistant)
  - 9 additional skills land: designer, writer, marketer, founder,
    researcher, analyst, coach, devils_advocate, creative

This migration:
  1. Updates server_default on user_settings.personality_mode to "all_purpose"
  2. Bulk-renames existing rows: "caveman" → "coder", "expert" → "researcher",
     "executive" → "founder" (so legacy modes don't disappear silently).
  3. Leaves all other personality values untouched.

backend/ai/persona.py also keeps _LEGACY_ALIAS so if any stale row sneaks
through, build_system_prompt() still does the right thing.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Server default — affects rows inserted by raw SQL outside the app.
    op.alter_column(
        "user_settings",
        "personality_mode",
        server_default="all_purpose",
        existing_type=sa.String(),
        existing_nullable=True,
    )

    # Rename existing values so legacy mode strings still match a real skill.
    op.execute("UPDATE user_settings SET personality_mode = 'coder'      WHERE personality_mode = 'caveman'")
    op.execute("UPDATE user_settings SET personality_mode = 'researcher' WHERE personality_mode = 'expert'")
    op.execute("UPDATE user_settings SET personality_mode = 'founder'    WHERE personality_mode = 'executive'")


def downgrade() -> None:
    op.execute("UPDATE user_settings SET personality_mode = 'caveman'   WHERE personality_mode = 'coder'")
    op.execute("UPDATE user_settings SET personality_mode = 'expert'    WHERE personality_mode = 'researcher'")
    op.execute("UPDATE user_settings SET personality_mode = 'executive' WHERE personality_mode = 'founder'")

    op.alter_column(
        "user_settings",
        "personality_mode",
        server_default="caveman",
        existing_type=sa.String(),
        existing_nullable=True,
    )
