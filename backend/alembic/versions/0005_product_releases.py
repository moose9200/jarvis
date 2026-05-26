"""product_releases table for industry product monitoring

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-26

Adds the `product_releases` table used by the daily product-release
watcher (backend/intel/product_watcher.py + backend/tasks/product_watcher.py).

Each row represents a product seen on a watched Shopify-style store.
The unique (site_domain, external_product_id) constraint makes re-fetches
idempotent — the watcher upserts on every run and only surfaces a
Decision row the first time a product is observed.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_releases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("site_domain", sa.String(), nullable=False),
        sa.Column("external_product_id", sa.String(), nullable=False),
        sa.Column("handle", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("vendor", sa.String(), nullable=True),
        sa.Column("product_type", sa.String(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("price", sa.String(), nullable=True),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("created_at_remote", sa.DateTime(), nullable=True),
        sa.Column("published_at_remote", sa.DateTime(), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "last_seen_at",
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
        sa.UniqueConstraint(
            "site_domain",
            "external_product_id",
            name="uq_product_release_site_pid",
        ),
    )
    op.create_index("ix_product_releases_user_id", "product_releases", ["user_id"])
    op.create_index("ix_product_releases_site_domain", "product_releases", ["site_domain"])
    op.create_index(
        "ix_product_releases_external_product_id",
        "product_releases",
        ["external_product_id"],
    )
    op.create_index(
        "ix_product_releases_first_seen_at", "product_releases", ["first_seen_at"]
    )
    op.create_index(
        "ix_product_releases_surfaced_to_user",
        "product_releases",
        ["surfaced_to_user"],
    )


def downgrade() -> None:
    op.drop_index("ix_product_releases_surfaced_to_user", table_name="product_releases")
    op.drop_index("ix_product_releases_first_seen_at", table_name="product_releases")
    op.drop_index(
        "ix_product_releases_external_product_id", table_name="product_releases"
    )
    op.drop_index("ix_product_releases_site_domain", table_name="product_releases")
    op.drop_index("ix_product_releases_user_id", table_name="product_releases")
    op.drop_table("product_releases")
