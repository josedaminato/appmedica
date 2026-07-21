import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import (
    AppointmentClosureStatus,
    AppointmentModality,
    AppointmentStatus,
    AttentionType,
)


class AppointmentBase(BaseModel):
    patient_id: uuid.UUID
    professional_id: uuid.UUID | None = None
    start_at: datetime
    end_at: datetime
    modality: AppointmentModality = AppointmentModality.IN_PERSON
    attention_type: AttentionType = AttentionType.PRIVATE
    expected_amount: Decimal | None = Field(default=None, ge=0)
    health_insurance_id: uuid.UUID | None = None
    notes: str | None = None


class AppointmentCreate(AppointmentBase):
    """Si recurring_weekly=True, genera turnos cada 7 días (incluye el primero)."""

    recurring_weekly: bool = False
    weeks: int = Field(default=12, ge=1, le=52)


class AppointmentUpdate(BaseModel):
    patient_id: uuid.UUID | None = None
    professional_id: uuid.UUID | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    modality: AppointmentModality | None = None
    attention_type: AttentionType | None = None
    expected_amount: Decimal | None = Field(default=None, ge=0)
    health_insurance_id: uuid.UUID | None = None
    notes: str | None = None


class PatientBrief(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    dni: str
    phone: str | None = None

    model_config = {"from_attributes": True}


class ProfessionalBrief(BaseModel):
    id: uuid.UUID
    full_name: str

    model_config = {"from_attributes": True}


class HealthInsuranceBrief(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class AppointmentResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    patient_id: uuid.UUID
    professional_id: uuid.UUID | None
    health_insurance_id: uuid.UUID | None
    rescheduled_to_id: uuid.UUID | None
    series_id: uuid.UUID | None = None
    start_at: datetime
    end_at: datetime
    status: AppointmentStatus
    modality: AppointmentModality
    attention_type: AttentionType
    expected_amount: Decimal | None
    closure_status: AppointmentClosureStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
    patient: PatientBrief | None = None
    professional: ProfessionalBrief | None = None
    health_insurance: HealthInsuranceBrief | None = None

    model_config = {"from_attributes": True}


class AppointmentCreateResult(BaseModel):
    created_count: int
    series_id: uuid.UUID | None = None
    appointments: list[AppointmentResponse]


class AppointmentRescheduleRequest(BaseModel):
    start_at: datetime
    end_at: datetime
    professional_id: uuid.UUID | None = None
    notes: str | None = None


class CloseAppointmentRequest(BaseModel):
    """Cierre administrativo tras marcar asistió."""

    closure_type: AppointmentClosureStatus = Field(
        description="paid | pending | partial | insurance_pending",
    )
    amount: Decimal = Field(gt=0, description="Monto total esperado del turno")
    method: str | None = Field(default=None, description="cash|transfer|mercadopago para pagos")
    paid_amount: Decimal | None = Field(
        default=None,
        ge=0,
        description="Monto cobrado ahora (parcial o total)",
    )
    health_insurance_id: uuid.UUID | None = None
    notes: str | None = None


class AddPaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    method: str
    notes: str | None = None
