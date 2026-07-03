import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PlatformLoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class PlatformAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class PlatformTenantRow(BaseModel):
    id: uuid.UUID
    name: str
    owner_email: str | None
    owner_name: str | None
    service_started_at: datetime
    paid_until: date | None
    monthly_fee: Decimal
    payment_status: str
    days_until_due: int | None
    users_count: int
    patients_count: int
    appointments_count: int


class PlatformDashboardResponse(BaseModel):
    total_clients: int
    payments_due: int
    due_soon: int
    tenants: list[PlatformTenantRow]


class PlatformMarkPaidResponse(BaseModel):
    id: uuid.UUID
    paid_until: date
    payment_status: str
    days_until_due: int | None
