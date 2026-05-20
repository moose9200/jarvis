"""SQLAlchemy ORM models.

V1 baseline (Step 0/1):
  User, OAuthToken, EmailHistory, SenderProfile, ConversationTurn, ConversationSummary

V2 additions (Step 2):
  UserSettings    — per-user AI provider, tier, BYOAK keys, response prefs
  UserContext     — RAG persona (about_me, communication_style, priorities, team)
  TokenUsage      — per-message billing/usage ledger
  KnowledgeChunk  — pgvector-backed RAG knowledge base
  FileUpload      — multimodal upload metadata (S3 key, processing status)
  Decision        — decision inbox (PRs / orders / tickets awaiting user action)
  ShopifyConfig   — per-user Shopify shop + access token
  FreshdeskConfig — per-user Freshdesk subdomain + API key

All v2 sensitive fields end in `_encrypted` and must be wrapped with
backend.crypto.{encrypt,decrypt} at write/read sites.
"""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from database import Base

# pgvector is only available on Postgres. For SQLite tests we degrade to JSON.
try:
    from pgvector.sqlalchemy import Vector

    EMBEDDING_DIM = 1536
    _EmbeddingType = Vector(EMBEDDING_DIM)
except Exception:  # pragma: no cover — sqlite test path
    _EmbeddingType = JSON


# ── V1 baseline ─────────────────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    industry = Column(String, nullable=True)  # free-text label; required at signup, drives default Intel Brief
    created_at = Column(DateTime, default=datetime.utcnow)


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    __table_args__ = (UniqueConstraint("provider", "user_id", name="uq_oauth_provider_user"),)
    id = Column(Integer, primary_key=True)
    provider = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    access_token = Column(Text)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    scope = Column(Text, nullable=True)
    extra = Column(JSON, nullable=True)


class EmailHistory(Base):
    __tablename__ = "email_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    sender = Column(String, index=True)
    subject = Column(Text)
    received_at = Column(DateTime)
    opened = Column(Integer, default=0)
    replied = Column(Integer, default=0)
    reply_latency_seconds = Column(Integer, nullable=True)
    thread_id = Column(String, nullable=True)


