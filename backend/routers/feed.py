import asyncio
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
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
async def feed(db: Session = Depends(get_db)):
    gmail = GmailConnector(db)
    outlook = OutlookMailConnector(db)
    gcal = GoogleCalendarConnector(db)
    ocal = OutlookCalendarConnector(db)
    slack = SlackConnector(db)
    teams = TeamsConnector(db)
    wa = WhatsAppConnector(db)
    gh = GitHubConnector(db)
    linear = LinearConnector(db)
    jira = JiraConnector(db)
    notion = NotionConnector(db)

    (
        g_mail, o_mail, g_evt, o_evt, slk, tms, wap, ghn, lin, jr, ntn,
    ) = await asyncio.gather(
        _safe(gmail.fetch(max_results=25)),
        _safe(outlook.fetch(top=25)),
        _safe(gcal.fetch(days=1)),
        _safe(ocal.fetch(days=1)),
        _safe(slack.fetch()),
        _safe(teams.fetch()),
        _safe(wa.fetch()),
        _safe(gh.fetch()),
        _safe(linear.fetch()),
        _safe(jira.fetch()),
        _safe(notion.fetch()),
    )

    all_mail = (g_mail or []) + (o_mail or [])
    scorer = EmailScorer(db)
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
