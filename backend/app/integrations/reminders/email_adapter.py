from app.integrations.reminders.base import ReminderPayload, ReminderProvider


class EmailReminderProvider(ReminderProvider):
    async def send(self, payload: ReminderPayload) -> bool:
        # Integración futura con proveedor de email (SendGrid, Resend, etc.)
        raise NotImplementedError("Email integration not configured")
