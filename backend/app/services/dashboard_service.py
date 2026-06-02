import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.insurance_claim_repository import InsuranceClaimRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.appointment import AppointmentResponse
from app.schemas.dashboard import DashboardSummary


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.appointments = AppointmentRepository(db)
        self.payments = PaymentRepository(db)
        self.claims = InsuranceClaimRepository(db)

    def get_summary(self, organization_id: uuid.UUID) -> DashboardSummary:
        now = datetime.now(timezone.utc)
        today = now.date()
        since_30 = now - timedelta(days=30)

        upcoming = self.appointments.list_upcoming(organization_id, now, limit=5)

        return DashboardSummary(
            appointments_today=self.appointments.count_today(organization_id, today),
            unclosed_attended=self.appointments.count_unclosed_attended(organization_id),
            overdue_unresolved=self.appointments.count_overdue_unresolved(organization_id, now),
            private_debt_total=self.payments.sum_private_debt(organization_id),
            insurance_debt_total=self.claims.sum_insurance_debt(organization_id),
            patients_with_debt=self.payments.count_patients_with_debt(organization_id),
            pending_insurance_claims=self.claims.count_pending(organization_id),
            no_shows_last_30_days=self.appointments.count_no_shows_since(
                organization_id, since_30,
            ),
            upcoming_appointments=[AppointmentResponse.model_validate(a) for a in upcoming],
        )
