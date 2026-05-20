"""Base class for all external-service connectors.

Provides:
    token()            current OAuthToken row (or None)
    access()           decrypted access_token; auto-refreshes if expired
    refresh()          decrypted refresh_token
    access_fresh()     async — returns access token, refreshing first if
                       the row is expired or near-expiry. Always use this
                       inside async API call paths.

`access()` (sync) does NOT refresh — it's used for diagnostics + by code
paths that don't have an event loop. `access_fresh()` is what
async-connector methods (Gmail/Outlook/Calendar fetch) should call.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from crypto import decrypt
from models import OAuthToken


# How close to the access_token's expiry before we proactively refresh.
# Keeps us from racing a request against a token that dies mid-flight.
_REFRESH_SKEW = timedelta(minutes=2)


class Connector(ABC):
    provider: str = ""

    def __init__(self, db: Session, user_id: Optional[int] = None):
        self.db = db
        self.user_id = user_id

    def token(self) -> Optional[OAuthToken]:
        q = self.db.query(OAuthToken).filter_by(provider=self.provider)
        if self.user_id is not None:
            q = q.filter_by(user_id=self.user_id)
        return q.first()

    def access(self) -> Optional[str]:
        """Sync — returns whatever's in the DB, no refresh. Diagnostics only."""
        t = self.token()
        return decrypt(t.access_token) if t else None

    def refresh(self) -> Optional[str]:
        t = self.token()
        return decrypt(t.refresh_token) if (t and t.refresh_token) else None

    async def access_fresh(self) -> Optional[str]:
        """Async — returns a non-expired access_token. Proactively refreshes
        if the stored expires_at is past (with 2-min skew). Returns None
        only when there's no token row or refresh failed."""
        t = self.token()
        if not t:
            return None

        if t.expires_at and t.expires_at - _REFRESH_SKEW <= datetime.utcnow():
            from .oauth_refresh import refresh as do_refresh
            if self.user_id is not None:
                refreshed = await do_refresh(self.db, self.provider, self.user_id)
                if refreshed:
                    return refreshed

        return decrypt(t.access_token)

    async def force_refresh(self) -> Optional[str]:
        """Use when an API call returned 401 even though our cached token
        looked fresh. The provider has invalidated the token upstream.
        Returns the new plaintext token, or None if refresh failed."""
        if self.user_id is None:
            return None
        from .oauth_refresh import force_refresh as do_force
        return await do_force(self.db, self.provider, self.user_id)

    async def authed_get(self, client, url: str, **kwargs):
        """httpx.AsyncClient.get with automatic Bearer header + retry-once
        on 401 (after a force_refresh). Returns the final Response or None
        if no token is available at all.

        Usage:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await self.authed_get(c, "https://gmail.googleapis.com/...")
                if r and r.status_code == 200: ...
        """
        token = await self.access_fresh()
        if not token:
            return None
        headers = {**kwargs.pop("headers", {}), "Authorization": f"Bearer {token}"}
        r = await client.get(url, headers=headers, **kwargs)
        if r.status_code == 401:
            new_token = await self.force_refresh()
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                r = await client.get(url, headers=headers, **kwargs)
        return r

    async def authed_post(self, client, url: str, **kwargs):
        """Same as authed_get but for POST. Same retry-on-401 semantics."""
        token = await self.access_fresh()
        if not token:
            return None
        headers = {**kwargs.pop("headers", {}), "Authorization": f"Bearer {token}"}
        r = await client.post(url, headers=headers, **kwargs)
        if r.status_code == 401:
            new_token = await self.force_refresh()
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                r = await client.post(url, headers=headers, **kwargs)
        return r

    @abstractmethod
    async def fetch(self, **kwargs) -> List[Dict[str, Any]]:
        ...
