"""Tests de los limites de dia local en UTC (zona del consultorio)."""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.core.timezone import (
    DEFAULT_ORG_TIMEZONE,
    local_date_range_bounds_utc,
    local_day_bounds_utc,
)

AR = ZoneInfo(DEFAULT_ORG_TIMEZONE)  # Argentina, UTC-3 fijo (sin DST)


def test_local_day_bounds_argentina():
    start_utc, end_utc = local_day_bounds_utc(date(2026, 6, 6), AR)
    assert start_utc == datetime(2026, 6, 6, 3, 0, tzinfo=timezone.utc)
    assert end_utc == datetime(2026, 6, 7, 3, 0, tzinfo=timezone.utc)


def test_evening_appointment_belongs_to_local_day_not_utc_next_day():
    # Turno 22:00 hora local del 6/6 -> 01:00 UTC del 7/6.
    appt_utc = datetime(2026, 6, 6, 22, 0, tzinfo=AR).astimezone(timezone.utc)
    assert appt_utc == datetime(2026, 6, 7, 1, 0, tzinfo=timezone.utc)

    start_utc, end_utc = local_day_bounds_utc(date(2026, 6, 6), AR)
    # Debe caer dentro del dia local 6/6 (el bug de castear a fecha UTC lo excluia).
    assert start_utc <= appt_utc < end_utc


def test_local_date_range_bounds():
    start_utc, end_utc = local_date_range_bounds_utc(date(2026, 6, 1), date(2026, 7, 1), AR)
    assert start_utc == datetime(2026, 6, 1, 3, 0, tzinfo=timezone.utc)
    assert end_utc == datetime(2026, 7, 1, 3, 0, tzinfo=timezone.utc)
