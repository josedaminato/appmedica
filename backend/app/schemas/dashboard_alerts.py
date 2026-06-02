import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


class UnclosedAppointmentsAlert(BaseModel):
    count: int


class OverdueAppointmentsAlert(BaseModel):
    count: int


class PartialPaymentsAlert(BaseModel):
    count: int
    pending_total: Decimal = Field(description="Suma de saldos pendientes (particular)")


class OldInsuranceClaimsByInsurance(BaseModel):
    health_insurance_id: uuid.UUID
    name: str
    claims_count: int
    debt_total: Decimal
    avg_days_pending: float


class OldInsuranceClaimsAlert(BaseModel):
    threshold_days: int
    items: list[OldInsuranceClaimsByInsurance]


class TopDebtPatient(BaseModel):
    patient_id: uuid.UUID
    patient_name: str
    total_debt: Decimal
    private_debt: Decimal
    insurance_debt: Decimal


class TopDebtPatientsAlert(BaseModel):
    items: list[TopDebtPatient]


class DashboardAlerts(BaseModel):
    unclosed_attended: UnclosedAppointmentsAlert
    overdue_unresolved: OverdueAppointmentsAlert
    partial_payments_pending: PartialPaymentsAlert
    old_insurance_claims: OldInsuranceClaimsAlert
    top_debt_patients: TopDebtPatientsAlert
