from decimal import Decimal

from pydantic import BaseModel

from app.schemas.appointment import AppointmentResponse


class DashboardSummary(BaseModel):
    appointments_today: int
    unclosed_attended: int
    overdue_unresolved: int
    private_debt_total: Decimal
    insurance_debt_total: Decimal
    patients_with_debt: int
    pending_insurance_claims: int
    no_shows_last_30_days: int
    upcoming_appointments: list[AppointmentResponse]
