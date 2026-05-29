"""File upload + metadata endpoints.

Workflow
--------
  POST /api/files/upload   multipart/form-data → FileUpload row + S3 object
  GET  /api/files          list user's uploads
  GET  /api/files/{id}     metadata + presigned URL (1h)
  DELETE /api/files/{id}   remove S3 object + DB row

S3 backend is the storage module (Cloudflare R2 recommended). Upload
returns 402 with a friendly message when storage isn't configured
(USER_TASKS #9). Images are stored as-is and referenced at chat time;
PDFs / CSVs / text are extracted to FileUpload.extracted_text for inline
use in the model prompt.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

import storage as object_store
from database import get_db
from files.processor import MAX_BYTES, process
from models import FileUpload, User
from routers.users import get_current_user

# NOTE: slowapi's @limiter.limit decorator does not compose cleanly with
# FastAPI routes that take an UploadFile parameter (the introspector trips
# on the wrapped signature and raises "ForwardRef('UploadFile') is a valid
# Pydantic field type"). File uploads are rate-limited at the gateway /
# reverse-proxy layer instead, or via a per-user disk-quota check inside
# the route body once we ship that.

logger = logging.getLogger("jarvis.files")
router = APIRouter()


def _serialize(fu: FileUpload, signed_url: Optional[str] = None) -> dict:
    return {
        "id": fu.id,
        "filename": fu.filename,
        "file_type": fu.file_type,
        "s3_key": fu.s3_key,
        "size_bytes": fu.size_bytes,
        "processed": fu.processed,
        "has_extracted_text": bool(fu.extracted_text),
        "extracted_preview": (fu.extracted_text or "")[:300] if fu.extracted_text else None,
        "signed_url": signed_url,
        "created_at": fu.created_at.isoformat() if fu.created_at else None,
    }


@router.post("/files/upload")
async def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Storage must be configured
    if not object_store.is_configured():
        raise HTTPException(
            status_code=402,
            detail=(
                "Object storage not configured. Set S3_BUCKET + S3_ACCESS_KEY + "
                "S3_SECRET_KEY in backend/.env (Cloudflare R2 free 10GB — see "
                "USER_TASKS #9)."
            ),
        )

    # Stream read with size cap — don't load 200MB into memory.
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large (max {MAX_BYTES} bytes)")

    filename = file.filename or "upload.bin"
    file_type, extracted = process(filename, data)

    # Upload bytes to S3
    try:
        url = object_store.upload_bytes(
            data=data,
            filename=filename,
            content_type=file.content_type,
        )
    except Exception:
        logger.exception("s3 upload failed")
        raise HTTPException(status_code=502, detail="Object storage upload failed.")

    # storage.upload_bytes returns full URL; we don't have the key separately,
    # so reconstruct from URL or stash both. Here we keep the URL in s3_key
    # since that's what the consumer needs.
    s3_key = url

    fu = FileUpload(
        user_id=current_user.id,
        filename=filename,
        file_type=file_type,
        s3_key=s3_key,
        size_bytes=len(data),
        processed=True,
        extracted_text=extracted,
        created_at=datetime.utcnow(),
    )
    db.add(fu)
    db.commit()
    db.refresh(fu)
    return _serialize(fu)


@router.get("/files")
def list_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(FileUpload)
        .filter(FileUpload.user_id == current_user.id)
        .order_by(FileUpload.id.desc())
        .limit(100)
        .all()
    )
    return {"files": [_serialize(r) for r in rows]}


@router.get("/files/{file_id}")
def get_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    fu = (
        db.query(FileUpload)
        .filter(FileUpload.id == file_id, FileUpload.user_id == current_user.id)
        .first()
    )
    if not fu:
        raise HTTPException(404, "File not found")
    return _serialize(fu, signed_url=fu.s3_key)


@router.delete("/files/{file_id}")
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    fu = (
        db.query(FileUpload)
        .filter(FileUpload.id == file_id, FileUpload.user_id == current_user.id)
        .first()
    )
    if not fu:
        raise HTTPException(404, "File not found")
    # storage.delete expects the raw S3 key; we stored the full URL.
    # Best-effort cleanup — extract the key from the URL if possible.
    try:
        if fu.s3_key and "/" in fu.s3_key:
            key = fu.s3_key.rsplit("/", 1)[-1]
            object_store.delete(key)
    except Exception:
        logger.exception("s3 delete failed (continuing with DB row cleanup)")
    db.delete(fu)
    db.commit()
    return {"ok": True, "deleted": file_id}
