import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from crypto import encrypt
from database import get_db
from models import OAuthToken, User
from routers.users import get_current_user, get_oauth_user

router = APIRouter()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost")

PROVIDERS = [
    ("gmail", "Gmail"),
    ("google_calendar", "Google Calendar"),
    ("outlook_mail", "Outlook Mail"),
    ("outlook_calendar", "Outlook Calendar"),
    ("slack", "Slack"),
    ("teams", "Microsoft Teams"),
    ("whatsapp", "WhatsApp"),
    ("github", "GitHub"),
    ("linear", "Linear"),
    ("jira", "Jira"),
    ("notion", "Notion"),
]

PROVIDER_CREDENTIALS = {
    "gmail":            ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
    "google_calendar":  ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
    "outlook_mail":     ["MS_CLIENT_ID", "MS_CLIENT_SECRET"],
    "outlook_calendar": ["MS_CLIENT_ID", "MS_CLIENT_SECRET"],
    "teams":            ["MS_CLIENT_ID", "MS_CLIENT_SECRET"],
    "slack":            ["SLACK_CLIENT_ID", "SLACK_CLIENT_SECRET"],
    "github":           ["GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"],
    "linear":           ["LINEAR_API_KEY"],
    "jira":             ["JIRA_TOKEN"],
    "notion":           ["NOTION_TOKEN"],
    "whatsapp":         ["WHATSAPP_TOKEN"],
}


def _is_configured(name: str) -> bool:
    return all(os.getenv(k, "").strip() for k in PROVIDER_CREDENTIALS.get(name, []))


def _save(db: Session, provider: str, access: str, refresh: str = None,
          ttl: int = 3600, scope: str = "", user_id: Optional[int] = None):
    q = db.query(OAuthToken).filter_by(provider=provider)
    if user_id is not None:
        q = q.filter_by(user_id=user_id)
    tok = q.first()
    if not tok:
        tok = OAuthToken(provider=provider, user_id=user_id)
        db.add(tok)
    tok.access_token = encrypt(access)
    if refresh:
        tok.refresh_token = encrypt(refresh)
    tok.expires_at = datetime.utcnow() + timedelta(seconds=ttl)
    tok.scope = scope
    db.commit()
    # Newly connected source — invalidate feed cache so the next /api/feed
    # request actually re-fans-out and surfaces this connector's data.
    if user_id is not None:
        try:
            from routers.feed import invalidate_feed_cache
            invalidate_feed_cache(user_id)
        except Exception:
            pass


def _get_user_id(request: Request) -> Optional[int]:
    """Retrieve user_id stored in session during OAuth start."""
    return request.session.get("oauth_user_id")


def _not_configured_redirect(provider: str):
    return RedirectResponse(f"{FRONTEND_URL}/?error=not_configured&provider={provider}")


@router.get("/status")
def status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = {
        t.provider
        for t in db.query(OAuthToken).filter_by(user_id=current_user.id).all()
    }
    out = []
    for name, display in PROVIDERS:
        out.append({
            "name": name,
            "display": display,
            "connected": name in rows,
            "configured": _is_configured(name),
        })
    return {"connectors": out}


# ---------- Google (Gmail + Calendar share a token) ----------
def _google_oauth_redirect(request: Request, current_user: User):
    if not _is_configured("gmail"):
        return _not_configured_redirect("google")
    state = secrets.token_urlsafe(16)
    request.session["g_state"] = state
    request.session["oauth_user_id"] = current_user.id
    params = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", ""),
        "response_type": "code",
        "scope": (
            "openid email profile "
            "https://www.googleapis.com/auth/gmail.readonly "
            "https://www.googleapis.com/auth/gmail.send "
            "https://www.googleapis.com/auth/calendar.readonly"
        ),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return RedirectResponse("https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params))


@router.get("/google/start")
def google_start(request: Request, current_user: User = Depends(get_oauth_user)):
    return _google_oauth_redirect(request, current_user)


@router.get("/google/callback")
async def google_callback(request: Request, code: str, state: str, db: Session = Depends(get_db)):
    if state != request.session.get("g_state"):
        raise HTTPException(400, "state mismatch")
    user_id = _get_user_id(request)
    async with httpx.AsyncClient() as c:
        r = await c.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", ""),
                "grant_type": "authorization_code",
            },
        )
    j = r.json()
    if "access_token" not in j:
        raise HTTPException(400, f"oauth error: {j}")
    kw = dict(refresh=j.get("refresh_token"), ttl=j.get("expires_in", 3600), scope=j.get("scope", ""), user_id=user_id)
    _save(db, "gmail", j["access_token"], **kw)
    _save(db, "google_calendar", j["access_token"], **kw)
    return RedirectResponse(f"{FRONTEND_URL}/?connected=google")


