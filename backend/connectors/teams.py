import httpx
from .base import Connector


class TeamsConnector(Connector):
    provider = "teams"

    async def fetch(self, top: int = 15, **_):
        tok = self.access()
        if not tok:
            return []
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                "https://graph.microsoft.com/v1.0/me/chats",
                params={"$top": top, "$expand": "lastMessagePreview"},
                headers={"Authorization": f"Bearer {tok}"},
            )
        if r.status_code != 200:
            return []
        out = []
        for chat in r.json().get("value", []):
            lm = chat.get("lastMessagePreview") or {}
            body = lm.get("body", {}) or {}
            out.append({
                "id": chat.get("id"),
                "from": (lm.get("from") or {}).get("user", {}).get("displayName", "?"),
                "text": (body.get("content") or "")[:280],
                "channel": chat.get("topic") or "DM",
                "received": lm.get("createdDateTime") or chat.get("lastUpdatedDateTime"),
                "source": "teams",
            })
        return out
