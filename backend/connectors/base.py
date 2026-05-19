from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from crypto import decrypt
from models import OAuthToken


class Connector(ABC):
    provider: str = ""

    def __init__(self, db: Session, user_id: Optional[int] = None):
        self.db = db
        self.user_id = user_id

    def token(self) -> Optional[OAuthToken]:
        q = self.db.query(OAuthToken).filter_by(provider=self.provider)
        if self.user_id is not None:
            q = q.filter_by(user_id=self.user_id)
        return q.first()

    def access(self) -> Optional[str]:
        t = self.token()
        return decrypt(t.access_token) if t else None

    def refresh(self) -> Optional[str]:
        t = self.token()
        return decrypt(t.refresh_token) if (t and t.refresh_token) else None

    @abstractmethod
    async def fetch(self, **kwargs) -> List[Dict[str, Any]]:
        ...
