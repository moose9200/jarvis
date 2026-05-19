from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import traceback

from database import get_db
from models import User
from routers.users import get_current_user
from ai.claude_client import JarvisClaude

router = APIRouter()


class ChatIn(BaseModel):
    message: str


@router.post("/chat")
async def chat(payload: ChatIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        client = JarvisClaude(db, current_user.id)
        reply = await client.respond(payload.message)
        return {"reply": reply}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
