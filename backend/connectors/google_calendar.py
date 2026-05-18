from datetime import datetime, timedelta, timezone
import httpx
from .base import Connector


class GoogleCalendarConnector(Connector):
    provider = "google_calendar"

    async def fetch(self, days: int = 1, **_):
        tok = self.access()
        if not tok:
            return []
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days)
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                params={
                    "timeMin": now.isoformat(),
                    "timeMax": end.isoformat(),
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": 25,
                },
                headers={"Authorization": f"Bearer {tok}"},
            )
        if r.status_code != 200:
            return []
        out = []
        for e in r.json().get("items", []):
            out.append({
                "id": e.get("id"),
                "title": e.get("summary", "(untitled)"),
                "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
                "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
                "location": e.get("location"),
                "attendees": [a.get("email") for a in e.get("attendees", [])],
                "source": "google",
            })
        return out
