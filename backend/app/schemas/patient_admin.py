import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import AppointmentClosureStatus, AppointmentStatus
from app.schemas.appointment import AppointmentResponse
from app.schemas.insurance_claim import InsuranceClaimResponse
from app.schemas.payment import PaymentResponse


class TimelineEvent(BaseModel):
    id: uuid.UUID
    event_type: str
    title: str
    subtitle: str | None = None
    amount: Decimal | None = None
    status: str | None = None
    occurred_at: datetime


class PatientAdminSummary(BaseModel):
    patient_id: uuid.UUID
    private_debt: Decimal
    insurance_debt: Decimal
    total_debt: Decimal
    no_show_count: int
    no_shows_last_30_days: int
    upcoming_appointments: list[AppointmentResponse]
    recent_appointments: list[AppointmentResponse]
    recent_payments: list[PaymentResponse]
    pending_claims: list[InsuranceClaimResponse]
    timeline: list[TimelineEvent]
