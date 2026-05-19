"""RAG knowledge base — cosine similarity search over per-user chunks.

Wraps the KnowledgeChunk pgvector column. Cosine distance uses the `<=>`
operator from pgvector. Lower distance = more similar.

Public API
----------
    add_chunk(db, user_id, content, source_type, source_id, metadata) -> chunk_id
    search(db, user_id, query, limit=5) -> list[KnowledgeChunk]
    status(db, user_id) -> {total, by_source, last_updated}
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from models import KnowledgeChunk

from .embedder import embed

logger = logging.getLogger("jarvis.knowledge")


async def add_chunk(
    db: Session,
    user_id: int,
    content: str,
    source_type: str,
    source_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> int:
    """Embed + insert a new chunk. Returns the new row id.

    If embedding fails (no API key), the chunk is still stored with NULL
    embedding — listable but not searchable."""
    vec = await embed(content, db, user_id)
    chunk = KnowledgeChunk(
        user_id=user_id,
        source_type=source_type,
        source_id=source_id,
        content=content,
        embedding=vec,
        metadata_json=metadata or None,
        created_at=datetime.utcnow(),
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk.id


async def search(
    db: Session,
    user_id: int,
    query: str,
    limit: int = 5,
) -> list[KnowledgeChunk]:
    """Cosine-similarity search for chunks relevant to `query`. Returns up to
    `limit` chunks ordered by ascending distance (most relevant first).

    Returns [] if no embedding can be generated for the query."""
    vec = await embed(query, db, user_id)
    if vec is None:
        return []

    try:
        # pgvector cosine distance: <=> operator. Returns ordered ascending.
        sql = text(
            """
            SELECT id, content, source_type, source_id, metadata_json, created_at,
                   embedding <=> CAST(:vec AS vector) AS distance
            FROM knowledge_chunks
            WHERE user_id = :uid AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :n
            """
        )
        rows = db.execute(sql, {"uid": user_id, "vec": str(vec), "n": limit}).fetchall()
        chunks: list[KnowledgeChunk] = []
        for r in rows:
            # Reconstruct lightweight chunk objects with the rendered fields.
            chunk = KnowledgeChunk(
                id=r.id,
                user_id=user_id,
                content=r.content,
                source_type=r.source_type,
                source_id=r.source_id,
                metadata_json=r.metadata_json,
                created_at=r.created_at,
            )
            chunks.append(chunk)
        return chunks
    except Exception:
        logger.exception("knowledge search failed")
        return []


def status(db: Session, user_id: int) -> dict:
    """Aggregate stats for /api/knowledge/status."""
    total = (
        db.query(func.count(KnowledgeChunk.id))
        .filter(KnowledgeChunk.user_id == user_id)
        .scalar()
        or 0
    )
    by_source_rows = (
        db.query(KnowledgeChunk.source_type, func.count(KnowledgeChunk.id))
        .filter(KnowledgeChunk.user_id == user_id)
        .group_by(KnowledgeChunk.source_type)
        .all()
    )
    last = (
        db.query(func.max(KnowledgeChunk.created_at))
        .filter(KnowledgeChunk.user_id == user_id)
        .scalar()
    )
    embedded = (
        db.query(func.count(KnowledgeChunk.id))
        .filter(KnowledgeChunk.user_id == user_id, KnowledgeChunk.embedding.isnot(None))
        .scalar()
        or 0
    )
    return {
        "total": total,
        "embedded": embedded,
        "by_source": {row[0] or "unknown": row[1] for row in by_source_rows},
        "last_updated": last.isoformat() if last else None,
    }
