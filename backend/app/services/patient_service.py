import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import conflict, not_found
from app.core.tenant_validation import TenantResourceValidator
from app.models.patient import Patient
from app.repositories.patient_repository import PatientRepository
from app.schemas.common import PaginatedResponse, pagination_meta
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate


class PatientService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PatientRepository(db)
        self.tenant = TenantResourceValidator(db)

    def list_patients(
        self,
        organization_id: uuid.UUID,
        *,
        page: int,
        page_size: int,
        q: str | None,
        is_active: bool | None,
    ) -> PaginatedResponse[PatientResponse]:
        items, total = self.repo.list_paginated(
            organization_id,
            page=page,
            page_size=page_size,
            q=q,
            is_active=is_active,
        )
        return PaginatedResponse(
            data=[PatientResponse.model_validate(p) for p in items],
            meta=pagination_meta(page, page_size, total),
        )

    def get_patient(self, organization_id: uuid.UUID, patient_id: uuid.UUID) -> PatientResponse:
        patient = self.repo.get_by_id(organization_id, patient_id)
        if not patient:
            raise not_found("Paciente")
        return PatientResponse.model_validate(patient)

    def create_patient(self, organization_id: uuid.UUID, data: PatientCreate) -> PatientResponse:
        existing = self.repo.get_by_dni(organization_id, data.dni.strip())
        if existing:
            raise conflict("Ya existe un paciente con ese DNI")

        if data.health_insurance_id is not None:
            self.tenant.require_health_insurance(organization_id, data.health_insurance_id)

        patient = Patient(
            organization_id=organization_id,
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            dni=data.dni.strip(),
            phone=data.phone,
            email=str(data.email) if data.email else None,
            birth_date=data.birth_date,
            health_insurance_id=data.health_insurance_id,
            affiliate_number=data.affiliate_number,
            notes=data.notes,
            is_active=data.is_active,
        )
        self.repo.create(patient)
        self.db.commit()
        self.db.refresh(patient)
        return PatientResponse.model_validate(patient)

    def update_patient(
        self,
        organization_id: uuid.UUID,
        patient_id: uuid.UUID,
        data: PatientUpdate,
    ) -> PatientResponse:
        patient = self.repo.get_by_id(organization_id, patient_id)
        if not patient:
            raise not_found("Paciente")

        updates = data.model_dump(exclude_unset=True)
        if "dni" in updates and updates["dni"]:
            updates["dni"] = updates["dni"].strip()
            other = self.repo.get_by_dni(organization_id, updates["dni"])
            if other and other.id != patient.id:
                raise conflict("Ya existe un paciente con ese DNI")

        if "email" in updates and updates["email"]:
            updates["email"] = str(updates["email"])

        if "health_insurance_id" in updates and updates["health_insurance_id"] is not None:
            self.tenant.require_health_insurance(organization_id, updates["health_insurance_id"])

        scalar_fields = (
            "first_name",
            "last_name",
            "dni",
            "phone",
            "email",
            "birth_date",
            "health_insurance_id",
            "affiliate_number",
            "notes",
            "is_active",
        )
        for field in scalar_fields:
            if field in updates:
                value = updates[field]
                if field in ("first_name", "last_name", "dni") and isinstance(value, str):
                    value = value.strip() or (None if field == "dni" else value.strip())
                setattr(patient, field, value)

        self.repo.update(patient)
        self.db.commit()
        self.db.refresh(patient)
        return PatientResponse.model_validate(patient)

    def delete_patient(self, organization_id: uuid.UUID, patient_id: uuid.UUID) -> None:
        patient = self.repo.get_by_id(organization_id, patient_id)
        if not patient:
            raise not_found("Paciente")

        patient.deleted_at = datetime.now(timezone.utc)
        patient.is_active = False
        self.repo.update(patient)
        self.db.commit()
