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


class PatientPendingPayment(BaseModel):
    payment_id: uuid.UUID
    appointment_id: uuid.UUID | None
    amount: Decimal
    appointment_start_at: datetime | None = None
    professional_name: str | None = None
    created_at: datetime


class PatientOpenClaim(InsuranceClaimResponse):
    health_insurance_name: str


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
    pending_private_payments: list[PatientPendingPayment]
    pending_claims: list[PatientOpenClaim]
    timeline: list[TimelineEvent]
