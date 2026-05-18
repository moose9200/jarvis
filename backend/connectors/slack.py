import httpx
from .base import Connector


class SlackConnector(Connector):
    provider = "slack"

    async def fetch(self, limit_channels: int = 10, **_):
        tok = self.access()
        if not tok:
            return []
        headers = {"Authorization": f"Bearer {tok}"}
        out = []
        async with httpx.AsyncClient(timeout=15) as c:
            convo = await c.get(
                "https://slack.com/api/conversations.list",
                params={"types": "im,mpim,public_channel", "limit": limit_channels},
                headers=headers,
            )
            if convo.status_code != 200:
                return []
            channels = convo.json().get("channels", [])
            for ch in channels:
                ch_id = ch["id"]
                hist = await c.get(
                    "https://slack.com/api/conversations.history",
                    params={"channel": ch_id, "limit": 5},
                    headers=headers,
                )
                if hist.status_code != 200:
                    continue
                for m in hist.json().get("messages", []):
                    out.append({
                        "id": m.get("ts"),
                        "from": m.get("user", "?"),
                        "text": (m.get("text") or "")[:280],
                        "channel": ch.get("name") or ch_id,
                        "received": m.get("ts"),
                        "source": "slack",
                    })
        return out
