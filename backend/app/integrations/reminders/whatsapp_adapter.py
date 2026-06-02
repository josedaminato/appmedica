from app.integrations.reminders.base import ReminderPayload, ReminderProvider


class WhatsAppReminderProvider(ReminderProvider):
    async def send(self, payload: ReminderPayload) -> bool:
        # Integración futura con WhatsApp Business API
        raise NotImplementedError("WhatsApp integration not configured")
