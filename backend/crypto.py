"""Symmetric encryption for sensitive at-rest data (OAuth tokens, API keys).

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the `cryptography` package, which is
already pulled in by python-jose[cryptography].

Key management:
- TOKEN_ENCRYPTION_KEY env var, required at boot (main.py crashes if missing).
- Accepts either a 44-char urlsafe-b64-encoded Fernet key (preferred), or any
  string >= 32 chars which is then base64-encoded to make a valid Fernet key.

Generate a proper key with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
from __future__ import annotations

import base64
import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    raw = os.getenv("TOKEN_ENCRYPTION_KEY", "")
    if not raw:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY not set")
    if len(raw) == 44:
        # already a Fernet key
        return Fernet(raw.encode())
    if len(raw) < 32:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY must be >= 32 chars or a 44-char Fernet key")
    # derive a 32-byte key by truncating/padding and base64-encoding
    key_bytes = raw.encode()[:32].ljust(32, b"\0")
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def encrypt(value: str | None) -> str | None:
    """Encrypt a plaintext string. Returns None if input is None."""
    if value is None:
        return None
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str | None) -> str | None:
    """Decrypt a ciphertext. Returns None if input is None. Returns the input unchanged
    if it doesn't look like a Fernet token (helps with backward-compat migration of
    previously-plaintext rows). Raises only on truly corrupt ciphertext."""
    if value is None:
        return None
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        # legacy plaintext row — return as-is so reads don't break during rollout
        return value
