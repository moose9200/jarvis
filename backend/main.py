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

from database import Base, engine
from rate_limit import limiter
import models  # noqa
import migrations
from routers import auth, feed, email_intelligence, chat, users

migrations.run(engine)
Base.metadata.create_all(bind=engine)

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


@app.get("/api/health")
def health():
    anthropic_key_set = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
    elevenlabs_key_set = bool(os.getenv("ELEVENLABS_API_KEY", "").strip())
    return {
        "status": "ok",
        "version": "0.1.0",
        "api_keys": {
            "anthropic": anthropic_key_set,
            "elevenlabs": elevenlabs_key_set,
        },
    }
