import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class PatientBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    dni: str = Field(min_length=7, max_length=20)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    birth_date: date | None = None
    health_insurance_id: uuid.UUID | None = None
    affiliate_number: str | None = Field(default=None, max_length=50)
    notes: str | None = None
    is_active: bool = True


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    dni: str | None = Field(default=None, min_length=7, max_length=20)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    birth_date: date | None = None
    health_insurance_id: uuid.UUID | None = None
    affiliate_number: str | None = Field(default=None, max_length=50)
    notes: str | None = None
    is_active: bool | None = None


class PatientResponse(PatientBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
