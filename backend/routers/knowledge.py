"""Knowledge base endpoints.

  GET  /api/knowledge/status   — counts by source, last_updated, embedded vs total
  POST /api/knowledge/note     — quick "save this thought" (manual chunk add)
  GET  /api/knowledge/search   — debug endpoint: ?q=foo&limit=5

Celery-driven ingest (emails, tasks, shopify, files) lives in tasks/ — added in
follow-up commits. The search/inject flow in JarvisAI already works against any
chunks present in the DB.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ai import knowledge as kb
from database import get_db
from models import User
from routers.users import get_current_user

router = APIRouter()


class NoteIn(BaseModel):
    content: str = Field(..., min_length=4, max_length=10_000)
    source_type: str = Field("note", max_length=40)
    metadata: dict | None = None


@router.get("/knowledge/status")
def status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return kb.status(db, current_user.id)


@router.post("/knowledge/note")
async def note(
    payload: NoteIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chunk_id = await kb.add_chunk(
        db=db,
        user_id=current_user.id,
        content=payload.content,
        source_type=payload.source_type,
        source_id=None,
        metadata=payload.metadata,
    )
    return {"id": chunk_id}


@router.get("/knowledge/search")
async def search(
    q: str = Query(..., min_length=2, max_length=500),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chunks = await kb.search(db, current_user.id, q, limit=limit)
    return {
        "query": q,
        "results": [
            {
                "id": c.id,
                "content": c.content,
                "source_type": c.source_type,
                "source_id": c.source_id,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in chunks
        ],
    }
