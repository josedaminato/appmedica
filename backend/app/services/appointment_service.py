import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, not_found
from app.models.appointment import Appointment
from app.models.enums import AppointmentClosureStatus, AppointmentStatus
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.patient_repository import PatientRepository
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentRescheduleRequest,
    AppointmentResponse,
    AppointmentUpdate,
)


class AppointmentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AppointmentRepository(db)
        self.patients = PatientRepository(db)

    def list_appointments(
        self,
        organization_id: uuid.UUID,
        *,
        view: str,
        reference_date: date,
        professional_id: uuid.UUID | None,
        status: AppointmentStatus | None,
        patient_q: str | None,
        closure_status: AppointmentClosureStatus | None,
    ) -> list[AppointmentResponse]:
        if view == "week":
            week_start = reference_date - timedelta(days=reference_date.weekday())
            week_end = week_start + timedelta(days=7)
            items = self.repo.list_in_range(
                organization_id,
                start=datetime.min.replace(tzinfo=timezone.utc),
                end=datetime.max.replace(tzinfo=timezone.utc),
                professional_id=professional_id,
                status=status,
                patient_q=patient_q,
                closure_status=closure_status,
                use_date_filter=True,
                start_date=week_start,
                end_date=week_end,
            )
        else:
            day_end = reference_date + timedelta(days=1)
            items = self.repo.list_in_range(
                organization_id,
                start=datetime.min.replace(tzinfo=timezone.utc),
                end=datetime.max.replace(tzinfo=timezone.utc),
                professional_id=professional_id,
                status=status,
                patient_q=patient_q,
                closure_status=closure_status,
                use_date_filter=True,
                start_date=reference_date,
                end_date=day_end,
            )
        return [AppointmentResponse.model_validate(a) for a in items]

    def get_appointment(self, organization_id: uuid.UUID, appointment_id: uuid.UUID) -> AppointmentResponse:
        appointment = self.repo.get_by_id(organization_id, appointment_id)
        if not appointment:
            raise not_found("Turno")
        return AppointmentResponse.model_validate(appointment)

    def create_appointment(
        self,
        organization_id: uuid.UUID,
        data: AppointmentCreate,
        default_professional_id: uuid.UUID | None,
    ) -> AppointmentResponse:
        if not self.patients.get_by_id(organization_id, data.patient_id):
            raise not_found("Paciente")
        if data.end_at <= data.start_at:
            raise bad_request("La hora de fin debe ser posterior al inicio")

        appointment = Appointment(
            organization_id=organization_id,
            patient_id=data.patient_id,
            professional_id=data.professional_id or default_professional_id,
            start_at=data.start_at,
            end_at=data.end_at,
            modality=data.modality,
            attention_type=data.attention_type,
            expected_amount=data.expected_amount,
            health_insurance_id=data.health_insurance_id,
            notes=data.notes,
            status=AppointmentStatus.PENDING,
            closure_status=AppointmentClosureStatus.NONE,
        )
        self.repo.create(appointment)
        self.db.commit()
        return self.get_appointment(organization_id, appointment.id)

    def update_appointment(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
        data: AppointmentUpdate,
    ) -> AppointmentResponse:
        appointment = self.repo.get_by_id(organization_id, appointment_id)
        if not appointment:
            raise not_found("Turno")
        if appointment.status in (AppointmentStatus.CANCELLED, AppointmentStatus.RESCHEDULED):
            raise bad_request("No se puede editar este turno")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(appointment, field, value)
        if appointment.end_at <= appointment.start_at:
            raise bad_request("La hora de fin debe ser posterior al inicio")

        self.repo.update(appointment)
        self.db.commit()
        return self.get_appointment(organization_id, appointment_id)

    def _transition(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
        *,
        allowed_from: list[AppointmentStatus],
        new_status: AppointmentStatus,
    ) -> AppointmentResponse:
        appointment = self.repo.get_by_id(organization_id, appointment_id)
        if not appointment:
            raise not_found("Turno")
        if appointment.status not in allowed_from:
            raise bad_request(f"No se puede cambiar de {appointment.status.value} a {new_status.value}")
        appointment.status = new_status
        self.repo.update(appointment)
        self.db.commit()
        return self.get_appointment(organization_id, appointment_id)

    def confirm(self, organization_id: uuid.UUID, appointment_id: uuid.UUID) -> AppointmentResponse:
        return self._transition(
            organization_id,
            appointment_id,
            allowed_from=[AppointmentStatus.PENDING],
            new_status=AppointmentStatus.CONFIRMED,
        )

    def mark_attended(self, organization_id: uuid.UUID, appointment_id: uuid.UUID) -> AppointmentResponse:
        return self._transition(
            organization_id,
            appointment_id,
            allowed_from=[AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED],
            new_status=AppointmentStatus.ATTENDED,
        )

    def mark_no_show(self, organization_id: uuid.UUID, appointment_id: uuid.UUID) -> AppointmentResponse:
        return self._transition(
            organization_id,
            appointment_id,
            allowed_from=[AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED],
            new_status=AppointmentStatus.NO_SHOW,
        )

    def cancel(self, organization_id: uuid.UUID, appointment_id: uuid.UUID) -> AppointmentResponse:
        return self._transition(
            organization_id,
            appointment_id,
            allowed_from=[AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED],
            new_status=AppointmentStatus.CANCELLED,
        )

    def reschedule(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
        data: AppointmentRescheduleRequest,
        default_professional_id: uuid.UUID | None,
    ) -> AppointmentResponse:
        old = self.repo.get_by_id(organization_id, appointment_id)
        if not old:
            raise not_found("Turno")
        if old.status in (AppointmentStatus.CANCELLED, AppointmentStatus.RESCHEDULED):
            raise bad_request("No se puede reprogramar este turno")
        if data.end_at <= data.start_at:
            raise bad_request("La hora de fin debe ser posterior al inicio")

        new_appt = Appointment(
            organization_id=organization_id,
            patient_id=old.patient_id,
            professional_id=data.professional_id or old.professional_id or default_professional_id,
            start_at=data.start_at,
            end_at=data.end_at,
            modality=old.modality,
            attention_type=old.attention_type,
            expected_amount=old.expected_amount,
            health_insurance_id=old.health_insurance_id,
            notes=data.notes or old.notes,
            status=AppointmentStatus.PENDING,
            closure_status=AppointmentClosureStatus.NONE,
        )
        self.repo.create(new_appt)
        old.status = AppointmentStatus.RESCHEDULED
        old.rescheduled_to_id = new_appt.id
        self.repo.update(old)
        self.db.commit()
        return self.get_appointment(organization_id, new_appt.id)
