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


class PlatformCheckResult(BaseModel):
    key: str
    label: str
    status: str
    message: str
    action: str | None = None


class PlatformOpsEvent(BaseModel):
    id: str
    created_at: str
    severity: str
    source: str
    code: str
    message: str
    path: str | None = None
    detail: str | None = None


class PlatformDiagnosticsResponse(BaseModel):
    overall_status: str
    checked_at: datetime
    checks: list[PlatformCheckResult]
    recent_errors: list[PlatformOpsEvent]
    error_count_window: int
    warning_count_window: int
