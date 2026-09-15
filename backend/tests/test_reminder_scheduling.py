"""Política de scheduling: T−24, quiet hours 21–08, mínimo 30 minutos."""

from datetime import datetime, timedelta, timezone
from typing import Tuple
from unittest.mock import MagicMock, patch
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.core.timezone import (
    DEFAULT_ORG_TIMEZONE,
    clamp_to_send_window,
    compute_reminder_send_at,
    has_min_reminder_lead,
    is_in_quiet_hours,
)
from app.integrations.reminders.base import ReminderSendResult
from app.models.enums import AppointmentStatus, ReminderChannel, ReminderStatus
from app.schemas.appointment import AppointmentUpdate
from app.services.appointment_service import AppointmentService
from app.services.reminder_service import ReminderService, _PreparedSend

AR = ZoneInfo(DEFAULT_ORG_TIMEZONE)
CL = ZoneInfo("America/Santiago")


def _art(year: int, month: int, day: int, hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=AR)


def _send(*, start: datetime, now: datetime, tz=AR, hours_before: int = 24) -> datetime | None:
    return compute_reminder_send_at(
        start_at=start,
        now=now,
        tz=tz,
        hours_before=hours_before,
    )


def test_t_minus_24_inside_window_unchanged():
    start = _art(2026, 6, 10, 15, 0)
    now = _art(2026, 6, 8, 12, 0)
    send_at = _send(start=start, now=now)
    assert send_at == _art(2026, 6, 9, 15, 0).astimezone(timezone.utc)


def test_case1_night_before_11am_clamps_to_0800():
    """Turno 11:00, creado 23:00 del día anterior → 08:00 del día del turno."""
    start = _art(2026, 6, 10, 11, 0)
    now = _art(2026, 6, 9, 23, 0)
    send_at = _send(start=start, now=now)
    assert send_at == _art(2026, 6, 10, 8, 0).astimezone(timezone.utc)


def test_case2_same_day_two_hours_is_eligible():
    start = _art(2026, 6, 10, 18, 0)
    now = _art(2026, 6, 10, 16, 0)
    send_at = _send(start=start, now=now)
    assert send_at == now.astimezone(timezone.utc)


def test_case3_ninety_minutes_is_eligible():
    start = _art(2026, 6, 10, 20, 0)
    now = _art(2026, 6, 10, 18, 30)
    send_at = _send(start=start, now=now)
    assert send_at == now.astimezone(timezone.utc)


def test_case4_created_at_0630_for_0900_clamps_to_0800():
    start = _art(2026, 6, 10, 9, 0)
    now = _art(2026, 6, 10, 6, 30)
    send_at = _send(start=start, now=now)
    assert send_at == _art(2026, 6, 10, 8, 0).astimezone(timezone.utc)
    assert not (start - send_at < timedelta(minutes=30))


def test_case5_exactly_30_minutes_is_eligible():
    start = _art(2026, 6, 10, 9, 0)
    now = _art(2026, 6, 10, 8, 30)
    send_at = _send(start=start, now=now)
    assert send_at == now.astimezone(timezone.utc)


def test_case7_modified_at_0930_for_1000_is_eligible():
    start = _art(2026, 6, 10, 10, 0)
    now = _art(2026, 6, 10, 9, 30)
    assert _send(start=start, now=now) == now.astimezone(timezone.utc)


def test_case8_modified_at_0931_for_1000_is_not_eligible():
    start = _art(2026, 6, 10, 10, 0)
    now = _art(2026, 6, 10, 9, 31)
    assert _send(start=start, now=now) is None


def test_case9_0800_created_at_2330_does_not_break_quiet_hours():
    start = _art(2026, 6, 10, 8, 0)
    now = _art(2026, 6, 9, 23, 30)
    assert _send(start=start, now=now) is None


