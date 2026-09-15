import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ConsultationStatus


class ConsultationUpdate(BaseModel):
    reason: str | None = None
    evolution: str | None = None
    diagnosis: str | None = None
    indications: str | None = None


class PatientConsultationCreate(BaseModel):
    occurred_at: datetime | None = None


class ConsultationAmendmentCreate(BaseModel):
    amend_reason: str


class ConsultationResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    appointment_id: uuid.UUID | None = None
    patient_id: uuid.UUID
    professional_id: uuid.UUID
    professional_name: str | None = None
    professional_name_snapshot: str | None = None
    professional_license_snapshot: str | None = None
    amends_id: uuid.UUID | None = None
    amend_reason: str | None = None
    occurred_at: datetime | None = None
    reason: str | None
    evolution: str | None
    diagnosis: str | None
    indications: str | None
    status: ConsultationStatus
    created_by: uuid.UUID
    updated_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConsultationListItem(BaseModel):
    id: uuid.UUID
    appointment_id: uuid.UUID | None = None
    professional_id: uuid.UUID
    professional_name: str | None = None
    appointment_start_at: datetime | None = None
    amends_id: uuid.UUID | None = None
    amend_reason: str | None = None
    occurred_at: datetime | None = None
    reason: str | None
    evolution: str | None = None
    diagnosis: str | None
    status: ConsultationStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PatientClinicalUpdate(BaseModel):
    medical_history: str | None = None
    allergies: str | None = None
    current_medications: str | None = None
    clinical_notes: str | None = None


class PatientClinicalResponse(BaseModel):
    patient_id: uuid.UUID
    medical_history: str | None
    allergies: str | None
    current_medications: str | None
    clinical_notes: str | None
    clinical_updated_by: uuid.UUID | None = None
    clinical_updated_by_name: str | None = None
    clinical_updated_at: datetime | None = None

    model_config = {"from_attributes": True}
