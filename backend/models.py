from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Boolean, UniqueConstraint, ForeignKey
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
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
