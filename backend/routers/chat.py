import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ai.claude_client import JarvisClaude
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
        client = JarvisClaude(db, current_user.id)
        reply = await client.respond(payload.message)
        return {"reply": reply}
    except Exception:
        logger.exception("chat error")
        raise HTTPException(status_code=500, detail="Internal error. Try again.")
