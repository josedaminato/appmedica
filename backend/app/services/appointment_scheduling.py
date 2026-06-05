"""Validaciones de horario para turnos."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.core.exceptions import conflict
from app.repositories.appointment_repository import AppointmentRepository


def assert_no_overlap(
    repo: AppointmentRepository,
    organization_id: uuid.UUID,
    *,
    professional_id: uuid.UUID | None,
    start_at: datetime,
    end_at: datetime,
    exclude_appointment_id: uuid.UUID | None = None,
) -> None:
    if not professional_id:
        return

    overlaps = repo.find_overlapping(
        organization_id,
        professional_id=professional_id,
        start_at=start_at,
        end_at=end_at,
        exclude_appointment_id=exclude_appointment_id,
    )
    if not overlaps:
        return

    other = overlaps[0]
    patient_name = "otro paciente"
    if other.patient:
        patient_name = f"{other.patient.last_name}, {other.patient.first_name}"

    other_start = other.start_at.astimezone(start_at.tzinfo).strftime("%H:%M")
    other_end = other.end_at.astimezone(start_at.tzinfo).strftime("%H:%M")
    raise conflict(
        f"Ese horario se superpone con un turno de {patient_name} ({other_start}–{other_end}). "
        "Elegí otro horario o duración.",
    )
