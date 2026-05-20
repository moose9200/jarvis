import base64
import httpx
from email.mime.text import MIMEText
from .base import Connector


class GmailConnector(Connector):
    provider = "gmail"
    BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

    async def fetch(self, max_results: int = 25, **_):
        tok = await self.access_fresh()
        if not tok:
            return []
        headers = {"Authorization": f"Bearer {tok}"}
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                f"{self.BASE}/messages",
                params={"maxResults": max_results, "q": "newer_than:2d in:inbox"},
                headers=headers,
            )
            if r.status_code != 200:
                return []
            ids = [m["id"] for m in r.json().get("messages", [])]
            out = []
            for mid in ids:
                m = await c.get(
                    f"{self.BASE}/messages/{mid}",
                    params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
                    headers=headers,
                )
                if m.status_code != 200:
                    continue
                j = m.json()
                headers_list = {h["name"]: h["value"] for h in j["payload"].get("headers", [])}
                out.append({
                    "id": mid,
                    "from": headers_list.get("From", ""),
                    "subject": headers_list.get("Subject", "(no subject)"),
                    "snippet": j.get("snippet", ""),
                    "received": headers_list.get("Date", ""),
                    "thread_id": j.get("threadId", ""),
                    "unread": "UNREAD" in j.get("labelIds", []),
                    "source": "gmail",
                })
            return out

    async def send(self, to: str, subject: str, body: str) -> bool:
        tok = await self.access_fresh()
        if not tok:
            return False
        msg = MIMEText(body)
        msg["to"] = to
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                f"{self.BASE}/messages/send",
                json={"raw": raw},
                headers={"Authorization": f"Bearer {tok}"},
            )
        return r.status_code in (200, 202)
