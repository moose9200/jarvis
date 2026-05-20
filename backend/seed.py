"""Seed script — populate the dev DB with realistic test data.

Run: docker compose exec backend python seed.py
     OR make seed

Creates:
  - 3 test users (founder@test.com / pro@test.com / free@test.com — pw: test1234)
  - UserContext for the founder user
  - UserSettings with caveman personality, intelligent tier
  - A handful of knowledge chunks for RAG testing
  - 30 days of fake TokenUsage rows to populate the dashboard

Safe to run multiple times — idempotent (lookups by email + delete-then-insert
for collections).
"""
from __future__ import annotations

import os
import random
import sys
from datetime import date, datetime, timedelta

# Ensure backend/ is the cwd so imports resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bcrypt  # noqa: E402

from database import SessionLocal  # noqa: E402
from models import (  # noqa: E402
    KnowledgeChunk,
    TokenUsage,
    User,
    UserContext,
    UserSettings,
)

SEED_USERS = [
    {"email": "founder@test.com", "name": "Founder", "plan": "founder", "industry": "D2C botanicals India"},
    {"email": "pro@test.com",     "name": "Pro",     "plan": "pro",     "industry": "SaaS startup"},
    {"email": "free@test.com",    "name": "Free",    "plan": "free",    "industry": "ecommerce"},
]
DEFAULT_PASSWORD = "test1234"


def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def ensure_user(db, email: str, industry: str | None = None) -> User:
    u = db.query(User).filter_by(email=email).first()
    if u:
        if industry and not u.industry:
            u.industry = industry
            db.commit()
        return u
    u = User(email=email, password_hash=hash_pw(DEFAULT_PASSWORD), industry=industry)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def seed_founder_persona(db, user: User) -> None:
    ctx = db.query(UserContext).filter_by(user_id=user.id).first()
    if not ctx:
        ctx = UserContext(user_id=user.id)
        db.add(ctx)
    ctx.about_me = "Hemant — founder of Braivex, a D2C botanicals brand based in India."
    ctx.communication_style = "Direct. No fluff. Bullet points OK. Indian English."
    ctx.priorities = "Customer retention, shipping defect rate, founding-team hiring."
    ctx.team_members = [
        {"name": "Anya",  "role": "Ops lead",       "relationship": "trusted, autonomous"},
        {"name": "Rohan", "role": "Lead developer", "relationship": "junior, needs guidance"},
    ]
    ctx.business_context = "B2C botanicals (skincare + wellness). Shopify storefront, Freshdesk for support."

    settings = db.query(UserSettings).filter_by(user_id=user.id).first()
    if not settings:
        settings = UserSettings(user_id=user.id)
        db.add(settings)
    settings.ai_provider = "anthropic"
    settings.default_model = "intelligent"
    settings.personality_mode = "coder"
    settings.response_length = "detailed"
    settings.daily_token_budget = 200_000

    db.commit()


def seed_knowledge(db, user: User) -> None:
    # Wipe existing seeded chunks for this user
    db.query(KnowledgeChunk).filter(
        KnowledgeChunk.user_id == user.id,
        KnowledgeChunk.source_type == "seed",
    ).delete()

    snippets = [
        "Top-selling SKU: Lavender Body Oil 200ml — 23% of revenue last month.",
        "Shipping defect rate dropped from 4.1% to 2.6% after switching couriers in April.",
        "Anya runs ops day-to-day. Trusted; only escalate refunds above ₹5000.",
        "We refuse paid ads on Instagram. Growth comes from referrals + content.",
        "Our packaging supplier is Vrindavan Glass — single source. Risk: backup needed.",
    ]
    for s in snippets:
        db.add(
            KnowledgeChunk(
                user_id=user.id,
                source_type="seed",
                content=s,
                created_at=datetime.utcnow(),
            )
        )
    db.commit()


def seed_token_history(db, user: User) -> None:
    db.query(TokenUsage).filter(TokenUsage.user_id == user.id).delete()
    today = date.today()
    for i in range(30):
        day = today - timedelta(days=i)
        n_calls = random.randint(3, 25)
        for _ in range(n_calls):
            inp = random.randint(200, 4000)
            out = random.randint(50, 1500)
            db.add(
                TokenUsage(
                    user_id=user.id,
                    date=day.isoformat(),
                    provider="anthropic",
                    model="claude-sonnet-4-5",
                    input_tokens=inp,
                    output_tokens=out,
                    cache_read_tokens=random.randint(0, inp),
                    cost_usd=round((inp * 3 + out * 15) / 1_000_000, 6),
                    created_at=datetime.combine(day, datetime.min.time()),
                )
            )
    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        users = [ensure_user(db, u["email"], u.get("industry")) for u in SEED_USERS]
        founder = users[0]
        seed_founder_persona(db, founder)
        seed_knowledge(db, founder)
        seed_token_history(db, founder)
        print(f"✓ Seeded {len(users)} users (password: {DEFAULT_PASSWORD!r})")
        print(f"  founder@test.com → persona + 5 RAG chunks + 30 days of usage")
        print(f"  pro@test.com / free@test.com → empty (test plan gates against them)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
