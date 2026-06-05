import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import Settings, get_settings
from app.integrations.reminders.base import ReminderPayload, ReminderProvider

logger = logging.getLogger(__name__)


class EmailReminderProvider(ReminderProvider):
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def send(self, payload: ReminderPayload) -> bool:
        if not payload.email:
            logger.warning("Email reminder skipped: sin dirección de email")
            return False

        provider = (self.settings.email_provider or "mock").lower()
        if provider == "mock":
            logger.info(
                "[MOCK EMAIL] Para: %s | Asunto: %s | %s",
                payload.email,
                payload.subject or "AppMedica",
                payload.message[:200],
            )
            return True

        if provider != "smtp":
            raise ValueError(f"Proveedor de email no soportado: {provider}")

        if not self.settings.smtp_host:
            raise ValueError("SMTP no configurado (SMTP_HOST vacío)")

        await asyncio.to_thread(self._send_smtp, payload)
        return True

    def _send_smtp(self, payload: ReminderPayload) -> None:
        subject = payload.subject or f"{self.settings.app_name} — Recordatorio"
        from_addr = self.settings.smtp_from_email or self.settings.smtp_user

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = payload.email
        msg.attach(MIMEText(payload.message, "plain", "utf-8"))

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=30) as server:
            if self.settings.smtp_use_tls:
                server.starttls()
            if self.settings.smtp_user and self.settings.smtp_password:
                server.login(self.settings.smtp_user, self.settings.smtp_password)
            server.sendmail(from_addr, [payload.email], msg.as_string())

        logger.info("Email enviado a %s", payload.email)
