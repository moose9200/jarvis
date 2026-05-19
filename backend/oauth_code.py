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
on first use and expires automatically.

NOTE: in-memory storage works for single-worker deployments only. Step 1 of the
build plan migrates this to Redis so it survives across workers + restarts.
"""
from __future__ import annotations

import secrets
import time
from threading import Lock
from typing import Dict, Optional, Tuple

_TTL_SECONDS = 60
_codes: Dict[str, Tuple[int, float]] = {}  # code -> (user_id, expires_at_epoch)
_lock = Lock()


def _gc_locked() -> None:
    now = time.time()
    expired = [c for c, (_, exp) in _codes.items() if exp < now]
    for c in expired:
        _codes.pop(c, None)


def issue(user_id: int) -> str:
    """Mint a fresh one-time code for the given user. Returns the code string."""
    with _lock:
        _gc_locked()
        code = secrets.token_urlsafe(24)
        _codes[code] = (user_id, time.time() + _TTL_SECONDS)
        return code


def consume(code: str) -> Optional[int]:
    """Single-use redemption. Returns the user_id if the code is valid and
    unexpired, else None. The code is always removed from the store after this
    call (even if expired) so it cannot be replayed."""
    with _lock:
        _gc_locked()
        entry = _codes.pop(code, None)
        if entry is None:
            return None
        user_id, exp = entry
        if exp < time.time():
            return None
        return user_id
