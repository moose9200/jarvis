"""Mock OAuth server for offline development + E2E tests.

Stands in for Google / Microsoft / Slack / GitHub / Shopify OAuth flows so
you can wire and test the connect-disconnect-fetch loop without setting up
real provider apps.

Endpoints:
  GET  /auth                   — fake authorize page (auto-redirects with code)
  POST /token                  — exchanges code for fake access_token
  GET  /api/<provider>/<path>  — minimal fake data so connectors don't 404

How to use:
  1. docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile mock up
  2. Override provider env vars in your .env.dev:
        GOOGLE_CLIENT_ID=mock-google
        GOOGLE_CLIENT_SECRET=mock-secret
        ANTHROPIC_API_KEY=...  (real — for chat synthesis only)
     And in backend/routers/auth.py, the real OAuth URLs would have to
     point at this server. NOT YET WIRED — that's a follow-up commit.

  3. Or just hit endpoints directly with curl to populate test data.

The server is intentionally permissive: every authorize request returns
the same `mock_code_xxx`, every token exchange returns the same access
token, every API request returns a small canned payload.
"""
from __future__ import annotations

import secrets
import time
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

app = FastAPI(title="mock-oauth", version="0.1.0")

# In-memory: code → {user_id, provider, expires_at, used}
_codes: dict[str, dict[str, Any]] = {}
_TOKEN = "mock_access_token_abcdefghijklmnopqrstuvwxyz123456"
_REFRESH = "mock_refresh_token_zzz"


# ── Authorize ──────────────────────────────────────────────────────────────


@app.get("/auth")
def fake_authorize(
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    state: str = Query(""),
    scope: str = Query(""),
    response_type: str = Query("code"),
):
    """Stand-in for /authorize on Google/Microsoft/Slack/etc. Immediately
    redirects back with a code. In a real flow the user would see a consent
    screen; here we just bounce straight through to keep tests fast."""
    code = f"mock_code_{secrets.token_hex(8)}"
    _codes[code] = {
        "client_id": client_id,
        "scope": scope,
        "expires_at": time.time() + 600,
        "used": False,
    }
    sep = "&" if "?" in redirect_uri else "?"
    target = f"{redirect_uri}{sep}code={code}"
    if state:
        target += f"&state={state}"
    return RedirectResponse(target)


@app.get("/")
def root():
    return HTMLResponse(
        "<h1>mock-oauth</h1>"
        "<p>Pretends to be Google/Microsoft/Slack/GitHub/Shopify OAuth.</p>"
        "<p>POST /token, GET /auth, GET /api/...</p>"
    )


# ── Token exchange ─────────────────────────────────────────────────────────


@app.post("/token")
async def fake_token(request: Request):
    """Accept form-encoded OR JSON body. Returns the same fake access_token
    regardless of input, but does mark the code as used so replays fail."""
    try:
        form = await request.form()
        data = dict(form) if form else {}
    except Exception:
        data = {}
    if not data:
        try:
            data = await request.json()
        except Exception:
            data = {}

    code = data.get("code")
    entry = _codes.get(code) if code else None
    if not entry:
        return JSONResponse({"error": "invalid_code"}, status_code=400)
    if entry["used"]:
        return JSONResponse({"error": "code_already_used"}, status_code=400)
    if entry["expires_at"] < time.time():
        return JSONResponse({"error": "code_expired"}, status_code=400)
    entry["used"] = True

    return {
        "access_token": _TOKEN,
        "refresh_token": _REFRESH,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": entry.get("scope", ""),
    }


# ── Fake provider data (so connectors don't 404 in offline tests) ──────────


@app.get("/api/gmail/messages")
def gmail_msgs():
    return {
        "messages": [
            {"id": "m1", "subject": "Q3 board pack ready", "from": "anya@braivex.com",
             "snippet": "Numbers in the deck. Want a walkthrough?", "received": _iso(), "unread": True},
            {"id": "m2", "subject": "Vrindavan Glass — backup quote", "from": "raj@vrindavanglass.in",
             "snippet": "Attaching pricing for 40k units.", "received": _iso(), "unread": False},
        ]
    }


@app.get("/api/calendar/events")
def cal_events():
    return {
        "events": [
            {"id": "e1", "title": "Investor sync — Lightspeed",
             "start": _iso(60), "end": _iso(90), "location": "Zoom"},
            {"id": "e2", "title": "1:1 with Rohan", "start": _iso(180), "end": _iso(210)},
        ]
    }


@app.get("/api/slack/channels")
def slack():
    return {"channels": [{"id": "C1", "name": "founders"}, {"id": "C2", "name": "ops"}]}


@app.get("/api/github/notifications")
def github_notifs():
    return [
        {"id": "1", "subject": {"title": "Approve PR #42: caching layer", "type": "PullRequest",
                                 "url": "https://github.com/example/repo/pull/42"}},
    ]


@app.get("/api/linear/issues")
def linear():
    return {"data": {"issues": {"nodes": [{"id": "I1", "title": "Investigate stock flicker",
                                            "state": {"name": "blocked"}}]}}}


def _iso(offset_minutes: int = 0) -> str:
    from datetime import timedelta
    return (datetime.utcnow() + timedelta(minutes=offset_minutes)).isoformat() + "Z"
