from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ReminderPayload:
    patient_name: str
    message: str
    phone: str | None = None
    email: str | None = None
    subject: str | None = None


@dataclass
class ReminderSendResult:
    """Resultado del adapter. No implica exactly-once frente al proveedor."""

    ok: bool
    retryable: bool = False
    http_status: int | None = None
    retry_after_seconds: int | None = None
    error_code: str | None = None
    error_message: str | None = None

    def __bool__(self) -> bool:
        return self.ok

    @classmethod
    def success(cls) -> "ReminderSendResult":
        return cls(ok=True)

    @classmethod
    def failure(
        cls,
        *,
        retryable: bool,
        http_status: int | None = None,
        retry_after_seconds: int | None = None,
        error_code: str = "send_failed",
        error_message: str | None = None,
    ) -> "ReminderSendResult":
        return cls(
            ok=False,
            retryable=retryable,
            http_status=http_status,
            retry_after_seconds=retry_after_seconds,
            error_code=error_code,
            error_message=error_message,
        )


class ReminderProvider(ABC):
    @abstractmethod
    async def send(self, payload: ReminderPayload) -> ReminderSendResult:
        """Envía un recordatorio por el canal configurado (mock, SMTP, Twilio, Meta)."""
