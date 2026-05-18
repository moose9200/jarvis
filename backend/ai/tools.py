from typing import Any, Dict, List
from sqlalchemy.orm import Session
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

TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "get_calendar_events",
        "description": "Fetch upcoming calendar events from Google Calendar or Outlook Calendar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look ahead (default 1).",
                    "default": 1,
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_priority_emails",
        "description": "Fetch and score the most important recent emails from Gmail or Outlook.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of emails to return (default 10).",
                    "default": 10,
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_slack_messages",
        "description": "Fetch recent Slack messages from the user's workspace.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_teams_messages",
        "description": "Fetch recent Microsoft Teams messages.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_whatsapp_messages",
        "description": "Fetch recent WhatsApp messages.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_github_notifications",
        "description": "Fetch recent GitHub notifications (PRs, issues, mentions).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_linear_issues",
        "description": "Fetch open Linear issues assigned to the user.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_jira_issues",
        "description": "Fetch open Jira issues assigned to the user.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_notion_tasks",
        "description": "Fetch tasks or pages from Notion.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_daily_plan",
        "description": "Get a combined daily overview: calendar events, priority emails, and open tasks.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "send_email",
        "description": "Send an email via Gmail (falls back to Outlook if Gmail not connected).",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address."},
                "subject": {"type": "string", "description": "Email subject line."},
                "body": {"type": "string", "description": "Email body text."},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "create_task",
        "description": "Create a new task in Linear.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Task title."},
                "description": {"type": "string", "description": "Optional task description."},
            },
            "required": ["title"],
        },
    },
]


async def dispatch(name: str, inputs: Dict[str, Any], db: Session) -> Any:
    if name == "get_calendar_events":
        days = inputs.get("days", 1)
        gcal = GoogleCalendarConnector(db)
        ocal = OutlookCalendarConnector(db)
        gcal_events = await gcal.fetch(days=days)
        ocal_events = await ocal.fetch(days=days)
        return gcal_events + ocal_events

    elif name == "get_priority_emails":
        limit = inputs.get("limit", 10)
        gmail = GmailConnector(db)
        outlook = OutlookMailConnector(db)
        gmail_emails = await gmail.fetch(max_results=limit)
        outlook_emails = await outlook.fetch(top=limit)
        all_emails = gmail_emails + outlook_emails
        scorer = EmailScorer(db)
        scored = sorted(all_emails, key=lambda e: scorer.score(e), reverse=True)
        return scored[:limit]

    elif name == "get_slack_messages":
        connector = SlackConnector(db)
        return await connector.fetch()

    elif name == "get_teams_messages":
        connector = TeamsConnector(db)
        return await connector.fetch()

    elif name == "get_whatsapp_messages":
        connector = WhatsAppConnector(db)
        return await connector.fetch()

    elif name == "get_github_notifications":
        connector = GitHubConnector(db)
        return await connector.fetch()

    elif name == "get_linear_issues":
        connector = LinearConnector(db)
        return await connector.fetch()

    elif name == "get_jira_issues":
        connector = JiraConnector(db)
        return await connector.fetch()

    elif name == "get_notion_tasks":
        connector = NotionConnector(db)
        return await connector.fetch()

    elif name == "get_daily_plan":
        gcal = GoogleCalendarConnector(db)
        ocal = OutlookCalendarConnector(db)
        gmail = GmailConnector(db)
        outlook = OutlookMailConnector(db)
        linear = LinearConnector(db)
        jira = JiraConnector(db)

        gcal_events = await gcal.fetch(days=1)
        ocal_events = await ocal.fetch(days=1)
        gmail_emails = await gmail.fetch(max_results=10)
        outlook_emails = await outlook.fetch(top=10)
        linear_issues = await linear.fetch()
        jira_issues = await jira.fetch()

        scorer = EmailScorer(db)
        all_emails = gmail_emails + outlook_emails
        priority_emails = sorted(all_emails, key=lambda e: scorer.score(e), reverse=True)[:5]

        return {
            "calendar": gcal_events + ocal_events,
            "priority_emails": priority_emails,
            "tasks": linear_issues + jira_issues,
        }

    elif name == "send_email":
        to = inputs.get("to", "")
        subject = inputs.get("subject", "")
        body = inputs.get("body", "")
        gmail = GmailConnector(db)
        sent = await gmail.send(to=to, subject=subject, body=body)
        if sent:
            return {"sent": True, "via": "gmail", "to": to, "subject": subject}
        outlook = OutlookMailConnector(db)
        sent = await outlook.send(to=to, subject=subject, body=body)
        if sent:
            return {"sent": True, "via": "outlook", "to": to, "subject": subject}
        return {"sent": False, "error": "No email connector available or send failed"}

    elif name == "create_task":
        import httpx
        import os
        title = inputs.get("title", "")
        description = inputs.get("description", "")
        linear = LinearConnector(db)
        tok = linear.access()
        if not tok:
            return {"error": "Linear not connected"}
        # Get team ID first
        team_query = """
        query {
          teams {
            nodes { id name }
          }
        }
        """
        async with httpx.AsyncClient(timeout=15) as c:
            tr = await c.post(
                "https://api.linear.app/graphql",
                json={"query": team_query},
                headers={"Authorization": tok, "Content-Type": "application/json"},
            )
        if tr.status_code != 200:
            return {"error": "Could not fetch Linear teams"}
        teams = tr.json().get("data", {}).get("teams", {}).get("nodes", [])
        if not teams:
            return {"error": "No Linear teams found"}
        team_id = teams[0]["id"]
        mutation = """
        mutation IssueCreate($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue { id identifier title url }
          }
        }
        """
        variables = {
            "input": {
                "teamId": team_id,
                "title": title,
                "description": description,
            }
        }
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                "https://api.linear.app/graphql",
                json={"query": mutation, "variables": variables},
                headers={"Authorization": tok, "Content-Type": "application/json"},
            )
        if r.status_code != 200:
            return {"error": "Linear issue creation failed"}
        data = r.json().get("data", {}).get("issueCreate", {})
        if data.get("success"):
            issue = data.get("issue", {})
            return {"created": True, "id": issue.get("identifier"), "title": title, "url": issue.get("url")}
        return {"error": "Linear issue creation returned success=false"}

    else:
        return {"error": f"unknown tool {name}"}
