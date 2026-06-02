import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class HealthInsuranceBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    coverage_percent: int | None = Field(default=None, ge=0, le=100)
    estimated_payment_days: int | None = Field(default=None, ge=0)
    notes: str | None = None


class HealthInsuranceCreate(HealthInsuranceBase):
    pass


class HealthInsuranceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    coverage_percent: int | None = Field(default=None, ge=0, le=100)
    estimated_payment_days: int | None = Field(default=None, ge=0)
    notes: str | None = None


class HealthInsuranceResponse(HealthInsuranceBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
