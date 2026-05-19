import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ai.exceptions import NoAPIKeyError, TokenBudgetExceededError
from ai.jarvis_ai import JarvisAI
from ai.persona import PERSONALITY_INJECTIONS, DEFAULT_PERSONALITY
from database import get_db
from models import User
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


@router.post("/chat")
async def chat(
    payload: ChatIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        client = JarvisAI(db, current_user.id)
        out = await client.respond(payload.message)
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


@router.get("/chat/quick-actions")
def quick_actions(current_user: User = Depends(get_current_user)):
    """Static quick-action chips. Frontend renders these as a row above the input."""
    return {"actions": QUICK_ACTIONS}


@router.get("/chat/personalities")
def personalities(current_user: User = Depends(get_current_user)):
    """All available personality modes + their style descriptors."""
    return {
        "default": DEFAULT_PERSONALITY,
        "modes": [
            {"id": k, "label": k.replace("_", " ").title(), "style": v[:200]}
            for k, v in PERSONALITY_INJECTIONS.items()
        ],
    }
