"""Shared slowapi Limiter instance.

Both main.py (binds to app.state) and routers (use as decorator) must share the
same Limiter object, otherwise rate-limit exceptions won't be caught by the
registered handler.

Keying:
  - Authenticated requests key on `user:<id>` so users behind a shared NAT
    don't share a bucket. `get_current_user` stashes the User on
    `request.state.user` before returning, which is what _user_or_ip_key
    reads.
  - Anonymous routes (login/register/oauth start) fall back to
    `ip:<addr>` so we still throttle credential stuffing.

Storage:
  - If REDIS_URL is set: Redis-backed (survives across workers, restarts).
  - Else: in-memory (single-process only; OK for tests and local dev).
"""
import os

from slowapi import Limiter
from slowapi.util import get_remote_address


def _user_or_ip_key(request) -> str:
    """Per-user keying for auth'd routes, IP fallback otherwise.

    The auth dependency (`routers.users.get_current_user`) stashes the
    `User` on `request.state.user` when a valid JWT is presented. For
    anonymous routes we fall back to IP so we still throttle
    credential-stuffing attempts on /login + /register.
    """
    user = getattr(request.state, "user", None)
    if user is not None and getattr(user, "id", None) is not None:
        return f"user:{user.id}"
    return f"ip:{get_remote_address(request)}"


_redis_url = os.getenv("REDIS_URL")

if _redis_url:
    limiter = Limiter(key_func=_user_or_ip_key, storage_uri=_redis_url)
else:
    limiter = Limiter(key_func=_user_or_ip_key)
