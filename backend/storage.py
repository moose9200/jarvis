"""Object storage abstraction.

Backed by S3 or any S3-compatible service (Cloudflare R2 recommended for
free 10GB tier — see Desktop/JARVIS_USER_TASKS.txt task #9).

Public API:
    upload_bytes(data: bytes, key: str, content_type: str) -> str
    upload_file(path: str, key: str | None = None) -> str
    presigned_url(key: str, expires_in: int = 3600) -> str
    delete(key: str) -> None
    is_configured() -> bool

If S3_* env vars are not set, the module is in "disabled" mode and any upload
attempt raises StorageUnconfiguredError. The rest of the app can call
is_configured() to gate UI affordances.
"""
from __future__ import annotations

import mimetypes
import os
import uuid
from functools import lru_cache
from typing import Optional

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


class StorageUnconfiguredError(RuntimeError):
    """Raised when S3 credentials are not set and an operation requires them."""


def is_configured() -> bool:
    return bool(
        os.getenv("S3_BUCKET")
        and os.getenv("S3_ACCESS_KEY")
        and os.getenv("S3_SECRET_KEY")
    )


@lru_cache(maxsize=1)
def _client():
    if not is_configured():
        raise StorageUnconfiguredError(
            "S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY must be set"
        )
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL") or None,
        aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
        region_name=os.getenv("S3_REGION", "auto"),
        config=Config(signature_version="s3v4"),
    )


def _bucket() -> str:
    return os.environ["S3_BUCKET"]


def _public_url(key: str) -> str:
    """Build a URL for the stored object.

    Cloudflare R2: typically `https://<bucket>.<account-id>.r2.cloudflarestorage.com/<key>`
                   or a custom domain like `https://assets.yourdomain.com/<key>`.
    AWS S3:        `https://<bucket>.s3.<region>.amazonaws.com/<key>`.

    We prefer the explicit S3_PUBLIC_URL env if set (custom domain or CDN),
    otherwise derive from endpoint + bucket.
    """
    base = os.getenv("S3_PUBLIC_URL")
    if base:
        return f"{base.rstrip('/')}/{key}"
    endpoint = os.getenv("S3_ENDPOINT_URL", "").rstrip("/")
    if endpoint:
        return f"{endpoint}/{_bucket()}/{key}"
    region = os.getenv("S3_REGION", "us-east-1")
    return f"https://{_bucket()}.s3.{region}.amazonaws.com/{key}"


def _make_key(filename: str, prefix: str = "uploads") -> str:
    ext = os.path.splitext(filename)[1].lower()
    return f"{prefix}/{uuid.uuid4().hex}{ext}"


def upload_bytes(
    data: bytes,
    key: Optional[str] = None,
    content_type: Optional[str] = None,
    filename: Optional[str] = None,
) -> str:
    """Upload bytes. Returns the public URL.

    Caller supplies either `key` (full object key) or `filename` (we generate
    a UUID-based key under `uploads/`).
    """
    if not key:
        key = _make_key(filename or "file.bin")
    if not content_type and filename:
        content_type = mimetypes.guess_type(filename)[0]
    extra = {"ContentType": content_type} if content_type else {}
    _client().put_object(Bucket=_bucket(), Key=key, Body=data, **extra)
    return _public_url(key)


def upload_file(path: str, key: Optional[str] = None) -> str:
    """Upload a local file. Returns the public URL."""
    if not key:
        key = _make_key(os.path.basename(path))
    content_type, _ = mimetypes.guess_type(path)
    extra = {"ContentType": content_type} if content_type else {}
    _client().upload_file(path, _bucket(), key, ExtraArgs=extra or None)
    return _public_url(key)


def presigned_url(key: str, expires_in: int = 3600) -> str:
    """Signed GET URL for a private object. Default 1-hour expiry."""
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": _bucket(), "Key": key},
        ExpiresIn=expires_in,
    )


def delete(key: str) -> None:
    try:
        _client().delete_object(Bucket=_bucket(), Key=key)
    except ClientError:
        # idempotent — missing key is fine
        pass
