"""Short-lived one-time codes for OAuth-redirect authentication.

Browsers can't send `Authorization: Bearer` headers when navigating to an OAuth
provider's authorize URL — the redirect is a top-level navigation, not an
XHR. Previously we worked around this by appending `?token=<JWT>` to the
URL, but that leaks the JWT into:
  - server access logs
  - the OAuth provider's referrer header
  - browser history

This module mints opaque, short-lived (60s), single-use codes that map to a
user_id. The frontend exchanges its JWT for a code via an authenticated POST,
then uses the code in the URL for the redirect. The code is consumed (deleted)
on first use and expires automatically via Redis TTL.

Storage backend:
  - If REDIS_URL is set: Redis with native TTL — survives across workers and
    process restarts. This is the production path (Step 1.3+).
  - Else: in-memory dict — single-worker fallback for tests and offline dev.
"""
from __future__ import annotations

import os
import secrets
import time
from functools import lru_cache
from threading import Lock
from typing import Dict, Optional, Tuple

_TTL_SECONDS = 60
_KEY_PREFIX = "jarvis:oauth_code:"

# ── In-memory fallback (only used if REDIS_URL is unset) ────────────────────
_mem: Dict[str, Tuple[int, float]] = {}
_mem_lock = Lock()


def _mem_gc_locked() -> None:
    now = time.time()
    for c in [c for c, (_, exp) in _mem.items() if exp < now]:
        _mem.pop(c, None)


# ── Redis client (lazy, cached) ─────────────────────────────────────────────
@lru_cache(maxsize=1)
def _redis():
    url = os.getenv("REDIS_URL")
    if not url:
        return None
    try:
        import redis  # local import keeps module importable without redis lib
        return redis.Redis.from_url(url, decode_responses=True)
    except Exception:
        return None


def issue(user_id: int) -> str:
    """Mint a fresh one-time code for the given user. Returns the code string."""
    code = secrets.token_urlsafe(24)
    r = _redis()
    if r is not None:
        r.setex(_KEY_PREFIX + code, _TTL_SECONDS, str(user_id))
        return code
    # in-memory fallback
    with _mem_lock:
        _mem_gc_locked()
        _mem[code] = (user_id, time.time() + _TTL_SECONDS)
    return code


def consume(code: str) -> Optional[int]:
    """Single-use redemption. Returns user_id if valid and unexpired, else None.
    The code is always removed after this call (atomically when using Redis)."""
    if not code:
        return None
    r = _redis()
    if r is not None:
        # GETDEL is atomic — read + delete in one round-trip. Available in Redis 6.2+.
        try:
            value = r.getdel(_KEY_PREFIX + code)
        except AttributeError:
            # Older redis-py without getdel — emulate.
            pipe = r.pipeline()
            pipe.get(_KEY_PREFIX + code)
            pipe.delete(_KEY_PREFIX + code)
            value, _ = pipe.execute()
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    # in-memory fallback
    with _mem_lock:
        _mem_gc_locked()
        entry = _mem.pop(code, None)
        if entry is None:
            return None
        user_id, exp = entry
        if exp < time.time():
            return None
        return user_id
