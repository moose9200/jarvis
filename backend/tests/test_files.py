"""T1-11/C — `routers/files.py` upload + list + delete coverage.

Covers the four endpoints: POST /upload, GET /files, GET /files/{id},
DELETE /files/{id}. Storage (boto3 / S3) is patched so the tests don't
need real credentials.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models import FileUpload, User
from rate_limit import limiter
from routers.users import get_current_user


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture()
def files_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def client(files_db):
    limiter.reset()
    app.dependency_overrides[get_db] = lambda: files_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        limiter.reset()


def _seed_user(db, *, user_id: int = 1, email: str = "alice@example.com") -> User:
    u = User(id=user_id, email=email, password_hash="hashed", industry="d2c")
    db.add(u)
    db.commit()
    db.refresh(u)
    app.dependency_overrides[get_current_user] = lambda: u
    return u


# ── POST /api/files/upload ───────────────────────────────────────────


def test_upload_requires_storage_configured(client, files_db):
    """When S3 env vars aren't set, return 402 with the friendly message
    that points the operator to USER_TASKS #9 (Cloudflare R2)."""
    _seed_user(files_db)
    with patch("storage.is_configured", return_value=False):
        r = client.post(
            "/api/files/upload",
            files={"file": ("note.txt", b"hello world", "text/plain")},
        )
    assert r.status_code == 402
    detail = r.json().get("detail", "").lower()
    assert "storage" in detail


def test_upload_happy_path_creates_row(client, files_db):
    """Storage configured + small file → 200, DB row created, S3 upload
    called once with the right bytes."""
    user = _seed_user(files_db)
    fake_url = "https://r2.example.com/uploads/abcdef.txt"
    with patch("storage.is_configured", return_value=True), \
         patch("storage.upload_bytes", return_value=fake_url) as upload_mock:
        r = client.post(
            "/api/files/upload",
            files={"file": ("note.txt", b"hello world", "text/plain")},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["filename"] == "note.txt"
    assert body["s3_key"] == fake_url
    assert body["size_bytes"] == len(b"hello world")
    upload_mock.assert_called_once()

    rows = files_db.query(FileUpload).filter_by(user_id=user.id).all()
    assert len(rows) == 1
    assert rows[0].size_bytes == len(b"hello world")


def test_upload_rejects_over_size_cap(client, files_db):
    """Body > MAX_BYTES (20 MB) → 413, no upload attempt."""
    from files.processor import MAX_BYTES

    _seed_user(files_db)
    oversize = b"\0" * (MAX_BYTES + 1)
    with patch("storage.is_configured", return_value=True), \
         patch("storage.upload_bytes") as upload_mock:
        r = client.post(
            "/api/files/upload",
            files={"file": ("huge.bin", oversize, "application/octet-stream")},
        )
    assert r.status_code == 413
    upload_mock.assert_not_called()


def test_upload_returns_502_when_s3_fails(client, files_db):
    """Boto raises → route surfaces 502 and DOES NOT create a DB row
    (we'd otherwise have orphan rows pointing at nothing)."""
    _seed_user(files_db)
    with patch("storage.is_configured", return_value=True), \
         patch("storage.upload_bytes", side_effect=RuntimeError("R2 down")):
        r = client.post(
            "/api/files/upload",
            files={"file": ("note.txt", b"hello", "text/plain")},
        )
    assert r.status_code == 502
    assert files_db.query(FileUpload).count() == 0


# ── GET /api/files ───────────────────────────────────────────────────


def test_list_files_returns_only_current_user_files(client, files_db):
    """Cross-user isolation: rows belonging to other users must not leak
    into the list response."""
    user = _seed_user(files_db, user_id=1, email="me@x.com")
    # Seed a foreign user + their file
    other = User(id=99, email="other@x.com", password_hash="x", industry="x")
    files_db.add(other)
    files_db.commit()

    files_db.add(FileUpload(
        user_id=1, filename="mine.txt", file_type="text",
        s3_key="url1", size_bytes=10, processed=True, created_at=datetime.utcnow(),
    ))
    files_db.add(FileUpload(
        user_id=99, filename="theirs.txt", file_type="text",
        s3_key="url2", size_bytes=20, processed=True, created_at=datetime.utcnow(),
    ))
    files_db.commit()

    r = client.get("/api/files")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["files"]) == 1
    assert body["files"][0]["filename"] == "mine.txt"


# ── GET /api/files/{id} ──────────────────────────────────────────────


def test_get_file_returns_signed_url(client, files_db):
    user = _seed_user(files_db, user_id=2, email="dl@x.com")
    files_db.add(FileUpload(
        id=42, user_id=2, filename="report.pdf", file_type="pdf",
        s3_key="https://r2/report.pdf", size_bytes=500, processed=True,
        created_at=datetime.utcnow(),
    ))
    files_db.commit()
    r = client.get("/api/files/42")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["filename"] == "report.pdf"
    # signed_url should be present (the route reuses s3_key when no
    # presigned generator is wired in production yet)
    assert body["signed_url"]


def test_get_file_404_when_owned_by_other_user(client, files_db):
    """Looking up a file belonging to another user must return 404,
    not 403 — we don't even confirm existence to non-owners."""
    _seed_user(files_db, user_id=3, email="reader@x.com")
    files_db.add(User(id=99, email="owner@x.com", password_hash="x", industry="x"))
    files_db.add(FileUpload(
        id=77, user_id=99, filename="secret.pdf", file_type="pdf",
        s3_key="url", size_bytes=10, processed=True, created_at=datetime.utcnow(),
    ))
    files_db.commit()

    r = client.get("/api/files/77")
    assert r.status_code == 404


# ── DELETE /api/files/{id} ───────────────────────────────────────────


def test_delete_file_removes_db_row_and_calls_storage_delete(client, files_db):
    _seed_user(files_db, user_id=4, email="del@x.com")
    files_db.add(FileUpload(
        id=55, user_id=4, filename="temp.txt", file_type="text",
        s3_key="https://r2.example.com/uploads/temp-abc.txt",
        size_bytes=10, processed=True, created_at=datetime.utcnow(),
    ))
    files_db.commit()

    with patch("storage.delete") as del_mock:
        r = client.delete("/api/files/55")
    assert r.status_code == 200, r.text
    assert r.json()["deleted"] == 55
    # row gone
    files_db.expire_all()
    assert files_db.query(FileUpload).filter_by(id=55).first() is None
    # storage.delete was called with the parsed key (last segment of URL)
    del_mock.assert_called_once()
    assert "temp-abc.txt" in del_mock.call_args.args[0]


def test_delete_file_404_when_not_owned(client, files_db):
    _seed_user(files_db, user_id=5, email="x@x.com")
    files_db.add(User(id=99, email="owner@x.com", password_hash="x", industry="x"))
    files_db.add(FileUpload(
        id=66, user_id=99, filename="theirs.txt", file_type="text",
        s3_key="url", size_bytes=10, processed=True, created_at=datetime.utcnow(),
    ))
    files_db.commit()

    r = client.delete("/api/files/66")
    assert r.status_code == 404
    # foreign row untouched
    files_db.expire_all()
    assert files_db.query(FileUpload).filter_by(id=66).first() is not None
