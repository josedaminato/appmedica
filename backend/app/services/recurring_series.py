"""Constantes y extensión de turnos fijos indefinidos."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.appointment import Appointment
from app.models.enums import AppointmentClosureStatus, AppointmentStatus
from app.repositories.appointment_repository import AppointmentRepository
from app.services.appointment_scheduling import assert_no_overlap
from app.services.reminder_service import ReminderService

logger = logging.getLogger(__name__)

# Cuántas semanas se generan al crear un fijo continuo.
INDEFINITE_HORIZON_WEEKS = 16
# Si el último turno activo queda a menos de esto, se extiende la serie.
INDEFINITE_MIN_WEEKS_AHEAD = 4
# Semanas a agregar en cada extensión (hasta recuperar el horizonte).
INDEFINITE_EXTEND_CHUNK_WEEKS = 12

_ACTIVE = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)


def _as_utc(dt: datetime) -> datetime:
    """Normaliza datetimes naive (SQLite) a aware UTC para comparar."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def resolve_create_weeks(*, recurring_weekly: bool, weeks: int | None) -> tuple[int, bool]:
    """Devuelve (cantidad de turnos a crear, es_indefinido)."""
    if not recurring_weekly:
        return 1, False
    if weeks is None:
        return INDEFINITE_HORIZON_WEEKS, True
    return weeks, False


def extend_indefinite_series(db: Session) -> dict[str, int]:
    """Extiende series fijas indefinidas que se están quedando cortas de horizonte.

    Pensado para cron diario. Si un horario choca, saltea esa semana y sigue.
    """
    now = datetime.now(timezone.utc)
    threshold = now + timedelta(weeks=INDEFINITE_MIN_WEEKS_AHEAD)
    target_horizon = now + timedelta(weeks=INDEFINITE_HORIZON_WEEKS)

    series_ids = list(
        db.scalars(
            select(Appointment.series_id)
            .where(
                Appointment.series_id.is_not(None),
                Appointment.series_indefinite.is_(True),
                Appointment.status.in_(_ACTIVE),
            )
            .distinct(),
        ).all(),
    )

    series_extended = 0
    appointments_created = 0
    skipped_conflicts = 0
    repo = AppointmentRepository(db)

    for series_id in series_ids:
        if series_id is None:
            continue
        last_active = db.scalar(
            select(Appointment)
            .where(
                Appointment.series_id == series_id,
                Appointment.status.in_(_ACTIVE),
            )
            .order_by(Appointment.start_at.desc())
            .limit(1),
        )
        if last_active is None or _as_utc(last_active.start_at) >= threshold:
            continue

        template = db.scalar(
            select(Appointment)
            .where(Appointment.series_id == series_id)
            .order_by(Appointment.start_at.desc())
            .limit(1),
        )
        if template is None or template.professional_id is None:
            continue

        duration = template.end_at - template.start_at
        next_start = _as_utc(last_active.start_at) + timedelta(weeks=1)
        created_here: list[Appointment] = []
        weeks_tried = 0

        try:
            while next_start <= target_horizon and weeks_tried < INDEFINITE_EXTEND_CHUNK_WEEKS + 8:
                weeks_tried += 1
                end_at = next_start + duration
                try:
                    assert_no_overlap(
                        repo,
                        template.organization_id,
                        professional_id=template.professional_id,
                        start_at=next_start,
                        end_at=end_at,
                    )
                except AppException:
                    skipped_conflicts += 1
                    next_start += timedelta(weeks=1)
                    continue

                appointment = Appointment(
                    organization_id=template.organization_id,
                    patient_id=template.patient_id,
                    professional_id=template.professional_id,
                    start_at=next_start,
                    end_at=end_at,
                    modality=template.modality,
                    attention_type=template.attention_type,
                    expected_amount=template.expected_amount,
                    health_insurance_id=template.health_insurance_id,
                    notes=template.notes,
                    series_id=series_id,
                    series_indefinite=True,
                    status=AppointmentStatus.PENDING,
                    closure_status=AppointmentClosureStatus.NONE,
                )
                repo.create(appointment)
                created_here.append(appointment)
                next_start += timedelta(weeks=1)

            if created_here:
                db.commit()
                reminders = ReminderService(db)
                for appointment in created_here:
                    reminders.schedule_for_appointment(
                        appointment.organization_id,
                        appointment.id,
                    )
                series_extended += 1
                appointments_created += len(created_here)
            else:
                db.rollback()
        except Exception:
            db.rollback()
            logger.exception("No se pudo extender serie %s", series_id)

    return {
        "series_checked": len(series_ids),
        "series_extended": series_extended,
        "appointments_created": appointments_created,
        "skipped_conflicts": skipped_conflicts,
    }
