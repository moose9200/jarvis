import httpx
from .base import Connector


class OutlookMailConnector(Connector):
    provider = "outlook_mail"
    BASE = "https://graph.microsoft.com/v1.0"

    async def fetch(self, top: int = 25, **_):
        tok = await self.access_fresh()
        if not tok:
            return []
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                f"{self.BASE}/me/messages",
                params={"$top": top, "$orderby": "receivedDateTime desc"},
                headers={"Authorization": f"Bearer {tok}"},
            )
        if r.status_code != 200:
            return []
        out = []
        for m in r.json().get("value", []):
            out.append({
                "id": m.get("id"),
                "from": m.get("from", {}).get("emailAddress", {}).get("address", ""),
                "subject": m.get("subject", "(no subject)"),
                "snippet": m.get("bodyPreview", ""),
                "received": m.get("receivedDateTime"),
                "thread_id": m.get("conversationId"),
                "unread": not m.get("isRead", False),
                "source": "outlook",
            })
        return out

    async def send(self, to: str, subject: str, body: str) -> bool:
        tok = await self.access_fresh()
        if not tok:
            return False
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                f"{self.BASE}/me/sendMail",
                json={
                    "message": {
                        "subject": subject,
                        "body": {"contentType": "Text", "content": body},
                        "toRecipients": [{"emailAddress": {"address": to}}],
                    },
                    "saveToSentItems": "true",
                },
                headers={"Authorization": f"Bearer {tok}"},
            )
        return r.status_code in (200, 202)
