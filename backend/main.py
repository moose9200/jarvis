import os
import sys
from dotenv import load_dotenv
load_dotenv()

# ── FATAL: refuse to start if required secrets are missing ──────────────────
for _required in ("JWT_SECRET", "SESSION_SECRET", "TOKEN_ENCRYPTION_KEY"):
    if not os.getenv(_required):
        print(f"FATAL: {_required} env var not set", file=sys.stderr)
        sys.exit(1)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from database import Base, engine  # noqa: F401 — Base re-exported for legacy callers
from rate_limit import limiter
import models  # noqa
from routers import auth, chat, context, email_intelligence, feed, files, knowledge, settings as settings_router, tokens, users

# Schema is owned by Alembic. Migrations run via `alembic upgrade head` from
# the Dockerfile CMD (see backend/Dockerfile) — never auto-create here.

app = FastAPI(title="JARVIS Backend", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET"),
)

_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(feed.router, prefix="/api", tags=["feed"])
app.include_router(email_intelligence.router, prefix="/api", tags=["email"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(tokens.router, prefix="/api", tags=["tokens"])
app.include_router(settings_router.router, prefix="/api", tags=["settings"])
app.include_router(context.router, prefix="/api", tags=["context"])
app.include_router(knowledge.router, prefix="/api", tags=["knowledge"])
app.include_router(files.router, prefix="/api", tags=["files"])


@app.get("/api/health")
def health():
    """Liveness + dependency check. Returns 200 even if optional deps fail,
    with a `status` field per dependency for monitoring."""
    from sqlalchemy import text

    # Database
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass

    # Redis
    redis_ok = False
    if os.getenv("REDIS_URL"):
        try:
            import redis
            r = redis.Redis.from_url(os.environ["REDIS_URL"], socket_timeout=2)
            redis_ok = bool(r.ping())
        except Exception:
            pass

    # Storage
    try:
        from storage import is_configured as _storage_ok
        storage_ok = _storage_ok()
    except Exception:
        storage_ok = False

    return {
        "status": "ok",
        "version": "0.2.0",
        "api_keys": {
            "anthropic": bool(os.getenv("ANTHROPIC_API_KEY", "").strip()),
            "elevenlabs": bool(os.getenv("ELEVENLABS_API_KEY", "").strip()),
        },
        "deps": {
            "database": db_ok,
            "redis": redis_ok,
            "storage": storage_ok,
        },
    }
