import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, not_found
from app.core.rbac import assert_can_access_appointment
from app.core.tenant_validation import TenantResourceValidator
from app.core.timezone import local_date_range_bounds_utc, org_timezone
from app.models.appointment import Appointment
from app.models.enums import AppointmentClosureStatus, AppointmentStatus, UserRole
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.patient_repository import PatientRepository
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentCreateResult,
    AppointmentRescheduleRequest,
    AppointmentResponse,
    AppointmentUpdate,
)
from app.schemas.common import MessageResponse
from app.services.appointment_scheduling import assert_no_overlap
from app.services.recurring_series import resolve_create_weeks
from app.services.reminder_service import ReminderService


class AppointmentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AppointmentRepository(db)
        self.patients = PatientRepository(db)
        self.organizations = OrganizationRepository(db)
        self.tenant = TenantResourceValidator(db)

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
        tz = org_timezone(self.organizations.get_by_id(organization_id))
        if view == "week":
            range_start = reference_date - timedelta(days=reference_date.weekday())
            range_end = range_start + timedelta(days=7)
        else:
            range_start = reference_date
            range_end = reference_date + timedelta(days=1)

        # Ventana del rango local del consultorio expresada en limites UTC reales.
        start_utc, end_utc = local_date_range_bounds_utc(range_start, range_end, tz)
        items = self.repo.list_in_range(
            organization_id,
            start=start_utc,
            end=end_utc,
            professional_id=professional_id,
            status=status,
            patient_q=patient_q,
            closure_status=closure_status,
        )
        return [AppointmentResponse.model_validate(a) for a in items]

    def get_appointment(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
        current_user: User | None = None,
    ) -> AppointmentResponse:
        appointment = self.repo.get_by_id(organization_id, appointment_id)
        if not appointment:
            raise not_found("Turno")
        if current_user is not None:
            assert_can_access_appointment(current_user, appointment)
        return AppointmentResponse.model_validate(appointment)

    def create_appointment(
        self,
        organization_id: uuid.UUID,
        data: AppointmentCreate,
        current_user: User,
    ) -> AppointmentCreateResult:
        self.tenant.require_patient(organization_id, data.patient_id)
        if data.end_at <= data.start_at:
            raise bad_request("La hora de fin debe ser posterior al inicio")

        if current_user.role == UserRole.PROFESSIONAL:
            professional_id = current_user.id
        else:
            professional_id = data.professional_id or current_user.id

        self.tenant.require_professional(organization_id, professional_id)
        if data.health_insurance_id is not None:
            self.tenant.require_health_insurance(organization_id, data.health_insurance_id)

        weeks, series_indefinite = resolve_create_weeks(
            recurring_weekly=data.recurring_weekly,
            weeks=data.weeks,
        )
        series_id = uuid.uuid4() if data.recurring_weekly else None
        duration = data.end_at - data.start_at
        created: list[Appointment] = []

        try:
            self.repo.lock_professional_for_schedule(organization_id, professional_id)

            for week_offset in range(weeks):
                start_at = data.start_at + timedelta(weeks=week_offset)
                end_at = start_at + duration
                assert_no_overlap(
                    self.repo,
                    organization_id,
                    professional_id=professional_id,
                    start_at=start_at,
                    end_at=end_at,
                )

                appointment = Appointment(
                    organization_id=organization_id,
                    patient_id=data.patient_id,
                    professional_id=professional_id,
                    start_at=start_at,
                    end_at=end_at,
                    modality=data.modality,
                    attention_type=data.attention_type,
                    expected_amount=data.expected_amount,
                    health_insurance_id=data.health_insurance_id,
                    notes=data.notes,
                    series_id=series_id,
                    series_indefinite=series_indefinite,
                    status=AppointmentStatus.PENDING,
                    closure_status=AppointmentClosureStatus.NONE,
                )
                self.repo.create(appointment)
                created.append(appointment)

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        reminders = ReminderService(self.db)
        for appointment in created:
            reminders.schedule_for_appointment(organization_id, appointment.id)

        responses = [
            self.get_appointment(organization_id, appointment.id) for appointment in created
        ]
        return AppointmentCreateResult(
            created_count=len(responses),
            series_id=series_id,
            series_indefinite=series_indefinite,
            appointments=responses,
        )

    def update_appointment(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
        data: AppointmentUpdate,
        current_user: User,
    ) -> AppointmentResponse:
        appointment = self.repo.get_by_id(organization_id, appointment_id)
        if not appointment:
            raise not_found("Turno")
        assert_can_access_appointment(current_user, appointment)
        if appointment.status in (AppointmentStatus.CANCELLED, AppointmentStatus.RESCHEDULED):
            raise bad_request("No se puede editar este turno")

        updates = data.model_dump(exclude_unset=True)
        if "patient_id" in updates and updates["patient_id"] is not None:
            self.tenant.require_patient(organization_id, updates["patient_id"])
            appointment.patient_id = updates["patient_id"]
        if "professional_id" in updates:
            if updates["professional_id"] is not None:
                self.tenant.require_professional(organization_id, updates["professional_id"])
            appointment.professional_id = updates["professional_id"]
        if "health_insurance_id" in updates:
            if updates["health_insurance_id"] is not None:
                self.tenant.require_health_insurance(organization_id, updates["health_insurance_id"])
            appointment.health_insurance_id = updates["health_insurance_id"]
        if "start_at" in updates and updates["start_at"] is not None:
            appointment.start_at = updates["start_at"]
        if "end_at" in updates and updates["end_at"] is not None:
            appointment.end_at = updates["end_at"]
        if "modality" in updates and updates["modality"] is not None:
            appointment.modality = updates["modality"]
        if "attention_type" in updates and updates["attention_type"] is not None:
            appointment.attention_type = updates["attention_type"]
        if "expected_amount" in updates:
            appointment.expected_amount = updates["expected_amount"]
        if "notes" in updates:
            appointment.notes = updates["notes"]

        if appointment.end_at <= appointment.start_at:
            raise bad_request("La hora de fin debe ser posterior al inicio")
        # Un profesional no puede reasignar su turno a otro profesional.
        assert_can_access_appointment(current_user, appointment)

        assert_can_access_appointment(current_user, appointment)

        professional_id = appointment.professional_id
        if not professional_id:
            raise bad_request("El turno debe tener un profesional asignado para validar horario")

        try:
            self.repo.lock_professional_for_schedule(organization_id, professional_id)
            assert_no_overlap(
                self.repo,
                organization_id,
                professional_id=professional_id,
                start_at=appointment.start_at,
                end_at=appointment.end_at,
                exclude_appointment_id=appointment_id,
            )
            self.repo.update(appointment)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return self.get_appointment(organization_id, appointment_id)

    def _transition(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
        current_user: User,
        *,
        allowed_from: list[AppointmentStatus],
        new_status: AppointmentStatus,
    ) -> AppointmentResponse:
        appointment = self.repo.get_by_id(organization_id, appointment_id)
        if not appointment:
            raise not_found("Turno")
        assert_can_access_appointment(current_user, appointment)
        if appointment.status not in allowed_from:
            raise bad_request(f"No se puede cambiar de {appointment.status.value} a {new_status.value}")
        appointment.status = new_status
        self.repo.update(appointment)
        self.db.commit()
        return self.get_appointment(organization_id, appointment_id)

    def confirm(
        self, organization_id: uuid.UUID, appointment_id: uuid.UUID, current_user: User,
    ) -> AppointmentResponse:
        result = self._transition(
            organization_id,
            appointment_id,
            current_user,
            allowed_from=[AppointmentStatus.PENDING],
            new_status=AppointmentStatus.CONFIRMED,
        )
        ReminderService(self.db).schedule_for_appointment(organization_id, appointment_id)
        return result

    def mark_attended(
        self, organization_id: uuid.UUID, appointment_id: uuid.UUID, current_user: User,
    ) -> AppointmentResponse:
        return self._transition(
            organization_id,
            appointment_id,
            current_user,
            allowed_from=[AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED],
            new_status=AppointmentStatus.ATTENDED,
        )

    def mark_no_show(
        self, organization_id: uuid.UUID, appointment_id: uuid.UUID, current_user: User,
    ) -> AppointmentResponse:
        return self._transition(
            organization_id,
            appointment_id,
            current_user,
            allowed_from=[AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED],
            new_status=AppointmentStatus.NO_SHOW,
        )

    def cancel(
        self, organization_id: uuid.UUID, appointment_id: uuid.UUID, current_user: User,
    ) -> AppointmentResponse:
        result = self._transition(
            organization_id,
            appointment_id,
            current_user,
            allowed_from=[AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED],
            new_status=AppointmentStatus.CANCELLED,
        )
        ReminderService(self.db).cancel_for_appointment(organization_id, appointment_id)
        return result

    def cancel_series_from(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
        current_user: User,
    ) -> MessageResponse:
        """Cancela este turno fijo y todos los siguientes de la misma serie."""
        appointment = self.repo.get_by_id(organization_id, appointment_id)
        if not appointment:
            raise not_found("Turno")
        assert_can_access_appointment(current_user, appointment)
        if not appointment.series_id:
            raise bad_request("Este turno no pertenece a una serie fija")
        if appointment.status not in (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED):
            raise bad_request("Solo se pueden cancelar turnos pendientes o confirmados de la serie")

        to_cancel = self.repo.list_series_from(
            organization_id,
            appointment.series_id,
            from_start_at=appointment.start_at,
        )
        if not to_cancel:
            raise bad_request("No hay turnos pendientes en esta serie desde la fecha elegida")

        reminders = ReminderService(self.db)
        for item in to_cancel:
            assert_can_access_appointment(current_user, item)
            item.status = AppointmentStatus.CANCELLED
            self.repo.update(item)

        # Cortar renovación automática del fijo continuo.
        if appointment.series_indefinite:
            for row in self.db.scalars(
                select(Appointment).where(Appointment.series_id == appointment.series_id),
            ).all():
                row.series_indefinite = False
                self.repo.update(row)

        self.db.commit()

        for item in to_cancel:
            reminders.cancel_for_appointment(organization_id, item.id)

        count = len(to_cancel)
        return MessageResponse(
            message=(
                f"Se cancelaron {count} turnos fijos (este y los siguientes)."
                if count > 1
                else "Se canceló el turno fijo."
            ),
        )

    def reschedule(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
        data: AppointmentRescheduleRequest,
        current_user: User,
    ) -> AppointmentResponse:
        old = self.repo.get_by_id(organization_id, appointment_id)
        if not old:
            raise not_found("Turno")
        assert_can_access_appointment(current_user, old)
        if old.status in (AppointmentStatus.CANCELLED, AppointmentStatus.RESCHEDULED):
            raise bad_request("No se puede reprogramar este turno")
        if data.end_at <= data.start_at:
            raise bad_request("La hora de fin debe ser posterior al inicio")

        if current_user.role == UserRole.PROFESSIONAL:
            professional_id = current_user.id
        else:
            professional_id = data.professional_id or old.professional_id or current_user.id

        self.tenant.require_professional(organization_id, professional_id)

        try:
            self.repo.lock_professional_for_schedule(organization_id, professional_id)
            assert_no_overlap(
                self.repo,
                organization_id,
                professional_id=professional_id,
                start_at=data.start_at,
                end_at=data.end_at,
            )

            new_appt = Appointment(
                organization_id=organization_id,
                patient_id=old.patient_id,
                professional_id=professional_id,
                start_at=data.start_at,
                end_at=data.end_at,
                modality=old.modality,
                attention_type=old.attention_type,
                expected_amount=old.expected_amount,
                health_insurance_id=old.health_insurance_id,
                notes=data.notes or old.notes,
                # Reprogramar un turno de la serie lo saca de la serie (queda puntual).
                series_id=None,
                series_indefinite=False,
                status=AppointmentStatus.PENDING,
                closure_status=AppointmentClosureStatus.NONE,
            )
            self.repo.create(new_appt)
            old.status = AppointmentStatus.RESCHEDULED
            old.rescheduled_to_id = new_appt.id
            self.repo.update(old)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        reminders = ReminderService(self.db)
        reminders.cancel_for_appointment(organization_id, appointment_id)
        reminders.schedule_for_appointment(organization_id, new_appt.id)
        return self.get_appointment(organization_id, new_appt.id)
