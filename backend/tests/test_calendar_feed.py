"""Tests del feed iCal."""

from datetime import date, datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from app.models.enums import AppointmentStatus, UserRole
from app.models.user import User
from app.services.calendar_feed_service import (
    CalendarFeedService,
    build_ics_calendar,
    ics_escape,
)


def test_ics_escape():
    assert ics_escape("a;b\nc,d") == "a\\;b\\nc\\,d"


def test_build_ics_calendar_contains_vevent():
    patient = MagicMock()
    patient.last_name = "Pérez"
    patient.first_name = "Juan"
    patient.dni = "30123456"
    patient.phone = "2615551234"

    appt = MagicMock()
    appt.id = uuid4()
    appt.start_at = datetime(2026, 6, 2, 14, 30, tzinfo=timezone.utc)
    appt.end_at = datetime(2026, 6, 2, 15, 0, tzinfo=timezone.utc)
    appt.status = AppointmentStatus.CONFIRMED
    appt.notes = None
    appt.patient = patient
    appt.professional = None

    body = build_ics_calendar(
        calendar_name="Test",
        appointments=[appt],
        tz=ZoneInfo("America/Argentina/Buenos_Aires"),
        app_url="https://app.example.com",
    )
    assert "BEGIN:VCALENDAR" in body
    assert "BEGIN:VEVENT" in body
    assert "Juan" in body
    assert "Turno" in body
    assert "30123456" not in body
    assert "2615551234" not in body
    assert f"appointment-{appt.id}@appmedica" in body


def test_scope_label_professional():
    user = User(
        id=uuid4(),
        organization_id=uuid4(),
        email="p@test.com",
        password_hash="x",
        full_name="Dr. Test",
        role=UserRole.PROFESSIONAL,
        is_active=True,
    )
    svc = CalendarFeedService(MagicMock())
    assert svc._scope_label(user) == "Solo tus turnos"
