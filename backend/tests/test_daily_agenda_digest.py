"""Tests del resumen diario de agenda por email."""

from datetime import date, datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from app.models.enums import AppointmentStatus
from app.services.daily_agenda_digest_service import (
    build_agenda_digest_message,
    digest_send_window_open,
)


def test_digest_send_window_open():
    tz = ZoneInfo("America/Argentina/Buenos_Aires")
    inside = datetime(2026, 6, 1, 21, 10, tzinfo=tz)
    assert digest_send_window_open(inside, hour=21, minute=0) is True

    before = datetime(2026, 6, 1, 20, 50, tzinfo=tz)
    assert digest_send_window_open(before, hour=21, minute=0) is False

    after = datetime(2026, 6, 1, 21, 45, tzinfo=tz)
    assert digest_send_window_open(after, hour=21, minute=0, window_minutes=30) is False


def test_build_agenda_digest_message_empty():
    body = build_agenda_digest_message(
        recipient_name="Dr. López",
        org_name="Consultorio Test",
        target_date=date(2026, 6, 2),
        appointments=[],
        app_url="https://app.example.com",
        for_owner=False,
        tz=ZoneInfo("America/Argentina/Buenos_Aires"),
    )
    assert "Dr. López" in body
    assert "No hay turnos" in body
    assert "agenda?date=2026-06-02" in body


def test_build_agenda_digest_message_with_appointments():
    patient = MagicMock()
    patient.first_name = "Juan"
    patient.last_name = "Pérez"
    patient.dni = "30123456"
    patient.phone = "2615551234"

    appt = MagicMock()
    appt.start_at = datetime(2026, 6, 2, 14, 30, tzinfo=timezone.utc)
    appt.status = AppointmentStatus.CONFIRMED
    appt.modality.value = "presencial"
    appt.attention_type.value = "private"
    appt.notes = None
    appt.patient = patient
    appt.professional = None

    body = build_agenda_digest_message(
        recipient_name="Dr. López",
        org_name="Consultorio Test",
        target_date=date(2026, 6, 2),
        appointments=[appt],
        app_url="https://app.example.com",
        for_owner=False,
        tz=ZoneInfo("America/Argentina/Buenos_Aires"),
    )
    assert "Pérez, Juan" in body
    assert "Confirmado" in body
    assert "Total: 1 turno" in body
