import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import Base, engine
import models  # noqa
from routers import auth, feed, email_intelligence, chat

Base.metadata.create_all(bind=engine)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="JARVIS Backend", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-secret"),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