@router.get("/gmail/start")
def gmail_start(request: Request, current_user: User = Depends(get_oauth_user)):
    return google_start(request, current_user)


@router.get("/google_calendar/start")
def gcal_start(request: Request, current_user: User = Depends(get_oauth_user)):
    return google_start(request, current_user)


# ---------- Microsoft (Outlook Mail + Calendar + Teams) ----------
@router.get("/microsoft/start")
def ms_start(request: Request, current_user: User = Depends(get_oauth_user)):
    if not _is_configured("outlook_mail"):
        return _not_configured_redirect("microsoft")
    state = secrets.token_urlsafe(16)
    request.session["ms_state"] = state
    request.session["oauth_user_id"] = current_user.id
    params = {
        "client_id": os.getenv("MS_CLIENT_ID", ""),
        "redirect_uri": os.getenv("MS_REDIRECT_URI", ""),
        "response_type": "code",
        "scope": "offline_access User.Read Mail.Read Mail.Send Calendars.Read Chat.Read",
        "state": state,
    }
    tenant = os.getenv("MS_TENANT_ID", "common")
    return RedirectResponse(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?" + urlencode(params)
    )


@router.get("/microsoft/callback")
async def ms_callback(request: Request, code: str, state: str, db: Session = Depends(get_db)):
    if state != request.session.get("ms_state"):
        raise HTTPException(400, "state mismatch")
    user_id = _get_user_id(request)
    tenant = os.getenv("MS_TENANT_ID", "common")
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            data={
                "client_id": os.getenv("MS_CLIENT_ID", ""),
                "client_secret": os.getenv("MS_CLIENT_SECRET", ""),
                "code": code,
                "redirect_uri": os.getenv("MS_REDIRECT_URI", ""),
                "grant_type": "authorization_code",
            },
        )
    j = r.json()
    if "access_token" not in j:
        raise HTTPException(400, f"oauth error: {j}")
    kw = dict(refresh=j.get("refresh_token"), ttl=j.get("expires_in", 3600), scope=j.get("scope", ""), user_id=user_id)
    for p in ("outlook_mail", "outlook_calendar", "teams"):
        _save(db, p, j["access_token"], **kw)
    return RedirectResponse(f"{FRONTEND_URL}/?connected=microsoft")


@router.get("/outlook_mail/start")
def om_start(request: Request, current_user: User = Depends(get_oauth_user)):
    return ms_start(request, current_user)


@router.get("/outlook_calendar/start")
def oc_start(request: Request, current_user: User = Depends(get_oauth_user)):
    return ms_start(request, current_user)


@router.get("/teams/start")
def teams_start(request: Request, current_user: User = Depends(get_oauth_user)):
    return ms_start(request, current_user)


# ---------- Slack ----------
@router.get("/slack/start")
def slack_start(request: Request, current_user: User = Depends(get_oauth_user)):
    if not _is_configured("slack"):
        return _not_configured_redirect("slack")
    request.session["oauth_user_id"] = current_user.id
    params = {
        "client_id": os.getenv("SLACK_CLIENT_ID", ""),
        "scope": "channels:history,channels:read,im:history,im:read,users:read",
        "redirect_uri": os.getenv("SLACK_REDIRECT_URI", ""),
    }
    return RedirectResponse("https://slack.com/oauth/v2/authorize?" + urlencode(params))


