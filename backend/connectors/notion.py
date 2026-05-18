import httpx
from .base import Connector


class NotionConnector(Connector):
    provider = "notion"

    async def fetch(self, **_):
        tok = self.access()
        if not tok:
            return []
        h = {
            "Authorization": f"Bearer {tok}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                "https://api.notion.com/v1/search",
                json={
                    "filter": {"property": "object", "value": "page"},
                    "page_size": 25,
                    "sort": {"direction": "descending", "timestamp": "last_edited_time"},
                },
                headers=h,
            )
        if r.status_code != 200:
            return []
        out = []
        for p in r.json().get("results", []):
            props = p.get("properties", {})
            title = ""
            for v in props.values():
                if v.get("type") == "title":
                    title = "".join([t.get("plain_text", "") for t in v.get("title", [])])
                    break
            out.append({
                "id": p.get("id"),
                "title": title or "(untitled)",
                "status": "page",
                "due": None,
                "url": p.get("url"),
                "source": "notion",
            })
        return out
