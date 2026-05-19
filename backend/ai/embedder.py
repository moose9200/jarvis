"""Text → vector embeddings, used by the RAG knowledge base.

Strategy:
  - Primary: OpenAI's text-embedding-3-small (1536 dim, $0.02/1M).
    Triggered when the user has an OPENAI_API_KEY in UserSettings OR env.
  - Fallback: returns None. Knowledge search degrades gracefully — items
    are still stored with content but no embedding, so semantic search is
    unavailable until a key is configured.

A 1536-dim vector matches our pgvector column width (models.KnowledgeChunk).
If the user wants a different provider in the future, add a branch here.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from sqlalchemy.orm import Session

from crypto import decrypt
from models import UserSettings

logger = logging.getLogger("jarvis.embedder")

EMBEDDING_DIM = 1536
EMBEDDING_MODEL = "text-embedding-3-small"


def _openai_key(db: Session, user_id: Optional[int]) -> Optional[str]:
    """Resolve user's OpenAI key (BYOAK) or fall back to env."""
    if user_id is not None:
        s = db.query(UserSettings).filter_by(user_id=user_id).first()
        if s and s.openai_api_key_encrypted:
            try:
                k = decrypt(s.openai_api_key_encrypted)
                if k:
                    return k
            except Exception:
                logger.exception("decrypt openai key failed")
    return os.getenv("OPENAI_API_KEY", "").strip() or None


async def embed(text: str, db: Session, user_id: Optional[int]) -> Optional[list[float]]:
    """Embed a single text into a 1536-dim vector. Returns None if no key
    available — caller must handle this case gracefully."""
    text = (text or "").strip()
    if not text:
        return None
    key = _openai_key(db, user_id)
    if not key:
        return None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=key)
        resp = await client.embeddings.create(model=EMBEDDING_MODEL, input=text[:8000])
        return list(resp.data[0].embedding)
    except Exception:
        logger.exception("embedding call failed")
        return None


async def embed_batch(texts: list[str], db: Session, user_id: Optional[int]) -> list[Optional[list[float]]]:
    """Batch embedding — single round-trip up to ~2048 inputs. Falls back to
    [None]*len if no API key. Used by Celery ingest tasks for throughput."""
    cleaned = [(t or "").strip()[:8000] for t in texts]
    if not any(cleaned):
        return [None] * len(texts)
    key = _openai_key(db, user_id)
    if not key:
        return [None] * len(texts)
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=key)
        resp = await client.embeddings.create(model=EMBEDDING_MODEL, input=cleaned)
        return [list(d.embedding) for d in resp.data]
    except Exception:
        logger.exception("batch embedding call failed")
        return [None] * len(texts)
