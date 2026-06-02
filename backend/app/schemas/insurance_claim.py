import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import InsuranceClaimStatus


class InsuranceClaimCreate(BaseModel):
    patient_id: uuid.UUID
    appointment_id: uuid.UUID | None = None
    health_insurance_id: uuid.UUID
    expected_amount: Decimal = Field(gt=0)
    service_date: date
    notes: str | None = None


class InsuranceClaimUpdate(BaseModel):
    status: InsuranceClaimStatus | None = None
    expected_amount: Decimal | None = Field(default=None, gt=0)
    invoiced_at: datetime | None = None
    collected_at: datetime | None = None
    notes: str | None = None


class InsuranceClaimResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    patient_id: uuid.UUID
    appointment_id: uuid.UUID | None
    health_insurance_id: uuid.UUID
    expected_amount: Decimal
    service_date: date
    status: InsuranceClaimStatus
    invoiced_at: datetime | None
    collected_at: datetime | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InsuranceClaimListItem(InsuranceClaimResponse):
    patient_name: str
    health_insurance_name: str
    days_since_service: int
    days_to_collect: int | None = None
    days_service_to_invoice: int | None = None
