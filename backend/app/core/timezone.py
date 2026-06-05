"""Zona horaria del consultorio (organizations.timezone)."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.models.organization import Organization

DEFAULT_ORG_TIMEZONE = "America/Argentina/Buenos_Aires"


def org_timezone(org: Organization) -> ZoneInfo:
    """Resuelve la zona IANA del consultorio con fallback seguro."""
    try:
        return ZoneInfo(org.timezone or DEFAULT_ORG_TIMEZONE)
    except Exception:
        return ZoneInfo(DEFAULT_ORG_TIMEZONE)


def local_day_bounds_utc(target_date: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """Límites UTC [inicio, fin) de un día local.

    Los turnos se guardan en UTC; para filtrar "el día X en hora del consultorio"
    hay que convertir 00:00 y 24:00 locales a UTC, no castear el timestamp a fecha
    (que lo bucketea en UTC y corre los turnos de la noche al día siguiente).
    """
    start_local = datetime.combine(target_date, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def local_date_range_bounds_utc(
    start_date: date,
    end_date_exclusive: date,
    tz: ZoneInfo,
) -> tuple[datetime, datetime]:
    """Límites UTC [inicio, fin) de un rango de días locales [start, end)."""
    start_local = datetime.combine(start_date, time.min, tzinfo=tz)
    end_local = datetime.combine(end_date_exclusive, time.min, tzinfo=tz)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def now_local(tz: ZoneInfo) -> datetime:
    """Momento actual en la zona del consultorio."""
    return datetime.now(timezone.utc).astimezone(tz)
