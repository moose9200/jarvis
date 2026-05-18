import os
import base64
import httpx
from .base import Connector


class JiraConnector(Connector):
    provider = "jira"

    async def fetch(self, **_):
        base = os.getenv("JIRA_BASE", "")
        email = os.getenv("JIRA_EMAIL", "")
        token = self.access() or os.getenv("JIRA_TOKEN", "")
        if not base or not email or not token:
            return []
        auth = base64.b64encode(f"{email}:{token}".encode()).decode()
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                f"{base.rstrip('/')}/rest/api/3/search",
                params={
                    "jql": "assignee = currentUser() AND statusCategory != Done ORDER BY duedate ASC",
                    "maxResults": 25,
                    "fields": "summary,status,duedate",
                },
                headers={"Authorization": f"Basic {auth}", "Accept": "application/json"},
            )
        if r.status_code != 200:
            return []
        out = []
        for i in r.json().get("issues", []):
            f = i.get("fields", {})
            out.append({
                "id": i.get("id"),
                "title": f"{i.get('key')} {f.get('summary', '')}",
                "status": (f.get("status") or {}).get("name", "?"),
                "due": f.get("duedate"),
                "url": f"{base.rstrip('/')}/browse/{i.get('key')}",
                "source": "jira",
            })
        return out
