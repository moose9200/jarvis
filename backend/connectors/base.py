from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from models import OAuthToken


class Connector(ABC):
    provider: str = ""

    def __init__(self, db: Session):
        self.db = db

    def token(self) -> Optional[OAuthToken]:
        return self.db.query(OAuthToken).filter_by(provider=self.provider).first()

    def access(self) -> Optional[str]:
        t = self.token()
        return t.access_token if t else None

    @abstractmethod
    async def fetch(self, **kwargs) -> List[Dict[str, Any]]:
        ...
