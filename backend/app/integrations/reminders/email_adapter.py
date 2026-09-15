import html
import logging
import re
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from app.core.config import Settings, get_settings
from app.integrations.reminders.base import ReminderPayload, ReminderProvider, ReminderSendResult

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"(https?://[^\s<]+)")


def message_to_html(plain: str) -> str:
    """Convierte el cuerpo de texto a HTML seguro, con enlaces clicables."""
    parts: list[str] = []
    for line in plain.splitlines():
        if not line.strip():
            parts.append("<br/>")
            continue
        escaped = html.escape(line)
        linked = _URL_RE.sub(r'<a href="\1">\1</a>', escaped)
        parts.append(f"<p>{linked}</p>")
    return (
        "<html><body style='font-family:Arial,sans-serif;line-height:1.5;color:#222'>"
        + "".join(parts)
        + "</body></html>"
    )


class EmailReminderProvider(ReminderProvider):
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def send(self, payload: ReminderPayload) -> ReminderSendResult:
        if not payload.email:
            logger.warning("Email reminder skipped: missing recipient")
            return ReminderSendResult.failure(
                retryable=False,
                error_code="missing_contact",
            )
        try:
            ok = self.send_sync(payload)
        except Exception as exc:
            return ReminderSendResult.failure(
                retryable=True,
                error_code="email_error",
                error_message=type(exc).__name__,
            )
        if ok:
            return ReminderSendResult.success()
        return ReminderSendResult.failure(retryable=True, error_code="email_not_sent")

    def send_sync(self, payload: ReminderPayload) -> bool:
        """Envío síncrono (forgot-password, scripts). Evita asyncio.run en workers de uvicorn."""
        if not payload.email:
            logger.warning("Email reminder skipped: missing recipient")
            return False

        provider = (self.settings.email_provider or "mock").lower()
        if provider == "mock":
            logger.info("[MOCK EMAIL] send ok")
            return True

        if provider == "disabled":
            raise ValueError("EMAIL_PROVIDER=disabled: el envío de correo está desactivado")

        if provider != "smtp":
            raise ValueError(f"Proveedor de email no soportado: {provider}")

        if not self.settings.smtp_host:
            raise ValueError("SMTP no configurado (SMTP_HOST vacío)")
        if not (self.settings.smtp_user and self.settings.smtp_password):
            raise ValueError("SMTP incompleto: faltan SMTP_USER o SMTP_PASSWORD")

        self._send_smtp(payload)
        return True

    def verify_connection(self) -> None:
        """Login SMTP sin enviar (diagnóstico / setup de producción)."""
        provider = (self.settings.email_provider or "mock").lower()
        if provider != "smtp":
            raise ValueError(f"verify_connection solo aplica a smtp (actual: {provider})")
        self._with_smtp_session(lambda server: None)

    def _send_smtp(self, payload: ReminderPayload) -> None:
        subject = payload.subject or f"{self.settings.app_name} — Recordatorio"
        from_addr = self.settings.smtp_from_email or self.settings.smtp_user
        to_addr = payload.email
        assert to_addr is not None

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((self.settings.app_name, from_addr))
        msg["To"] = to_addr
        msg["Reply-To"] = from_addr
        plain = payload.message
        msg.attach(MIMEText(plain, "plain", "utf-8"))
        msg.attach(MIMEText(message_to_html(plain), "html", "utf-8"))

        def _do_send(server: smtplib.SMTP) -> None:
            server.sendmail(from_addr, [to_addr], msg.as_string())

        self._with_smtp_session(_do_send)
        logger.info("Email enviado a %s (asunto=%s)", to_addr, subject)

    def _smtp_attempts(self) -> list[tuple[str, int, bool]]:
        """Lista (host, port, use_ssl) a probar, en orden."""
        host = self.settings.smtp_host
        port = int(self.settings.smtp_port or 587)
        prefer_ssl = bool(getattr(self.settings, "smtp_use_ssl", False)) or port == 465

        attempts: list[tuple[str, int, bool]] = []
        if prefer_ssl:
            attempts.append((host, port if port == 465 else 465, True))
            attempts.append((host, 587, False))
        else:
            attempts.append((host, port, False))
            if port != 465:
                attempts.append((host, 465, True))

        # dedupe
        seen: set[tuple[str, int, bool]] = set()
        unique: list[tuple[str, int, bool]] = []
        for item in attempts:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        return unique

    def _with_smtp_session(self, action) -> None:
        errors: list[str] = []
        for host, port, use_ssl in self._smtp_attempts():
            try:
                if use_ssl:
                    context = ssl.create_default_context()
                    with smtplib.SMTP_SSL(host, port, timeout=30, context=context) as server:
                        server.ehlo()
                        server.login(self.settings.smtp_user, self.settings.smtp_password)
                        action(server)
                else:
                    with smtplib.SMTP(host, port, timeout=30) as server:
                        server.ehlo()
                        if self.settings.smtp_use_tls:
                            context = ssl.create_default_context()
                            server.starttls(context=context)
                            server.ehlo()
                        server.login(self.settings.smtp_user, self.settings.smtp_password)
                        action(server)
                logger.info("SMTP OK via %s:%s ssl=%s", host, port, use_ssl)
                return
            except Exception as exc:
                msg = f"{host}:{port} ssl={use_ssl} -> {type(exc).__name__}: {exc}"
                errors.append(msg)
                logger.warning("SMTP intento fallido: %s", msg)

        raise RuntimeError(
            "No se pudo conectar/enviar por SMTP. Intentos: " + " | ".join(errors)
        )
