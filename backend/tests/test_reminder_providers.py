"""Tests de proveedores de recordatorios (modo mock)."""

import pytest

from app.core.config import Settings
from app.integrations.reminders.base import ReminderPayload
from app.integrations.reminders.email_adapter import EmailReminderProvider, message_to_html
from app.integrations.reminders.whatsapp_adapter import WhatsAppReminderProvider, normalize_whatsapp_phone


@pytest.fixture()
def mock_settings():
    return Settings(
        email_provider="mock",
        whatsapp_provider="mock",
        app_name="AppMedica Test",
    )


@pytest.mark.asyncio
async def test_email_mock_send(mock_settings):
    provider = EmailReminderProvider(mock_settings)
    ok = await provider.send(
        ReminderPayload(
            patient_name="Juan Pérez",
            message="Recordatorio de turno",
            email="juan@test.com",
            subject="Test",
        ),
    )
    assert ok.ok is True


@pytest.mark.asyncio
async def test_whatsapp_mock_send(mock_settings):
    provider = WhatsAppReminderProvider(mock_settings)
    ok = await provider.send(
        ReminderPayload(
            patient_name="Juan Pérez",
            message="Hola Juan",
            phone="2615551234",
        ),
    )
    assert ok.ok is True


def test_normalize_phone_argentina():
    assert normalize_whatsapp_phone("261 555-1234").startswith("54")


def test_reset_email_html_makes_url_clickable_and_escapes():
    url = "https://daminatoweb.com/reset-password?token=abc_123"
    html_body = message_to_html(f"Hola <script>\n\n{url}\n")
    assert "<script>" not in html_body
    assert "&lt;script&gt;" in html_body
    assert f'<a href="{url}">{url}</a>' in html_body