def test_case10_already_started_does_not_schedule():
    start = _art(2026, 6, 10, 10, 0)
    now = _art(2026, 6, 10, 10, 0)
    assert _send(start=start, now=now) is None
    assert _send(start=start, now=_art(2026, 6, 10, 10, 1)) is None


def test_quiet_hours_0700_appointment_sends_at_0800_day_before_shifted():
    """Turno 07:00 → T−24 = 07:00 → clamp 08:00 (23h antes)."""
    start = _art(2026, 6, 11, 7, 0)
    now = _art(2026, 6, 9, 12, 0)
    send_at = _send(start=start, now=now)
    assert send_at == _art(2026, 6, 10, 8, 0).astimezone(timezone.utc)


def test_turno_0800_t_minus_24_stays_0800():
    start = _art(2026, 6, 11, 8, 0)
    now = _art(2026, 6, 9, 12, 0)
    send_at = _send(start=start, now=now)
    assert send_at == _art(2026, 6, 10, 8, 0).astimezone(timezone.utc)


def test_turno_2200_clamps_t_minus_24_to_next_0800():
    start = _art(2026, 6, 11, 22, 0)
    now = _art(2026, 6, 9, 12, 0)
    send_at = _send(start=start, now=now)
    # T−24 = 10/6 22:00 → silencio → 11/6 08:00
    assert send_at == _art(2026, 6, 11, 8, 0).astimezone(timezone.utc)


def test_quiet_hours_boundaries():
    assert not is_in_quiet_hours(_art(2026, 6, 10, 21, 0, 0), AR)
    assert is_in_quiet_hours(_art(2026, 6, 10, 21, 0, 1), AR)
    assert not is_in_quiet_hours(_art(2026, 6, 10, 8, 0, 0), AR)
    assert is_in_quiet_hours(_art(2026, 6, 10, 7, 59, 59), AR)


def test_clamp_window_edges():
    tz = AR
    stay_205959 = _art(2026, 6, 10, 20, 59, 59)
    assert clamp_to_send_window(stay_205959, tz) == stay_205959.astimezone(timezone.utc)

    stay_2100 = _art(2026, 6, 10, 21, 0, 0)
    assert clamp_to_send_window(stay_2100, tz) == stay_2100.astimezone(timezone.utc)

    clamped_210001 = clamp_to_send_window(_art(2026, 6, 10, 21, 0, 1), tz)
    assert clamped_210001 == _art(2026, 6, 11, 8, 0, 0).astimezone(timezone.utc)

    clamped_075959 = clamp_to_send_window(_art(2026, 6, 10, 7, 59, 59), tz)
    assert clamped_075959 == _art(2026, 6, 10, 8, 0, 0).astimezone(timezone.utc)

    stay_0800 = _art(2026, 6, 10, 8, 0, 0)
    assert clamp_to_send_window(stay_0800, tz) == stay_0800.astimezone(timezone.utc)


def test_compute_send_at_none_when_clamp_equals_start():
    start = _art(2026, 6, 10, 8, 0, 0)
    now = _art(2026, 6, 9, 23, 30, 0)
    assert _send(start=start, now=now) is None


def test_compute_send_at_none_when_clamp_after_start():
    start = _art(2026, 6, 10, 7, 0, 0)
    now = _art(2026, 6, 10, 6, 30, 0)
    assert _send(start=start, now=now) is None


def test_clamp_uses_organization_timezone_not_argentina():
    # 23:00 Santiago en invierno (UTC-4) no es 23:00 ART.
    santiago_2300 = datetime(2026, 6, 10, 23, 0, tzinfo=CL)
    clamped = clamp_to_send_window(santiago_2300, CL)
    local = clamped.astimezone(CL)
    assert local.hour == 8
    assert local.date().isoformat() == "2026-06-11"


