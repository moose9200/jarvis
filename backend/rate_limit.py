"""Shared slowapi Limiter instance.

Both main.py (binds to app.state) and routers (use as decorator) must share the
same Limiter object, otherwise rate-limit exceptions won't be caught by the
registered handler.

Storage:
  - If REDIS_URL is set: Redis-backed (survives across workers, restarts).
  - Else: in-memory (single-process only; OK for tests and local dev).
"""
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

_redis_url = os.getenv("REDIS_URL")

if _redis_url:
    limiter = Limiter(key_func=get_remote_address, storage_uri=_redis_url)
else:
    limiter = Limiter(key_func=get_remote_address)
