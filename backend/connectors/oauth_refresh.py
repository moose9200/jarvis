"""Per-provider OAuth access-token refresh — production-grade.

Public API:
    await refresh(db, provider, user_id) -> str | None
        Refresh the stored access_token in place. Returns plaintext token,
        or None on failure.

    await force_refresh(db, provider, user_id) -> str | None
        Same as refresh() but skips the "is it actually expired" check.
        Use this when a live API call returned 401 — the DB row may show
        the token as not-yet-expired but the provider rejected it (rotated
        upstream, scope revoked, etc.).

Concurrency: a per-(user_id, vendor) asyncio.Lock prevents thundering-herd
refreshes. If five concurrent API calls all hit an expired token, only
the first triggers a network call to the provider; the others wait, then
read the freshly-stored token.

Failure modes handled:
    - missing refresh_token              → returns None, no DB change
    - decrypt failure                    → returns None, no DB change
    - network error / 5xx from provider  → returns None, no DB change
                                           (token left intact; next call retries)
    - 400 invalid_grant from provider    → token is dead beyond recovery.
                                           Mark expires_at far in past + emit
                                           a Decision row "Reconnect <provider>"
                                           so the user sees actionable signal.

Providers handled today: google (gmail + google_calendar share a token),
microsoft (outlook_mail + outlook_calendar + teams share a token).
Slack / GitHub / Linear / Jira / Notion / WhatsApp access tokens are
non-expiring or use static API keys — `refresh()` is a no-op for them.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from crypto import decrypt, encrypt
from models import Decision, OAuthToken

logger = logging.getLogger("jarvis.oauth_refresh")

PROVIDER_GROUPS: dict[str, dict] = {
    "gmail":            {"vendor": "google",    "siblings": ["gmail", "google_calendar"]},
    "google_calendar":  {"vendor": "google",    "siblings": ["gmail", "google_calendar"]},
    "outlook_mail":     {"vendor": "microsoft", "siblings": ["outlook_mail", "outlook_calendar", "teams"]},
    "outlook_calendar": {"vendor": "microsoft", "siblings": ["outlook_mail", "outlook_calendar", "teams"]},
    "teams":            {"vendor": "microsoft", "siblings": ["outlook_mail", "outlook_calendar", "teams"]},
}

NON_EXPIRING = {"slack", "github", "linear", "jira", "notion", "whatsapp"}

# Single-flight: one in-flight refresh per (user_id, vendor) at a time.
# Locks live for the process lifetime — cheap, no cleanup needed.
_LOCKS: dict[tuple[int, str], asyncio.Lock] = {}


def _lock_for(user_id: int, vendor: str) -> asyncio.Lock:
    key = (user_id, vendor)
    lock = _LOCKS.get(key)
    if lock is None:
        lock = _LOCKS[key] = asyncio.Lock()
    return lock


async def refresh(db: Session, provider: str, user_id: int) -> Optional[str]:
    """Refresh if the stored token is expired (with skew). No-op if a
    different async task already won the lock and refreshed during our
    wait — we just read the new row."""
    return await _do_refresh(db, provider, user_id, force=False)


async def force_refresh(db: Session, provider: str, user_id: int) -> Optional[str]:
    """Refresh unconditionally. Use this when a live API call returned 401
    and the cached token looks fresh — the provider has invalidated it
    upstream and we need a new one immediately."""
    return await _do_refresh(db, provider, user_id, force=True)


async def _do_refresh(db: Session, provider: str, user_id: int, force: bool) -> Optional[str]:
    if provider in NON_EXPIRING:
        return None
    group = PROVIDER_GROUPS.get(provider)
    if not group:
        return None

    vendor = group["vendor"]
    lock = _lock_for(user_id, vendor)

    async with lock:
        # Re-read after acquiring the lock — a sibling task may have refreshed
        # while we were queued.
        row = _read_row(db, group["siblings"], user_id)
        if not row:
            return None

        if not force and row.expires_at and row.expires_at - timedelta(minutes=2) > datetime.utcnow():
            # Another task already refreshed. Return the fresh token.
            try:
                return decrypt(row.access_token)
            except Exception:
                logger.exception("decrypt after winning lock failed")
                return None

        if not row.refresh_token:
            logger.warning("no refresh_token for user_id=%s vendor=%s", user_id, vendor)
            return None

        try:
            refresh_plain = decrypt(row.refresh_token)
        except Exception:
            logger.exception("refresh_token decrypt failed")
            return None
        if not refresh_plain:
            return None

        new, err = await _call_provider(vendor, refresh_plain)
        if err == "invalid_grant":
            _surface_reconnect(db, vendor, user_id, group["siblings"])
            return None
        if not new or not new.get("access_token"):
            return None  # transient — leave row intact, next call retries

        return _store(db, group["siblings"], user_id, new)


def _read_row(db: Session, siblings: list[str], user_id: int) -> Optional[OAuthToken]:
    return (
        db.query(OAuthToken)
        .filter(OAuthToken.provider.in_(siblings), OAuthToken.user_id == user_id)
        .first()
    )


def _store(db: Session, siblings: list[str], user_id: int, new: dict) -> str:
    access = new["access_token"]
    expires_in = int(new.get("expires_in", 3600))
    new_refresh = new.get("refresh_token")  # Microsoft rotates these

    enc_access = encrypt(access)
    enc_refresh = encrypt(new_refresh) if new_refresh else None
    new_exp = datetime.utcnow() + timedelta(seconds=expires_in)

    rows = (
        db.query(OAuthToken)
        .filter(OAuthToken.provider.in_(siblings), OAuthToken.user_id == user_id)
        .all()
    )
    for r in rows:
        r.access_token = enc_access
        if enc_refresh:
            r.refresh_token = enc_refresh
        r.expires_at = new_exp
    db.commit()
    logger.info("refreshed user_id=%s siblings=%s exp_in=%ss", user_id, siblings, expires_in)
    return access


def _surface_reconnect(db: Session, vendor: str, user_id: int, siblings: list[str]) -> None:
    """invalid_grant means the user revoked the app or the refresh token has
    been rotated out from under us. Make sure the user sees this:
      1. Stamp expires_at to epoch so subsequent access_fresh() short-circuits
      2. Create a pending Decision row prompting "Reconnect <vendor>"
    Idempotent — the Decision dedupe key prevents pile-up.
    """
    far_past = datetime(2000, 1, 1)
    rows = (
        db.query(OAuthToken)
        .filter(OAuthToken.provider.in_(siblings), OAuthToken.user_id == user_id)
        .all()
    )
    for r in rows:
        r.expires_at = far_past

    src_id = f"reconnect_{vendor}"
    existing = (
        db.query(Decision)
        .filter_by(user_id=user_id, source="reconnect", source_id=src_id)
        .filter(Decision.status.in_(["pending", "snoozed"]))
        .first()
    )
    if not existing:
        db.add(
            Decision(
                user_id=user_id,
                source="reconnect",
                source_id=src_id,
                title=f"Reconnect {vendor.title()} — token was revoked",
                ai_suggestion=(
                    f"JARVIS lost access to your {vendor} account. The most "
                    f"likely cause is that you revoked the app in your provider's "
                    f"security settings, or your provider rotated your refresh "
                    f"token. Open Profile → Integrations → Connect to re-grant."
                ),
                status="pending",
                created_at=datetime.utcnow(),
                context_json={"vendor": vendor},
            )
        )
    db.commit()
    logger.warning("invalid_grant for user_id=%s vendor=%s — surfaced reconnect Decision", user_id, vendor)


# ── Provider HTTP calls ─────────────────────────────────────────────────────


async def _call_provider(vendor: str, refresh_token: str) -> tuple[Optional[dict], Optional[str]]:
    """Returns (payload, error_code). error_code="invalid_grant" means the
    refresh_token is dead; anything else (None, "transient") leaves the row
    intact so the next call retries."""
    if vendor == "google":
        return await _refresh_google(refresh_token)
    if vendor == "microsoft":
        return await _refresh_microsoft(refresh_token)
    return None, None


async def _refresh_google(refresh_token: str) -> tuple[Optional[dict], Optional[str]]:
    cid = os.getenv("GOOGLE_CLIENT_ID", "")
    sec = os.getenv("GOOGLE_CLIENT_SECRET", "")
    if not cid or not sec:
        return None, None
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": cid,
                    "client_secret": sec,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
    except Exception:
        logger.exception("google refresh network error")
        return None, "transient"
    if r.status_code == 200:
        return r.json(), None
    body = r.text[:300]
    if r.status_code == 400 and "invalid_grant" in body:
        return None, "invalid_grant"
    logger.warning("google refresh returned %s: %s", r.status_code, body)
    return None, "transient"


async def _refresh_microsoft(refresh_token: str) -> tuple[Optional[dict], Optional[str]]:
    cid = os.getenv("MS_CLIENT_ID", "")
    sec = os.getenv("MS_CLIENT_SECRET", "")
    tenant = os.getenv("MS_TENANT_ID", "common")
    if not cid or not sec:
        return None, None
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                data={
                    "client_id": cid,
                    "client_secret": sec,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
    except Exception:
        logger.exception("microsoft refresh network error")
        return None, "transient"
    if r.status_code == 200:
        return r.json(), None
    body = r.text[:300]
    if r.status_code == 400 and "invalid_grant" in body:
        return None, "invalid_grant"
    logger.warning("microsoft refresh returned %s: %s", r.status_code, body)
    return None, "transient"
