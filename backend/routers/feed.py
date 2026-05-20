import asyncio
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User
from routers.users import get_current_user
from connectors.gmail import GmailConnector
from connectors.outlook_mail import OutlookMailConnector
from connectors.google_calendar import GoogleCalendarConnector
from connectors.outlook_calendar import OutlookCalendarConnector
from connectors.slack import SlackConnector
from connectors.teams import TeamsConnector
from connectors.whatsapp import WhatsAppConnector
from connectors.github import GitHubConnector
from connectors.linear import LinearConnector
from connectors.jira import JiraConnector
from connectors.notion import NotionConnector
from intelligence.email_scorer import EmailScorer

router = APIRouter()


async def _safe(coro):
    try:
        return await coro
    except Exception:
        return []


@router.get("/feed")
async def feed(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    uid = current_user.id

    def _c(cls):
        return cls(db, uid)

    (
        g_mail, o_mail, g_evt, o_evt, slk, tms, wap, ghn, lin, jr, ntn,
    ) = await asyncio.gather(
        _safe(_c(GmailConnector).fetch(max_results=25)),
        _safe(_c(OutlookMailConnector).fetch(top=25)),
        # 14-day window — picks up the next ~2 weeks of events. Same-day-only
        # is too narrow (most users have empty same-day calendars by mid-day).
        _safe(_c(GoogleCalendarConnector).fetch(days=14)),
        _safe(_c(OutlookCalendarConnector).fetch(days=14)),
        _safe(_c(SlackConnector).fetch()),
        _safe(_c(TeamsConnector).fetch()),
        _safe(_c(WhatsAppConnector).fetch()),
        _safe(_c(GitHubConnector).fetch()),
        _safe(_c(LinearConnector).fetch()),
        _safe(_c(JiraConnector).fetch()),
        _safe(_c(NotionConnector).fetch()),
    )

    all_mail = (g_mail or []) + (o_mail or [])
    scorer = EmailScorer(db, uid)
    for m in all_mail:
        m["priority"] = scorer.score(m)
    all_mail.sort(key=lambda x: x["priority"], reverse=True)

    events = sorted((g_evt or []) + (o_evt or []), key=lambda e: e.get("start") or "")
    messages = (slk or []) + (tms or []) + (wap or [])
    tasks = (lin or []) + (jr or []) + (ntn or [])
    projects = (ghn or [])

    return {
        "events": events,
        "emails": all_mail[:15],
        "messages": messages[:10],
        "tasks": tasks[:20],
        "projects": projects[:15],
    }