class SenderProfile(Base):
    __tablename__ = "sender_profiles"
    __table_args__ = (UniqueConstraint("sender", "user_id", name="uq_sender_user"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    sender = Column(String, index=True)
    relationship_weight = Column(Float, default=0.0)
    email_count = Column(Integer, default=0)
    reply_rate = Column(Float, default=0.0)
    avg_reply_latency = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    role = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    summary = Column(Text)
    up_to_turn_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── V2 additions ────────────────────────────────────────────────────────────


class UserSettings(Base):
    """Per-user AI configuration + BYOAK keys.

    `ai_provider` chooses the abstraction provider (anthropic/openai/groq/
    mistral/google). `default_model` is the tier slug (eco/intelligent/scientist)
    OR an explicit model id — the tiers module resolves it.

    All *_encrypted columns must be wrapped with crypto.{encrypt,decrypt}.
    """
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    ai_provider = Column(String, default="anthropic")
    default_model = Column(String, default="intelligent")  # eco/intelligent/scientist or model id
    response_length = Column(String, default="detailed")   # brief/detailed/deep
    personality_mode = Column(String, default="caveman")   # caveman/normal/coach/...

    daily_token_budget = Column(Integer, default=100_000)
    budget_alert_pct = Column(Integer, default=80)

    # BYOAK — encrypted at rest
    anthropic_api_key_encrypted = Column(Text, nullable=True)
    openai_api_key_encrypted = Column(Text, nullable=True)
    groq_api_key_encrypted = Column(Text, nullable=True)
    mistral_api_key_encrypted = Column(Text, nullable=True)
    google_api_key_encrypted = Column(Text, nullable=True)
    elevenlabs_api_key_encrypted = Column(Text, nullable=True)

    github_repo_url = Column(String, nullable=True)
    github_pat_encrypted = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserContext(Base):
    """User persona injected into every JARVIS prompt + RAG retrieval."""
    __tablename__ = "user_context"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    about_me = Column(Text, nullable=True)
    communication_style = Column(Text, nullable=True)
    priorities = Column(Text, nullable=True)
    team_members = Column(JSON, nullable=True)
    business_context = Column(Text, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TokenUsage(Base):
    """Per-message usage + cost ledger. Aggregated for /api/tokens/* dashboards."""
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    date = Column(String, index=True)        # "YYYY-MM-DD" for cheap daily grouping
    provider = Column(String)                # anthropic/openai/groq/...
    model = Column(String)                   # claude-sonnet-4-6, gpt-4o, ...
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cache_read_tokens = Column(Integer, default=0)
    cache_write_tokens = Column(Integer, default=0)
    thinking_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class KnowledgeChunk(Base):
    """RAG knowledge base entry — text chunk + embedding for cosine search.

    `embedding` is pgvector on Postgres, JSON fallback on SQLite (tests only).
    Indexed via ivfflat or hnsw in a later migration when row count justifies it.
    """
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    source_type = Column(String, index=True)   # email/calendar/task/shopify/upload/note
    source_id = Column(String, nullable=True)  # external id (email id, ticket id, ...)
    content = Column(Text, nullable=False)
    embedding = Column(_EmbeddingType, nullable=True)
    metadata_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class FileUpload(Base):
    """Multimodal upload — image/pdf/video/csv/text. S3 key is canonical
    location; signed URLs are minted on demand."""
    __tablename__ = "file_uploads"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    filename = Column(String)
    file_type = Column(String)   # image/pdf/video/csv/text
    s3_key = Column(String)
    size_bytes = Column(Integer)
    processed = Column(Boolean, default=False)
    extracted_text = Column(Text, nullable=True)  # PDF/CSV/transcript output
    extra = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class Decision(Base):
    """Decision inbox — items awaiting user approval/reject/snooze."""
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    source = Column(String)   # github_pr/shopify_order/freshdesk_ticket/linear_issue
    source_id = Column(String, nullable=True)
    title = Column(String)
    context_json = Column(JSON)
    status = Column(String, default="pending", index=True)
    # pending/approved/rejected/delegated/snoozed
    ai_suggestion = Column(Text, nullable=True)

    snoozed_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)


class ShopifyConfig(Base):
    """Per-user Shopify shop + permanent access token (encrypted)."""
    __tablename__ = "shopify_configs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    shop_domain = Column(String)           # mystore.myshopify.com
    access_token_encrypted = Column(Text)
    scope = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)


class FreshdeskConfig(Base):
    """Per-user Freshdesk subdomain + API key (encrypted)."""
    __tablename__ = "freshdesk_configs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    subdomain = Column(String)             # yourcompany (NOT the full domain)
    api_key_encrypted = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)


class IntelBrief(Base):
    """Periodic industry / topic monitor.

    A brief is a saved query that JARVIS can re-run on a schedule. The brief
    describes:
      - what topic to monitor (`topic`, free-form, e.g. "D2C botanicals India")
      - where to look (`sources_json` — list of Reddit subs, HN, etc.)
      - how often (`frequency_minutes` — None for manual-only)
      - any extra prompt template

    Default Intel Brief is created for every new user from their `industry`
    field. They can edit/disable/delete it.
    """
    __tablename__ = "intel_briefs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String, nullable=False)            # human-readable, e.g. "Industry chatter"
    topic = Column(String, nullable=False)           # the search subject
    prompt_template = Column(Text, nullable=True)    # optional override of the synthesis prompt
    sources_json = Column(JSON, nullable=True)       # {"reddit": ["r/Entrepreneur"], "hn": true}
    frequency_minutes = Column(Integer, nullable=True)  # None = manual; e.g. 1440 for daily
    is_active = Column(Boolean, default=True)

    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class IntelBriefRun(Base):
    """One execution of an IntelBrief. Stores the produced report so the user
    can browse history. Tied to brief_id and user_id for fast lookup."""
    __tablename__ = "intel_brief_runs"

    id = Column(Integer, primary_key=True)
    brief_id = Column(Integer, ForeignKey("intel_briefs.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    status = Column(String, default="pending")       # pending | running | done | failed
    output_text = Column(Text, nullable=True)        # the AI-synthesized briefing
    sources_summary = Column(JSON, nullable=True)    # {"reddit_items": 23, "hn_items": 7, ...}
    error = Column(Text, nullable=True)
    cost_usd = Column(Float, default=0.0)

    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
