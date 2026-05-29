import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ai.exceptions import NoAPIKeyError, TokenBudgetExceededError
from ai.jarvis_ai import JarvisAI
from ai.persona import DEFAULT_PERSONALITY, list_skills
from database import get_db
from models import User
from rate_limit import limiter
from routers.users import get_current_user

logger = logging.getLogger("jarvis.chat")
router = APIRouter()


# Default quick-action prompts shown as chips above the chat input.
# These are static; future iteration could personalize per integration set.
QUICK_ACTIONS = [
    {"id": "day_plan",         "label": "What's my day?",
     "prompt": "Give me a complete briefing for today: meetings, priority emails, and top 3 tasks I should focus on."},
    {"id": "priority_emails",  "label": "Priority emails",
     "prompt": "What are my most important emails right now that need action?"},
    {"id": "draft_replies",    "label": "Draft top replies",
     "prompt": "Draft replies to my top 3 priority emails. Show each draft for approval."},
    {"id": "blockers",         "label": "What's blocking me?",
     "prompt": "Look at my tasks and tell me what's overdue or blocked and what I should do about it."},
    {"id": "week_summary",     "label": "Week summary",
     "prompt": "Summarize what happened this week: emails, tasks completed, meetings, Shopify performance."},
    {"id": "meeting_prep",     "label": "Next meeting prep",
     "prompt": "Brief me for my next meeting. Pull attendee context, related emails, and any relevant tasks."},
    {"id": "shopify_today",    "label": "Shopify today",
     "prompt": "What's my Shopify revenue today vs yesterday? Top selling product? Any orders needing attention?"},
    {"id": "customer_issues",  "label": "Customer issues",
     "prompt": "What are the top customer support issues this week? Any spikes or patterns I should know about?"},
    {"id": "decide_today",     "label": "What to decide?",
     "prompt": "What things need my decision today? PRs, orders, tickets — anything waiting for me to act."},
    {"id": "delegate",         "label": "What to delegate?",
     "prompt": "Look at my task list. What can be delegated? Draft delegation messages for the top 3 candidates."},
]


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    file_ids: list[int] = Field(default_factory=list, max_length=10)


@router.post("/chat")
@limiter.limit("30/minute")
async def chat(
    request: Request,
    payload: ChatIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        client = JarvisAI(db, current_user.id)
        out = await client.respond(payload.message, file_ids=payload.file_ids)
        return {"reply": out["text"], "usage": out["usage"]}
    except NoAPIKeyError as e:
        raise HTTPException(
            status_code=402,
            detail=f"No {e.provider} API key configured. Add yours in Settings → AI Keys.",
        )
    except TokenBudgetExceededError as e:
        raise HTTPException(
            status_code=429,
            detail=f"Daily token budget hit ({e.used}/{e.budget}). Raise it in Settings.",
        )
    except Exception:
        logger.exception("chat error")
        raise HTTPException(status_code=500, detail="Internal error. Try again.")


@router.post("/chat/stream")
@limiter.limit("20/minute")
async def chat_stream(
    request: Request,
    payload: ChatIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SSE streaming chat. Emits events:
        data: {"type":"token","text":"..."}\n\n
        data: {"type":"done","usage":{...}}\n\n
        data: [DONE]\n\n

    NOTE: tool use is disabled in streaming mode (v1). For full tool support
    fall back to POST /api/chat.
    """
    try:
        client = JarvisAI(db, current_user.id)
    except NoAPIKeyError as e:
        raise HTTPException(
            status_code=402,
            detail=f"No {e.provider} API key configured. Add yours in Settings → AI Keys.",
        )

    async def generate():
        try:
            async for chunk in client.stream(payload.message, file_ids=payload.file_ids):
                yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception:
            logger.exception("stream generator error")
            yield 'data: {"type":"error","text":"Internal error."}\n\n'
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",   # disable proxy buffering (nginx)
            "Cache-Control": "no-cache",
        },
    )


@router.get("/chat/quick-actions")
def quick_actions(current_user: User = Depends(get_current_user)):
    """Static quick-action chips. Frontend renders these as a row above the input."""
    return {"actions": QUICK_ACTIONS}


# Per-panel "Suggestions" prompts (Step 11). Frontend renders these as a
# drawer under a ❓ button on each panel. Polished, ready-to-use prompts.
PANEL_SUGGESTIONS = {
    "email": [
        "Summarize all unread emails in one paragraph.",
        "Which emails need a reply today? List sender + why it matters.",
        "Draft replies to my top 3 priority emails. Show each for approval.",
        "Flag any emails I've been ignoring too long.",
        "Anything in my inbox that could be a legal or financial risk?",
    ],
    "calendar": [
        "Brief me for my next meeting — attendees, context, what to know.",
        "What's eating most of my time this week? Any patterns?",
        "I need 2 hours of focused work today — best slot?",
        "Which meetings this week could be an email instead?",
        "Any conflicts or double bookings I should know about?",
    ],
    "tasks": [
        "What's my single most important task today and why?",
        "Which tasks are overdue? What should I do about each?",
        "Break the top task into smaller steps I can action today.",
        "What on my task list can I delegate? Draft delegation messages.",
        "What tasks haven't moved in a week? Should I drop them?",
    ],
    "projects": [
        "Status update on every active project — one line each.",
        "Which project is most behind schedule? What's blocking it?",
        "Which project should I personally focus on this week?",
        "Anything that needs a decision from me right now?",
        "End-of-week summary: what shipped, what slipped.",
    ],
    "shopify": [
        "How is my store performing this week vs last week?",
        "Top 3 selling products this week and what's driving them?",
        "Which products should I restock urgently?",
        "Best promotion + discount combo to maximize revenue?",
        "Customers who spent over $500 but haven't ordered in 30 days.",
    ],
    "freshdesk": [
        "What are my customers most frustrated about this week?",
        "Tickets that have waited too long? Who's affected?",
        "Draft a reply to my most urgent open ticket.",
        "What's my team's support response time looking like?",
        "Any recurring complaints I should fix at the product level?",
    ],
    "home": [
        "Good morning — give me my complete daily brief.",
        "What are the 3 most important things I need to do today?",
        "Anything on fire right now that needs my immediate attention?",
        "What decisions am I avoiding that I should make today?",
        "End-of-day review — what got done, what's still open, tomorrow's priority?",
    ],
}


@router.get("/chat/suggestions/{panel}")
def panel_suggestions(panel: str, current_user: User = Depends(get_current_user)):
    """Pre-built prompts for a given dashboard panel. Returns 404 if the
    panel is unknown so the frontend can hide the ❓ button gracefully."""
    if panel not in PANEL_SUGGESTIONS:
        raise HTTPException(404, f"No suggestions for panel: {panel}")
    return {"panel": panel, "prompts": PANEL_SUGGESTIONS[panel]}


@router.get("/chat/suggestions")
def all_panel_suggestions(current_user: User = Depends(get_current_user)):
    """Bulk fetch — frontend can prefetch on app load."""
    return {"panels": PANEL_SUGGESTIONS}


@router.get("/chat/personalities")
def personalities(current_user: User = Depends(get_current_user)):
    """All available skill modes + their style descriptors.

    Returns 11 entries: `all_purpose` (default) plus the 10 popular skills:
    coder, designer, writer, marketer, founder, researcher, analyst, coach,
    devils_advocate, creative. Each entry has id + label + one-line tag
    + first 240 chars of the system-prompt injection (for tooltips)."""
    return {
        "default": DEFAULT_PERSONALITY,
        "modes": list_skills(),
    }
