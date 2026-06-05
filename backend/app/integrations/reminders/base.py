from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ReminderPayload:
    patient_name: str
    message: str
    phone: str | None = None
    email: str | None = None
    subject: str | None = None


class ReminderProvider(ABC):
    @abstractmethod
    async def send(self, payload: ReminderPayload) -> bool:
        """Envía un recordatorio por el canal configurado (mock, SMTP, Twilio, Meta)."""
