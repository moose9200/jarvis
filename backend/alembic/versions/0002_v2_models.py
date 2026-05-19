"""v2 models — UserSettings, UserContext, TokenUsage, KnowledgeChunk,
FileUpload, Decision, ShopifyConfig, FreshdeskConfig

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-20

Adds the V2 schema for:
  - BYOAK (Bring Your Own API Key) + per-user AI configuration (UserSettings)
  - User persona for RAG (UserContext)
  - Per-message token usage + cost ledger (TokenUsage)
  - pgvector-backed RAG knowledge base (KnowledgeChunk)
  - Multimodal file uploads (FileUpload)
  - Decision inbox (Decision)
  - Shopify + Freshdesk per-user configs

Also cleans up a v1 quirk: the User.email column was previously declared with
both an explicit UniqueConstraint AND an index — we now collapse to a single
unique index, which is what `Column(..., unique=True, index=True)` should yield.

KnowledgeChunk.embedding uses pgvector's vector(1536) on Postgres. The Vector
column type is registered by the pgvector.sqlalchemy import side-effect; we
also ensure the extension exists (it's already created in 0001, but the
IF NOT EXISTS makes this self-contained).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # ── Clean up User.email index drift from 0001 ──────────────────────────
    # 0001 created both `uq_users_email` UNIQUE CONSTRAINT and a non-unique
    # `ix_users_email`. Collapse to a single unique index.
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_index("ix_users_email", table_name="users")
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── pgvector type (Postgres only) ──────────────────────────────────────
    if is_pg:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        from pgvector.sqlalchemy import Vector
        embedding_type = Vector(1536)
    else:
        embedding_type = sa.JSON()

    # ── user_settings ──────────────────────────────────────────────────────
    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("ai_provider", sa.String(), nullable=True, server_default="anthropic"),
        sa.Column("default_model", sa.String(), nullable=True, server_default="intelligent"),
        sa.Column("response_length", sa.String(), nullable=True, server_default="detailed"),
        sa.Column("personality_mode", sa.String(), nullable=True, server_default="caveman"),
        sa.Column("daily_token_budget", sa.Integer(), nullable=True, server_default="100000"),
        sa.Column("budget_alert_pct", sa.Integer(), nullable=True, server_default="80"),
        sa.Column("anthropic_api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("openai_api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("groq_api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("mistral_api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("google_api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("elevenlabs_api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("github_repo_url", sa.String(), nullable=True),
        sa.Column("github_pat_encrypted", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # ── user_context ───────────────────────────────────────────────────────
    op.create_table(
        "user_context",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("about_me", sa.Text(), nullable=True),
        sa.Column("communication_style", sa.Text(), nullable=True),
        sa.Column("priorities", sa.Text(), nullable=True),
        sa.Column("team_members", sa.JSON(), nullable=True),
        sa.Column("business_context", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # ── token_usage ────────────────────────────────────────────────────────
    op.create_table(
        "token_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.String(), nullable=True),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("cache_read_tokens", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("cache_write_tokens", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("thinking_tokens", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_token_usage_user_id", "token_usage", ["user_id"])
    op.create_index("ix_token_usage_date", "token_usage", ["date"])
    op.create_index("ix_token_usage_created_at", "token_usage", ["created_at"])

    # ── knowledge_chunks ───────────────────────────────────────────────────
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source_type", sa.String(), nullable=True),
        sa.Column("source_id", sa.String(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", embedding_type, nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_knowledge_chunks_user_id", "knowledge_chunks", ["user_id"])
    op.create_index("ix_knowledge_chunks_source_type", "knowledge_chunks", ["source_type"])

    # ── file_uploads ───────────────────────────────────────────────────────
    op.create_table(
        "file_uploads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.String(), nullable=True),
        sa.Column("file_type", sa.String(), nullable=True),
        sa.Column("s3_key", sa.String(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("processed", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_file_uploads_user_id", "file_uploads", ["user_id"])

    # ── decisions ──────────────────────────────────────────────────────────
    op.create_table(
        "decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("source_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("context_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=True, server_default="pending"),
        sa.Column("ai_suggestion", sa.Text(), nullable=True),
        sa.Column("snoozed_until", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_decisions_user_id", "decisions", ["user_id"])
    op.create_index("ix_decisions_status", "decisions", ["status"])

    # ── shopify_configs ────────────────────────────────────────────────────
    op.create_table(
        "shopify_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("shop_domain", sa.String(), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    # ── freshdesk_configs ──────────────────────────────────────────────────
    op.create_table(
        "freshdesk_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("subdomain", sa.String(), nullable=True),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("freshdesk_configs")
    op.drop_table("shopify_configs")

    op.drop_index("ix_decisions_status", "decisions")
    op.drop_index("ix_decisions_user_id", "decisions")
    op.drop_table("decisions")

    op.drop_index("ix_file_uploads_user_id", "file_uploads")
    op.drop_table("file_uploads")

    op.drop_index("ix_knowledge_chunks_source_type", "knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_user_id", "knowledge_chunks")
    op.drop_table("knowledge_chunks")

    op.drop_index("ix_token_usage_created_at", "token_usage")
    op.drop_index("ix_token_usage_date", "token_usage")
    op.drop_index("ix_token_usage_user_id", "token_usage")
    op.drop_table("token_usage")

    op.drop_table("user_context")
    op.drop_table("user_settings")

    # restore the v1 user index quirk so 0001 downgrade still works cleanly
    op.drop_index("ix_users_email", "users")
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_unique_constraint("uq_users_email", "users", ["email"])
