from app.core.config import Settings, get_settings
from app.integrations.reminders.base import ReminderProvider
from app.integrations.reminders.email_adapter import EmailReminderProvider
from app.integrations.reminders.whatsapp_adapter import WhatsAppReminderProvider


def get_email_provider(settings: Settings | None = None) -> ReminderProvider:
    return EmailReminderProvider(settings or get_settings())


def get_whatsapp_provider(settings: Settings | None = None) -> ReminderProvider:
    return WhatsAppReminderProvider(settings or get_settings())
