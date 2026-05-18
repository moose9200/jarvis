import os
import httpx
from .base import Connector


class WhatsAppConnector(Connector):
    provider = "whatsapp"

    async def fetch(self, **_):
        tok = self.access()
        phone_id = os.getenv("WHATSAPP_PHONE_ID", "")
        if not tok or not phone_id:
            return []
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                f"https://graph.facebook.com/v18.0/{phone_id}",
                headers={"Authorization": f"Bearer {tok}"},
            )
        if r.status_code != 200:
            return []
        j = r.json()
        return [{
            "id": j.get("id", "wa-status"),
            "from": j.get("display_phone_number", "WhatsApp"),
            "text": "WhatsApp Cloud webhook configured. Inbound messages will appear here.",
            "channel": "whatsapp",
            "received": "",
            "source": "whatsapp",
        }]
