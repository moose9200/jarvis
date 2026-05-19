"""Shared slowapi Limiter instance.

Both main.py (binds to app.state) and routers (use as decorator) must share the
same Limiter object, otherwise rate-limit exceptions won't be caught by the
registered handler.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
