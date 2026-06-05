import logging
import re

import httpx

from app.core.config import Settings, get_settings
from app.integrations.reminders.base import ReminderPayload, ReminderProvider

logger = logging.getLogger(__name__)


def normalize_whatsapp_phone(phone: str) -> str:
    """E.164 sin '+' para APIs que lo piden así."""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("0"):
        digits = digits[1:]
    if not digits.startswith("54") and len(digits) <= 10:
        digits = "54" + digits
    return digits


class WhatsAppReminderProvider(ReminderProvider):
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def send(self, payload: ReminderPayload) -> bool:
        if not payload.phone:
            logger.warning("WhatsApp reminder skipped: sin teléfono")
            return False

        provider = (self.settings.whatsapp_provider or "mock").lower()
        if provider == "mock":
            logger.info(
                "[MOCK WHATSAPP] Para: %s | %s",
                payload.phone,
                payload.message[:200],
            )
            return True

        phone = normalize_whatsapp_phone(payload.phone)
        if provider == "twilio":
            return await self._send_twilio(phone, payload.message)
        if provider == "meta":
            return await self._send_meta(phone, payload.message)
        raise ValueError(f"Proveedor WhatsApp no soportado: {provider}")

    async def _send_twilio(self, phone: str, body: str) -> bool:
        sid = self.settings.twilio_account_sid
        token = self.settings.twilio_auth_token
        from_num = self.settings.twilio_whatsapp_from
        if not all([sid, token, from_num]):
            raise ValueError("Twilio incompleto: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM")

        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        data = {
            "From": from_num if from_num.startswith("whatsapp:") else f"whatsapp:{from_num}",
            "To": f"whatsapp:+{phone}",
            "Body": body,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, data=data, auth=(sid, token))
            if not response.is_success:
                logger.error("Twilio error %s: %s", response.status_code, response.text)
                return False
        logger.info("WhatsApp Twilio enviado a +%s", phone)
        return True

    async def _send_meta(self, phone: str, body: str) -> bool:
        token = self.settings.meta_whatsapp_token
        phone_id = self.settings.meta_whatsapp_phone_number_id
        if not token or not phone_id:
            raise ValueError("Meta WhatsApp incompleto: META_WHATSAPP_TOKEN, META_WHATSAPP_PHONE_NUMBER_ID")

        url = f"https://graph.facebook.com/v21.0/{phone_id}/messages"
        headers = {"Authorization": f"Bearer {token}"}
        json_body = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": body},
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=json_body)
            if not response.is_success:
                logger.error("Meta WhatsApp error %s: %s", response.status_code, response.text)
                return False
        logger.info("WhatsApp Meta enviado a %s", phone)
        return True
