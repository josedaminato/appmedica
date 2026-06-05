"""Tests de solapamiento de turnos."""

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import AppException
from app.models.enums import AppointmentStatus
from app.services.appointment_scheduling import assert_no_overlap


def test_assert_no_overlap_raises():
    patient = MagicMock()
    patient.last_name = "Perez"
    patient.first_name = "Juan"

    other = MagicMock()
    other.patient = patient
    other.start_at = datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)
    other.end_at = datetime(2026, 6, 2, 10, 30, tzinfo=timezone.utc)

    repo = MagicMock()
    repo.find_overlapping.return_value = [other]

    start = datetime(2026, 6, 2, 10, 15, tzinfo=timezone.utc)
    end = datetime(2026, 6, 2, 10, 45, tzinfo=timezone.utc)

    with pytest.raises(AppException) as exc:
        assert_no_overlap(
            repo,
            uuid4(),
            professional_id=uuid4(),
            start_at=start,
            end_at=end,
        )
    assert exc.value.status_code == 409
    assert "superpone" in exc.value.detail["message"].lower()  # type: ignore[index]


def test_assert_no_overlap_skips_without_professional():
    repo = MagicMock()
    assert_no_overlap(
        repo,
        uuid4(),
        professional_id=None,
        start_at=datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 6, 2, 11, 0, tzinfo=timezone.utc),
    )
    repo.find_overlapping.assert_not_called()
