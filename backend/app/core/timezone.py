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


# Ventana de envío de recordatorios al paciente: [08:00:00, 21:00:00] hora local.
# Silencio: (21:00:00, 08:00:00). 21:00:00 y 08:00:00 son válidos; 21:00:01 y 07:59:59 no.
REMINDER_QUIET_START = time(21, 0)
REMINDER_QUIET_END = time(8, 0)
REMINDER_MIN_LEAD = timedelta(minutes=30)


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def is_in_quiet_hours(moment: datetime, tz: ZoneInfo) -> bool:
    """True si el instante cae en (21:00:00, 08:00:00) hora local del consultorio."""
    local_t = _as_utc(moment).astimezone(tz).time()
    return local_t > REMINDER_QUIET_START or local_t < REMINDER_QUIET_END


def has_min_reminder_lead(start_at: datetime, send_at: datetime) -> bool:
    """True si send_at < start_at y el margen es >= 30 minutos."""
    start_utc = _as_utc(start_at)
    send_utc = _as_utc(send_at)
    return send_utc < start_utc and start_utc - send_utc >= REMINDER_MIN_LEAD


def clamp_to_send_window(moment: datetime, tz: ZoneInfo) -> datetime:
    """Adelanta un instante UTC a la próxima ventana [08:00:00, 21:00:00] local.

    Si ya está en ventana, lo deja igual. Nunca mueve hacia atrás.
    """
    utc_moment = _as_utc(moment)
    local = utc_moment.astimezone(tz)
    local_t = local.time()
    if local_t > REMINDER_QUIET_START:
        send_local = datetime.combine(
            local.date() + timedelta(days=1),
            REMINDER_QUIET_END,
            tzinfo=tz,
        )
        return send_local.astimezone(timezone.utc)
    if local_t < REMINDER_QUIET_END:
        send_local = datetime.combine(local.date(), REMINDER_QUIET_END, tzinfo=tz)
        return send_local.astimezone(timezone.utc)
    return utc_moment


def compute_reminder_send_at(
    *,
    start_at: datetime,
    now: datetime,
    tz: ZoneInfo,
    hours_before: int = 24,
) -> datetime | None:
    """UTC en el que debe intentarse el reminder, o None si no corresponde.

    T−24h preferido; si ya pasó, `now`; quiet hours hacia adelante;
    omitir si el turno ya empezó, send_at >= start_at, o el margen es < 30 min.
    """
    start_utc = _as_utc(start_at)
    now_utc = _as_utc(now)
    if start_utc <= now_utc:
        return None

    desired = start_utc - timedelta(hours=hours_before)
    if desired < now_utc:
        desired = now_utc

    send_at = clamp_to_send_window(desired, tz)
    if not has_min_reminder_lead(start_utc, send_at):
        return None
    return send_at
