import uuid
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, conflict, not_found
from app.core.rbac import (
    assert_can_access_appointment,
    assert_can_access_patient_clinical_profile,
    assert_can_create_standalone_consultation,
    assert_can_modify_consultation,
    assert_can_read_consultation,
    assert_clinical_access,
)
from app.core.tenant_validation import TenantResourceValidator
from app.models.consultation import Consultation
from app.models.enums import AppointmentStatus, ConsultationStatus, UserRole
from app.models.patient import Patient
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.consultation_repository import ConsultationRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.user_repository import UserRepository
from app.schemas.consultation import (
    ConsultationAmendmentCreate,
    ConsultationListItem,
    ConsultationResponse,
    ConsultationUpdate,
    PatientClinicalResponse,
    PatientClinicalUpdate,
    PatientConsultationCreate,
)


class ConsultationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.consultations = ConsultationRepository(db)
        self.appointments = AppointmentRepository(db)
        self.patients = PatientRepository(db)
        self.users = UserRepository(db)
        self.tenant = TenantResourceValidator(db)

    def _professional_filter(self, user: User) -> uuid.UUID | None:
        if user.role == UserRole.PROFESSIONAL:
            return user.id
        return None

    def get_by_appointment(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
        current_user: User,
    ) -> ConsultationResponse:
        assert_clinical_access(current_user)

        appointment = self.appointments.get_by_id(organization_id, appointment_id)
        if not appointment:
            raise not_found("Turno")
        assert_can_access_appointment(current_user, appointment)

        consultation = self.consultations.get_by_appointment_id(organization_id, appointment_id)
        if not consultation:
            raise not_found("Consulta")
        has_relationship = self._has_clinical_relationship(
            organization_id, current_user, consultation.patient_id,
        )
        assert_can_read_consultation(
            current_user, consultation, has_relationship=has_relationship,
        )
        return self._to_response(consultation)

    def create_for_appointment(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
        current_user: User,
    ) -> ConsultationResponse:
        assert_clinical_access(current_user)

        appointment = self.appointments.get_by_id(organization_id, appointment_id)
        if not appointment:
            raise not_found("Turno")
        assert_can_access_appointment(current_user, appointment)

        if appointment.status != AppointmentStatus.ATTENDED:
            raise bad_request("Solo se puede atender un turno marcado como asistió")

        if not appointment.professional_id:
            raise bad_request("El turno debe tener un profesional asignado")

        existing = self.consultations.get_by_appointment_id(organization_id, appointment_id)
        if existing:
            raise conflict("Ya existe una consulta para este turno")

        consultation = Consultation(
            organization_id=organization_id,
            appointment_id=appointment.id,
            patient_id=appointment.patient_id,
            professional_id=appointment.professional_id,
            status=ConsultationStatus.DRAFT,
            occurred_at=appointment.start_at,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        try:
            self.consultations.create(consultation)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise conflict("Ya existe una consulta para este turno")
        self.db.refresh(consultation)
        return self._to_response(
            self.consultations.get_by_id(organization_id, consultation.id),
        )

    def create_for_patient(
        self,
        organization_id: uuid.UUID,
        patient_id: uuid.UUID,
        data: PatientConsultationCreate,
        current_user: User,
    ) -> ConsultationResponse:
        assert_can_create_standalone_consultation(current_user)
        patient = self.patients.get_by_id(organization_id, patient_id)
        if not patient:
            raise not_found("Paciente")

        now = datetime.now(timezone.utc)
        occurred_at = self._resolve_occurred_at(data.occurred_at, fallback=now)
        consultation = Consultation(
            organization_id=organization_id,
            appointment_id=None,
            patient_id=patient.id,
            professional_id=current_user.id,
            status=ConsultationStatus.DRAFT,
            occurred_at=occurred_at,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        self.consultations.create(consultation)
        self.db.commit()
        self.db.refresh(consultation)
        return self._to_response(
            self.consultations.get_by_id(organization_id, consultation.id),
        )

    def update_consultation(
        self,
        organization_id: uuid.UUID,
        consultation_id: uuid.UUID,
        data: ConsultationUpdate,
        current_user: User,
    ) -> ConsultationResponse:
        consultation = self.consultations.get_by_id(organization_id, consultation_id)
        if not consultation:
            raise not_found("Consulta")
        assert_can_modify_consultation(current_user, consultation)

        if consultation.status != ConsultationStatus.DRAFT:
            raise bad_request("Solo se pueden modificar consultas en borrador")

        updates = data.model_dump(exclude_unset=True)
        for field in ("reason", "evolution", "diagnosis", "indications"):
            if field in updates:
                setattr(consultation, field, updates[field])

        consultation.updated_by = current_user.id
        self.consultations.update(consultation)
        self.db.commit()
        self.db.refresh(consultation)
        return self._to_response(consultation)

    def finalize_consultation(
        self,
        organization_id: uuid.UUID,
        consultation_id: uuid.UUID,
        current_user: User,
    ) -> ConsultationResponse:
        consultation = self.consultations.get_by_id(organization_id, consultation_id)
        if not consultation:
            raise not_found("Consulta")
        assert_can_modify_consultation(current_user, consultation)

        if consultation.status != ConsultationStatus.DRAFT:
            raise bad_request("La consulta ya fue finalizada")

        if consultation.appointment_id is not None:
            appointment = self.appointments.get_by_id(
                organization_id, consultation.appointment_id,
            )
            if not appointment:
                raise not_found("Turno")
            if appointment.status != AppointmentStatus.ATTENDED:
                raise bad_request("El turno debe estar marcado como asistió")

        if not (consultation.reason and consultation.reason.strip()):
            raise bad_request("El motivo de consulta es obligatorio para finalizar")
        if not (consultation.evolution and consultation.evolution.strip()):
            raise bad_request("La evolución es obligatoria para finalizar")

        professional = consultation.professional or self.db.get(User, consultation.professional_id)
        if not professional:
            raise bad_request("No se encontró el profesional de la consulta")

        consultation.professional_name_snapshot = professional.full_name
        consultation.professional_license_snapshot = professional.license_number
        consultation.status = ConsultationStatus.FINALIZED
        consultation.updated_by = current_user.id
        self.consultations.update(consultation)
        self.db.commit()
        self.db.refresh(consultation)
        return self._to_response(consultation)

    def list_patient_consultations(
        self,
        organization_id: uuid.UUID,
        patient_id: uuid.UUID,
        current_user: User,
        *,
        limit: int | None = None,
    ) -> list[ConsultationListItem]:
        assert_clinical_access(current_user)
        if not self.patients.get_by_id(organization_id, patient_id):
            raise not_found("Paciente")

        has_relationship = self._has_clinical_relationship(
            organization_id, current_user, patient_id,
        )
        if current_user.role == UserRole.PROFESSIONAL:
            assert_can_access_patient_clinical_profile(
                current_user, has_relationship=has_relationship,
            )

        prof_filter = self._professional_filter(current_user)
        rows = self.consultations.list_by_patient(
            organization_id,
            patient_id,
            professional_id=prof_filter,
            include_colleague_finalized=current_user.role == UserRole.PROFESSIONAL,
            limit=limit,
        )
        return [self._to_list_item(row) for row in rows]

    def get_consultation(
        self,
        organization_id: uuid.UUID,
        consultation_id: uuid.UUID,
        current_user: User,
    ) -> ConsultationResponse:
        consultation = self.consultations.get_by_id(organization_id, consultation_id)
        if not consultation:
            raise not_found("Consulta")
        has_relationship = self._has_clinical_relationship(
            organization_id, current_user, consultation.patient_id,
        )
        assert_can_read_consultation(
            current_user, consultation, has_relationship=has_relationship,
        )
        return self._to_response(consultation)

    def create_amendment(
        self,
        organization_id: uuid.UUID,
        consultation_id: uuid.UUID,
        data: ConsultationAmendmentCreate,
        current_user: User,
    ) -> ConsultationResponse:
        assert_clinical_access(current_user)
        source = self.consultations.get_by_id(organization_id, consultation_id)
        if not source:
            raise not_found("Consulta")

        has_relationship = self._has_clinical_relationship(
            organization_id, current_user, source.patient_id,
        )
        assert_can_read_consultation(
            current_user, source, has_relationship=has_relationship,
        )
        if current_user.role == UserRole.PROFESSIONAL:
            assert_can_access_patient_clinical_profile(
                current_user, has_relationship=has_relationship,
            )

        if source.status != ConsultationStatus.FINALIZED:
            raise bad_request("Solo se puede corregir una consulta finalizada")

        amend_reason = (data.amend_reason or "").strip()
        if not amend_reason:
            raise bad_request("El motivo de la corrección es obligatorio")

        original = source
        if source.amends_id is not None:
            original = self.consultations.get_by_id(organization_id, source.amends_id)
            if not original:
                raise bad_request("No se encontró la consulta original a corregir")

        consultation = Consultation(
            organization_id=organization_id,
            appointment_id=original.appointment_id,
            patient_id=original.patient_id,
            professional_id=current_user.id,
            amends_id=original.id,
            amend_reason=amend_reason,
            occurred_at=original.occurred_at,
            status=ConsultationStatus.DRAFT,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        try:
            self.consultations.create(consultation)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise bad_request("No se pudo registrar la corrección")
        self.db.refresh(consultation)
        return self._to_response(
            self.consultations.get_by_id(organization_id, consultation.id),
        )

    def _has_clinical_relationship(
        self,
        organization_id: uuid.UUID,
        user: User,
        patient_id: uuid.UUID,
    ) -> bool:
        if user.role != UserRole.PROFESSIONAL:
            return True
        return self._professional_has_patient_relationship(
            organization_id, user.id, patient_id,
        )

    def _professional_has_patient_relationship(
        self,
        organization_id: uuid.UUID,
        professional_id: uuid.UUID,
        patient_id: uuid.UUID,
    ) -> bool:
        if self.appointments.exists_professional_patient(
            organization_id, professional_id, patient_id,
        ):
            return True
        return self.consultations.exists_professional_patient(
            organization_id, professional_id, patient_id,
        )

    def get_patient_clinical(
        self,
        organization_id: uuid.UUID,
        patient_id: uuid.UUID,
        current_user: User,
    ) -> PatientClinicalResponse:
        patient = self.patients.get_by_id(organization_id, patient_id)
        if not patient:
            raise not_found("Paciente")

        has_relationship = True
        if current_user.role == UserRole.PROFESSIONAL:
            has_relationship = self._professional_has_patient_relationship(
                organization_id, current_user.id, patient_id,
            )
        assert_can_access_patient_clinical_profile(
            current_user, has_relationship=has_relationship,
        )
        return self._to_clinical_response(patient)

    def update_patient_clinical(
        self,
        organization_id: uuid.UUID,
        patient_id: uuid.UUID,
        data: PatientClinicalUpdate,
        current_user: User,
    ) -> PatientClinicalResponse:
        patient = self.patients.get_by_id(organization_id, patient_id)
        if not patient:
            raise not_found("Paciente")

        has_relationship = True
        if current_user.role == UserRole.PROFESSIONAL:
            has_relationship = self._professional_has_patient_relationship(
                organization_id, current_user.id, patient_id,
            )
        assert_can_access_patient_clinical_profile(
            current_user, has_relationship=has_relationship,
        )

        updates = data.model_dump(exclude_unset=True)
        clinical_fields = (
            "medical_history",
            "allergies",
            "current_medications",
            "clinical_notes",
        )
        changed = False
        for field in clinical_fields:
            if field in updates:
                setattr(patient, field, updates[field])
                changed = True

        if changed:
            patient.clinical_updated_by = current_user.id
            patient.clinical_updated_at = datetime.now(timezone.utc)
            self.patients.update(patient)
            self.db.commit()
            self.db.refresh(patient)

        return self._to_clinical_response(patient)

    @classmethod
    def _resolve_occurred_at(
        cls,
        value: datetime | None,
        *,
        fallback: datetime,
    ) -> datetime:
        occurred = value if value is not None else fallback
        if occurred.tzinfo is None:
            occurred = occurred.replace(tzinfo=timezone.utc)
        return occurred

    def _to_clinical_response(self, patient: Patient) -> PatientClinicalResponse:
        updater_name = None
        if patient.clinical_updated_by:
            updater = self.users.get_by_id_in_organization(
                patient.organization_id,
                patient.clinical_updated_by,
            )
            if updater:
                updater_name = updater.full_name
        return PatientClinicalResponse(
            patient_id=patient.id,
            medical_history=patient.medical_history,
            allergies=patient.allergies,
            current_medications=patient.current_medications,
            clinical_notes=patient.clinical_notes,
            clinical_updated_by=patient.clinical_updated_by,
            clinical_updated_by_name=updater_name,
            clinical_updated_at=patient.clinical_updated_at,
        )

    @staticmethod
    def _display_professional_name(row: Consultation) -> str | None:
        if row.status == ConsultationStatus.FINALIZED and row.professional_name_snapshot:
            return row.professional_name_snapshot
        if row.professional:
            return row.professional.full_name
        return row.professional_name_snapshot

    def _to_response(self, consultation: Consultation | None) -> ConsultationResponse:
        if consultation is None:
            raise not_found("Consulta")
        payload = ConsultationResponse.model_validate(consultation)
        return payload.model_copy(
            update={"professional_name": self._display_professional_name(consultation)},
        )

    @staticmethod
    def _to_list_item(row: Consultation) -> ConsultationListItem:
        return ConsultationListItem(
            id=row.id,
            appointment_id=row.appointment_id,
            professional_id=row.professional_id,
            professional_name=ConsultationService._display_professional_name(row),
            appointment_start_at=row.appointment.start_at if row.appointment else None,
            amends_id=row.amends_id,
            amend_reason=row.amend_reason,
            occurred_at=row.occurred_at,
            reason=row.reason,
            evolution=row.evolution,
            diagnosis=row.diagnosis,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