def _job_and_prepared(start: datetime) -> Tuple[MagicMock, _PreparedSend]:
    job = MagicMock()
    job.attempt_count = 0
    job.id = uuid4()
    job.appointment_id = uuid4()
    job.organization_id = uuid4()
    job.channel = ReminderChannel.EMAIL
    prepared = _PreparedSend(
        job_id=job.id,
        organization_id=job.organization_id,
        channel=ReminderChannel.EMAIL,
        appointment_start=start,
        patient_name="Pérez, Ana",
        message="x",
        phone=None,
        email="ana@test.com",
        subject="s",
        provider_name="smtp",
        tz=AR,
    )
    return job, prepared


def test_has_min_reminder_lead_boundaries():
    start = _art(2026, 6, 10, 10, 0)
    assert has_min_reminder_lead(start, _art(2026, 6, 10, 9, 30))
    assert not has_min_reminder_lead(start, _art(2026, 6, 10, 9, 30, 1))
    assert not has_min_reminder_lead(start, start)
    assert not has_min_reminder_lead(start, start + timedelta(seconds=1))


def test_retry_clamps_into_next_morning():
    service = ReminderService(MagicMock())
    start = _art(2026, 6, 11, 15, 0)
    job, prepared = _job_and_prepared(start)
    now = _art(2026, 6, 10, 20, 58)
    outcome = service._apply_send_result(
        job,
        prepared,
        ReminderSendResult.failure(retryable=True, error_code="http_503"),
        now,
    )
    assert outcome == "retried"
    assert job.next_attempt_at == _art(2026, 6, 11, 8, 0).astimezone(timezone.utc)
    assert job.status == ReminderStatus.SCHEDULED


def test_retry_after_start_still_skipped_after_quiet_hours_clamp():
    service = ReminderService(MagicMock())
    start = _art(2026, 6, 10, 21, 10)
    job, prepared = _job_and_prepared(start)
    now = _art(2026, 6, 10, 20, 58)
    outcome = service._apply_send_result(
        job,
        prepared,
        ReminderSendResult.failure(retryable=True, error_code="http_503"),
        now,
    )
    assert outcome == "skipped"
    assert job.status == ReminderStatus.SKIPPED
    assert job.error_code == "retry_after_start"


def test_retry_exactly_30_minutes_is_allowed():
    service = ReminderService(MagicMock())
    job, prepared = _job_and_prepared(_art(2026, 6, 10, 10, 35))
    outcome = service._apply_send_result(
        job,
        prepared,
        ReminderSendResult.failure(retryable=True, error_code="http_503"),
        _art(2026, 6, 10, 10, 0),
    )
    assert outcome == "retried"
    assert job.status == ReminderStatus.SCHEDULED
    assert job.next_attempt_at == _art(2026, 6, 10, 10, 5).astimezone(timezone.utc)


def test_retry_29_minutes_59_seconds_is_skipped():
    service = ReminderService(MagicMock())
    job, prepared = _job_and_prepared(_art(2026, 6, 10, 10, 34, 59))
    outcome = service._apply_send_result(
        job,
        prepared,
        ReminderSendResult.failure(retryable=True, error_code="http_503"),
        _art(2026, 6, 10, 10, 0),
    )
    assert outcome == "skipped"
    assert job.status == ReminderStatus.SKIPPED
    assert job.error_code == "retry_too_close_to_start"


def test_retry_quiet_hours_clamp_too_close_is_skipped():
    service = ReminderService(MagicMock())
    job, prepared = _job_and_prepared(_art(2026, 6, 11, 8, 20))
    outcome = service._apply_send_result(
        job,
        prepared,
        ReminderSendResult.failure(retryable=True, error_code="http_503"),
        _art(2026, 6, 10, 20, 58),
    )
    assert outcome == "skipped"
    assert job.status == ReminderStatus.SKIPPED
    assert job.error_code == "retry_too_close_to_start"


def test_retry_quiet_hours_clamp_with_enough_lead_stays_scheduled():
    service = ReminderService(MagicMock())
    job, prepared = _job_and_prepared(_art(2026, 6, 11, 9, 0))
    outcome = service._apply_send_result(
        job,
        prepared,
        ReminderSendResult.failure(retryable=True, error_code="http_503"),
        _art(2026, 6, 10, 20, 58),
    )
    assert outcome == "retried"
    assert job.status == ReminderStatus.SCHEDULED
    assert job.next_attempt_at == _art(2026, 6, 11, 8, 0).astimezone(timezone.utc)


