"""Tests de ReminderService (alcance por organización)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from zoneinfo import ZoneInfo

from app.core.timezone import org_timezone
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus
from app.models.organization import Organization
from app.models.patient import Patient
from app.services.reminder_service import ReminderService


@pytest.mark.asyncio
async def test_process_due_jobs_passes_organization_id_to_repository():
    org_id = uuid4()
    db = MagicMock()
    service = ReminderService(db)
    service.reminders = MagicMock()
    service.reminders.list_due.return_value = []

    await service.process_due_jobs(organization_id=org_id)

    service.reminders.list_due.assert_called_once()
    _, kwargs = service.reminders.list_due.call_args
    assert kwargs["organization_id"] == org_id
    assert isinstance(kwargs["before"], datetime)


@pytest.mark.asyncio
async def test_process_due_jobs_without_organization_processes_all():
    db = MagicMock()
    service = ReminderService(db)
    service.reminders = MagicMock()
    service.reminders.list_due.return_value = []

    await service.process_due_jobs()

    _, kwargs = service.reminders.list_due.call_args
    assert kwargs["organization_id"] is None


def test_reminder_message_uses_organization_timezone():
    """15:00 UTC = 12:00 en America/Argentina/Buenos_Aires (UTC-3)."""
    org = Organization(
        id=uuid4(),
        name="Consultorio Test",
        slug="consultorio-test",
        timezone="America/Argentina/Buenos_Aires",
    )
    tz = org_timezone(org)
    patient = Patient(
        id=uuid4(),
        organization_id=org.id,
        first_name="Juan",
        last_name="Perez",
        dni="30123456",
        is_active=True,
    )
    appt = Appointment(
        id=uuid4(),
        organization_id=org.id,
        patient_id=patient.id,
        professional_id=None,
        start_at=datetime(2026, 6, 2, 15, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 6, 2, 15, 30, tzinfo=timezone.utc),
        status=AppointmentStatus.CONFIRMED,
    )

    msg = ReminderService(MagicMock())._build_appointment_message(
        patient, appt, org.name, tz,
    )

    assert "12:00" in msg
    assert "02/06/2026" in msg
    assert "hora del consultorio" in msg
    assert "hora Argentina" not in msg