@router.get("/slack/callback")
async def slack_callback(request: Request, code: str, db: Session = Depends(get_db)):
    user_id = _get_user_id(request)
    async with httpx.AsyncClient() as c:
        r = await c.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "code": code,
                "client_id": os.getenv("SLACK_CLIENT_ID", ""),
                "client_secret": os.getenv("SLACK_CLIENT_SECRET", ""),
                "redirect_uri": os.getenv("SLACK_REDIRECT_URI", ""),
            },
        )
    j = r.json()
    token = j.get("authed_user", {}).get("access_token") or j.get("access_token")
    if not token:
        raise HTTPException(400, f"slack oauth error: {j}")
    _save(db, "slack", token, ttl=10**9, user_id=user_id)
    return RedirectResponse(f"{FRONTEND_URL}/?connected=slack")


# ---------- GitHub ----------
@router.get("/github/start")
def github_start(request: Request, current_user: User = Depends(get_oauth_user)):
    if not _is_configured("github"):
        return _not_configured_redirect("github")
    request.session["oauth_user_id"] = current_user.id
    params = {
        "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
        "redirect_uri": os.getenv("GITHUB_REDIRECT_URI", ""),
        "scope": "repo notifications read:user",
    }
    return RedirectResponse("https://github.com/login/oauth/authorize?" + urlencode(params))


@router.get("/github/callback")
async def github_callback(request: Request, code: str, db: Session = Depends(get_db)):
    user_id = _get_user_id(request)
    async with httpx.AsyncClient() as c:
        r = await c.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
                "client_secret": os.getenv("GITHUB_CLIENT_SECRET", ""),
                "code": code,
                "redirect_uri": os.getenv("GITHUB_REDIRECT_URI", ""),
            },
            headers={"Accept": "application/json"},
        )
    j = r.json()
    if "access_token" not in j:
        raise HTTPException(400, f"github oauth error: {j}")
    _save(db, "github", j["access_token"], ttl=10**9, scope=j.get("scope", ""), user_id=user_id)
    return RedirectResponse(f"{FRONTEND_URL}/?connected=github")


# ---------- Static-key connectors ----------
@router.get("/linear/start")
def linear_start(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_oauth_user)):
    if not _is_configured("linear"):
        return _not_configured_redirect("linear")
    _save(db, "linear", os.getenv("LINEAR_API_KEY", ""), ttl=10**9, user_id=current_user.id)
    return RedirectResponse(f"{FRONTEND_URL}/?connected=linear")


@router.get("/jira/start")
def jira_start(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_oauth_user)):
    if not _is_configured("jira"):
        return _not_configured_redirect("jira")
    _save(db, "jira", os.getenv("JIRA_TOKEN", ""), ttl=10**9, user_id=current_user.id)
    return RedirectResponse(f"{FRONTEND_URL}/?connected=jira")


@router.get("/notion/start")
def notion_start(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_oauth_user)):
    if not _is_configured("notion"):
        return _not_configured_redirect("notion")
    _save(db, "notion", os.getenv("NOTION_TOKEN", ""), ttl=10**9, user_id=current_user.id)
    return RedirectResponse(f"{FRONTEND_URL}/?connected=notion")


@router.get("/whatsapp/start")
def whatsapp_start(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_oauth_user)):
    if not _is_configured("whatsapp"):
        return _not_configured_redirect("whatsapp")
    _save(db, "whatsapp", os.getenv("WHATSAPP_TOKEN", ""), ttl=10**9, user_id=current_user.id)
    return RedirectResponse(f"{FRONTEND_URL}/?connected=whatsapp")


# ---------- Disconnect ----------
@router.delete("/{provider}/disconnect")
def disconnect(provider: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tok = db.query(OAuthToken).filter_by(provider=provider, user_id=current_user.id).first()
    if not tok:
        raise HTTPException(404, "Provider not connected")
    db.delete(tok)
    db.commit()
    # Best-effort: drop the user's cached feed so the disconnected source
    # disappears from the dashboard immediately rather than after the TTL.
    try:
        from routers.feed import invalidate_feed_cache
        invalidate_feed_cache(current_user.id)
    except Exception:
        pass
    return {"ok": True, "disconnected": provider}
