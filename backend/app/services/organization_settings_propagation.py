"""Actualiza turnos futuros cuando cambia el valor estándar del consultorio."""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus, AttentionType

_FUTURE_STATUSES = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)


def _uses_standard_amount(current: Decimal | None, old_standard: Decimal | None) -> bool:
    if current is None:
        return True
    if old_standard is None:
        return False
    return current == old_standard


def propagate_private_session_amount(
    db: Session,
    organization_id: uuid.UUID,
    old_standard: Decimal | None,
    new_standard: Decimal | None,
) -> int:
    """
    Al subir el valor (ej. inflación), actualiza turnos particulares futuros que aún
    tenían el valor estándar anterior o ninguno. No toca montos personalizados distintos.
    """
    if new_standard is None or new_standard == old_standard:
        return 0

    now = datetime.now(timezone.utc)
    stmt = select(Appointment).where(
        Appointment.organization_id == organization_id,
        Appointment.attention_type == AttentionType.PRIVATE,
        Appointment.start_at >= now,
        Appointment.status.in_(_FUTURE_STATUSES),
    )
    updated = 0
    for appt in db.scalars(stmt).all():
        if _uses_standard_amount(appt.expected_amount, old_standard):
            appt.expected_amount = new_standard
            updated += 1
    return updated


def appointment_duration_minutes(appt: Appointment) -> int:
    delta = appt.end_at - appt.start_at
    return int(delta.total_seconds() // 60)


def propagate_appointment_duration(
    db: Session,
    organization_id: uuid.UUID,
    old_minutes: int,
    new_minutes: int,
) -> int:
    if old_minutes == new_minutes:
        return 0

    now = datetime.now(timezone.utc)
    stmt = select(Appointment).where(
        Appointment.organization_id == organization_id,
        Appointment.start_at >= now,
        Appointment.status.in_(_FUTURE_STATUSES),
    )
    updated = 0
    for appt in db.scalars(stmt).all():
        if appointment_duration_minutes(appt) != old_minutes:
            continue
        appt.end_at = appt.start_at + timedelta(minutes=new_minutes)
        updated += 1
    return updated
