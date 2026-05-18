from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from ai.claude_client import JarvisClaude

router = APIRouter()

class ChatIn(BaseModel):
    message: str

@router.post("/chat")
async def chat(payload: ChatIn, db: Session = Depends(get_db)):
    client = JarvisClaude(db)
    reply = await client.respond(payload.message)
    return {"reply": reply}
