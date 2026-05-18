import httpx
from .base import Connector


class GitHubConnector(Connector):
    provider = "github"

    async def fetch(self, **_):
        tok = self.access()
        if not tok:
            return []
        h = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}
        out = []
        async with httpx.AsyncClient(timeout=15) as c:
            n = await c.get("https://api.github.com/notifications", headers=h)
            if n.status_code == 200:
                for item in n.json()[:20]:
                    sub = item.get("subject", {})
                    out.append({
                        "id": item.get("id"),
                        "title": sub.get("title", "(no title)"),
                        "status": sub.get("type", "Notification"),
                        "url": sub.get("url", ""),
                        "due": None,
                        "source": "github",
                    })
            iq = await c.get(
                "https://api.github.com/search/issues",
                params={"q": "is:open assignee:@me archived:false"},
                headers=h,
            )
            if iq.status_code == 200:
                for item in iq.json().get("items", [])[:15]:
                    out.append({
                        "id": str(item.get("id")),
                        "title": item.get("title", ""),
                        "status": item.get("state", "open"),
                        "url": item.get("html_url", ""),
                        "due": None,
                        "source": "github",
                    })
        return out