def test_quiet_hours_defer_too_close_is_skipped():
    service = ReminderService(MagicMock())
    job, prepared = _job_and_prepared(_art(2026, 6, 10, 8, 20))
    outcome = service._apply_quiet_hours_defer(job, prepared, _art(2026, 6, 10, 7, 0))
    assert outcome == "skipped"
    assert job.status == ReminderStatus.SKIPPED
    assert job.error_code == "quiet_hours_too_close_to_start"


def test_quiet_hours_defer_with_enough_lead_stays_scheduled():
    service = ReminderService(MagicMock())
    job, prepared = _job_and_prepared(_art(2026, 6, 10, 9, 0))
    outcome = service._apply_quiet_hours_defer(job, prepared, _art(2026, 6, 10, 7, 0))
    assert outcome == "deferred"
    assert job.next_attempt_at == _art(2026, 6, 10, 8, 0).astimezone(timezone.utc)


def test_next_attempt_at_equal_to_start_is_skipped():
    service = ReminderService(MagicMock())
    start = _art(2026, 6, 10, 10, 5)
    job, prepared = _job_and_prepared(start)
    outcome = service._apply_send_result(
        job,
        prepared,
        ReminderSendResult.failure(retryable=True, error_code="http_503"),
        _art(2026, 6, 10, 10, 0),
    )
    assert outcome == "skipped"
    assert job.error_code == "retry_after_start"


def test_update_appointment_reschedules_when_start_at_changes():
    db = MagicMock()
    service = AppointmentService(db)
    org_id = uuid4()
    appt_id = uuid4()
    user = MagicMock()
    appt = MagicMock()
    appt.status = AppointmentStatus.PENDING
    appt.professional_id = uuid4()
    appt.start_at = _art(2026, 6, 10, 10, 0)
    appt.end_at = _art(2026, 6, 10, 10, 30)
    service.repo = MagicMock()
    service.repo.get_by_id.return_value = appt
    service.get_appointment = MagicMock(return_value=MagicMock())
    new_start = _art(2026, 6, 10, 11, 0)
    new_end = _art(2026, 6, 10, 11, 30)
    with (
        patch("app.services.appointment_service.assert_can_access_appointment"),
        patch("app.services.appointment_service.assert_no_overlap"),
        patch("app.services.appointment_service.ReminderService") as reminder_cls,
    ):
        reminder_cls.return_value.schedule_for_appointment.return_value = []
        service.update_appointment(
            org_id,
            appt_id,
            AppointmentUpdate(start_at=new_start, end_at=new_end),
            user,
        )
        reminder_cls.return_value.schedule_for_appointment.assert_called_once_with(org_id, appt_id)


def test_update_appointment_notes_does_not_reschedule():
    db = MagicMock()
    service = AppointmentService(db)
    org_id = uuid4()
    appt_id = uuid4()
    user = MagicMock()
    appt = MagicMock()
    appt.status = AppointmentStatus.PENDING
    appt.professional_id = uuid4()
    appt.start_at = _art(2026, 6, 10, 10, 0)
    appt.end_at = _art(2026, 6, 10, 10, 30)
    service.repo = MagicMock()
    service.repo.get_by_id.return_value = appt
    service.get_appointment = MagicMock(return_value=MagicMock())
    with (
        patch("app.services.appointment_service.assert_can_access_appointment"),
        patch("app.services.appointment_service.assert_no_overlap"),
        patch("app.services.appointment_service.ReminderService") as reminder_cls,
    ):
        service.update_appointment(org_id, appt_id, AppointmentUpdate(notes="hola"), user)
        reminder_cls.return_value.schedule_for_appointment.assert_not_called()
