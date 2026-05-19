import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ai.exceptions import NoAPIKeyError, TokenBudgetExceededError
from ai.jarvis_ai import JarvisAI
from database import get_db
from models import User
from routers.users import get_current_user

logger = logging.getLogger("jarvis.chat")
router = APIRouter()


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
