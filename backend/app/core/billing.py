import calendar
from datetime import date, datetime, timezone
from decimal import Decimal


DEFAULT_MONTHLY_FEE = Decimal("25000")


def add_calendar_month(value: date) -> date:
    month = value.month + 1
    year = value.year
    if month > 12:
        month = 1
        year += 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(value.day, last_day))


def initial_paid_until(start: datetime | None = None) -> date:
    started = start or datetime.now(timezone.utc)
    return add_calendar_month(started.date())


def extend_paid_period(current_paid_until: date | None) -> date:
    today = datetime.now(timezone.utc).date()
    base = today
    if current_paid_until and current_paid_until > today:
        base = current_paid_until
    return add_calendar_month(base)


def payment_status(paid_until: date | None) -> tuple[str, int | None]:
    """Devuelve (estado, días hasta el vencimiento; negativo si está vencido)."""
    if paid_until is None:
        return "unknown", None

    today = datetime.now(timezone.utc).date()
    days = (paid_until - today).days
    if days < 0:
        return "overdue", days
    if days == 0:
        return "due_today", 0
    if days <= 7:
        return "due_soon", days
    return "current", days
