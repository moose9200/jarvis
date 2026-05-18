from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_db
from ai.claude_client import JarvisClaude

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


class ChatIn(BaseModel):
    message: str


@router.post("/chat")
@limiter.limit("30/minute")
async def chat(request: Request, payload: ChatIn, db: Session = Depends(get_db)):
    client = JarvisClaude(db)
    reply = await client.respond(payload.message)
    return {"reply": reply}
