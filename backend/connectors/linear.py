import httpx
from .base import Connector


class LinearConnector(Connector):
    provider = "linear"

    QUERY = """
    query Me {
      viewer {
        assignedIssues(first: 25, filter: { state: { type: { nin: ["completed","canceled"] } } }) {
          nodes {
            id
            identifier
            title
            state { name }
            dueDate
            url
          }
        }
      }
    }
    """

    async def fetch(self, **_):
        tok = self.access()
        if not tok:
            return []
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                "https://api.linear.app/graphql",
                json={"query": self.QUERY},
                headers={"Authorization": tok, "Content-Type": "application/json"},
            )
        if r.status_code != 200:
            return []
        nodes = r.json().get("data", {}).get("viewer", {}).get("assignedIssues", {}).get("nodes", [])
        out = []
        for n in nodes:
            out.append({
                "id": n["id"],
                "title": f"{n['identifier']} {n['title']}",
                "status": (n.get("state") or {}).get("name", "?"),
                "due": n.get("dueDate"),
                "url": n.get("url"),
                "source": "linear",
            })
        return out
