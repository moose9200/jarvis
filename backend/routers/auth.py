import os
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from models import OAuthToken

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


def _save(db: Session, provider: str, access: str, refresh: str = None, ttl: int = 3600, scope: str = ""):
    tok = db.query(OAuthToken).filter_by(provider=provider).first()
    if not tok:
        tok = OAuthToken(provider=provider)
        db.add(tok)
    tok.access_token = access
    if refresh:
        tok.refresh_token = refresh
    tok.expires_at = datetime.utcnow() + timedelta(seconds=ttl)
    tok.scope = scope
    db.commit()


def _not_configured_redirect(provider: str):
    return RedirectResponse(f"{FRONTEND_URL}/?error=not_configured&provider={provider}")


@router.get("/status")
def status(db: Session = Depends(get_db)):
    rows = {t.provider: t for t in db.query(OAuthToken).all()}
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
@router.get("/google/start")
def google_start(request: Request):
    if not _is_configured("gmail"):
        return _not_configured_redirect("google")
    state = secrets.token_urlsafe(16)
    request.session["g_state"] = state
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


@router.get("/google/callback")
async def google_callback(request: Request, code: str, state: str, db: Session = Depends(get_db)):
    if state != request.session.get("g_state"):
        raise HTTPException(400, "state mismatch")
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
    _save(db, "gmail", j["access_token"], j.get("refresh_token"), j.get("expires_in", 3600), j.get("scope", ""))
    _save(db, "google_calendar", j["access_token"], j.get("refresh_token"), j.get("expires_in", 3600), j.get("scope", ""))
    return RedirectResponse(f"{FRONTEND_URL}/?connected=google")


@router.get("/gmail/start")
def gmail_start(request: Request):
    return google_start(request)


@router.get("/google_calendar/start")
def gcal_start(request: Request):
    return google_start(request)


# ---------- Microsoft (Outlook Mail + Calendar + Teams) ----------
@router.get("/microsoft/start")
def ms_start(request: Request):
    if not _is_configured("outlook_mail"):
        return _not_configured_redirect("microsoft")
    state = secrets.token_urlsafe(16)
    request.session["ms_state"] = state
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
    for p in ("outlook_mail", "outlook_calendar", "teams"):
        _save(db, p, j["access_token"], j.get("refresh_token"), j.get("expires_in", 3600), j.get("scope", ""))
    return RedirectResponse(f"{FRONTEND_URL}/?connected=microsoft")


@router.get("/outlook_mail/start")
def om_start(request: Request):
    return ms_start(request)


@router.get("/outlook_calendar/start")
def oc_start(request: Request):
    return ms_start(request)


@router.get("/teams/start")
def teams_start(request: Request):
    return ms_start(request)


# ---------- Slack ----------
@router.get("/slack/start")
def slack_start(request: Request):
    if not _is_configured("slack"):
        return _not_configured_redirect("slack")
    params = {
        "client_id": os.getenv("SLACK_CLIENT_ID", ""),
        "scope": "channels:history,channels:read,im:history,im:read,users:read",
        "redirect_uri": os.getenv("SLACK_REDIRECT_URI", ""),
    }
    return RedirectResponse("https://slack.com/oauth/v2/authorize?" + urlencode(params))


@router.get("/slack/callback")
async def slack_callback(code: str, db: Session = Depends(get_db)):
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
    _save(db, "slack", token, ttl=10**9)
    return RedirectResponse(f"{FRONTEND_URL}/?connected=slack")


# ---------- GitHub ----------
@router.get("/github/start")
def github_start():
    if not _is_configured("github"):
        return _not_configured_redirect("github")
    params = {
        "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
        "redirect_uri": os.getenv("GITHUB_REDIRECT_URI", ""),
        "scope": "repo notifications read:user",
    }
    return RedirectResponse("https://github.com/login/oauth/authorize?" + urlencode(params))


@router.get("/github/callback")
async def github_callback(code: str, db: Session = Depends(get_db)):
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
    _save(db, "github", j["access_token"], ttl=10**9, scope=j.get("scope", ""))
    return RedirectResponse(f"{FRONTEND_URL}/?connected=github")


# ---------- Static-key connectors ----------
@router.post("/linear/connect")
def linear_connect(db: Session = Depends(get_db)):
    key = os.getenv("LINEAR_API_KEY", "")
    if not key:
        raise HTTPException(400, "LINEAR_API_KEY missing")
    _save(db, "linear", key, ttl=10**9)
    return {"ok": True}


@router.get("/linear/start")
def linear_start(db: Session = Depends(get_db)):
    if not _is_configured("linear"):
        return _not_configured_redirect("linear")
    linear_connect(db)
    return RedirectResponse(f"{FRONTEND_URL}/?connected=linear")


@router.get("/jira/start")
def jira_start(db: Session = Depends(get_db)):
    if not _is_configured("jira"):
        return _not_configured_redirect("jira")
    _save(db, "jira", os.getenv("JIRA_TOKEN", ""), ttl=10**9)
    return RedirectResponse(f"{FRONTEND_URL}/?connected=jira")


@router.get("/notion/start")
def notion_start(db: Session = Depends(get_db)):
    if not _is_configured("notion"):
        return _not_configured_redirect("notion")
    _save(db, "notion", os.getenv("NOTION_TOKEN", ""), ttl=10**9)
    return RedirectResponse(f"{FRONTEND_URL}/?connected=notion")


@router.get("/whatsapp/start")
def whatsapp_start(db: Session = Depends(get_db)):
    if not _is_configured("whatsapp"):
        return _not_configured_redirect("whatsapp")
    _save(db, "whatsapp", os.getenv("WHATSAPP_TOKEN", ""), ttl=10**9)
    return RedirectResponse(f"{FRONTEND_URL}/?connected=whatsapp")
