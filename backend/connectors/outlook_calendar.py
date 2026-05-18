from datetime import datetime, timedelta, timezone
import httpx
from .base import Connector


class OutlookCalendarConnector(Connector):
    provider = "outlook_calendar"

    async def fetch(self, days: int = 1, **_):
        tok = self.access()
        if not tok:
            return []
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days)
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                "https://graph.microsoft.com/v1.0/me/calendarView",
                params={
                    "startDateTime": now.isoformat(),
                    "endDateTime": end.isoformat(),
                    "$orderby": "start/dateTime",
                    "$top": 25,
                },
                headers={"Authorization": f"Bearer {tok}"},
            )
        if r.status_code != 200:
            return []
        out = []
        for e in r.json().get("value", []):
            out.append({
                "id": e.get("id"),
                "title": e.get("subject", "(untitled)"),
                "start": e.get("start", {}).get("dateTime"),
                "end": e.get("end", {}).get("dateTime"),
                "location": e.get("location", {}).get("displayName"),
                "attendees": [a.get("emailAddress", {}).get("address") for a in e.get("attendees", [])],
                "source": "outlook",
            })
        return out
