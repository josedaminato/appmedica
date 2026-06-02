import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import PaymentMethod, PaymentStatus


class PaymentCreate(BaseModel):
    patient_id: uuid.UUID
    appointment_id: uuid.UUID | None = None
    amount: Decimal = Field(gt=0)
    method: PaymentMethod
    status: PaymentStatus = PaymentStatus.PAID
    notes: str | None = None


class PaymentResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    patient_id: uuid.UUID
    appointment_id: uuid.UUID | None
    professional_id: uuid.UUID | None
    amount: Decimal
    method: PaymentMethod
    status: PaymentStatus
    paid_at: datetime | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
