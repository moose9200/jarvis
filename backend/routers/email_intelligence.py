from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from intelligence.history_collector import HistoryCollector
from intelligence.email_scorer import EmailScorer
from connectors.gmail import GmailConnector
from connectors.outlook_mail import OutlookMailConnector

router = APIRouter()


@router.post("/email/collect")
async def collect(db: Session = Depends(get_db)):
    added = await HistoryCollector(db).collect()
    return {"added": added}


@router.get("/email/priority")
async def priority(limit: int = 15, db: Session = Depends(get_db)):
    all_mail = []
    all_mail += await GmailConnector(db).fetch(max_results=30)
    all_mail += await OutlookMailConnector(db).fetch(top=30)
    scorer = EmailScorer(db)
    for m in all_mail:
        m["priority"] = scorer.score(m)
    all_mail.sort(key=lambda x: x["priority"], reverse=True)
    return {"emails": all_mail[:limit]}
