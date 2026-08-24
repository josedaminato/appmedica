import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.timezone import local_day_bounds_utc, now_local, org_timezone
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.appointment import AppointmentResponse
from app.schemas.dashboard import DashboardSummary
from app.services.collections_service import CollectionsService


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.appointments = AppointmentRepository(db)
        self.payments = PaymentRepository(db)
        self.organizations = OrganizationRepository(db)
        self.collections = CollectionsService(db)

    def get_summary(
        self,
        organization_id: uuid.UUID,
        *,
        professional_id: uuid.UUID | None = None,
    ) -> DashboardSummary:
        now = datetime.now(timezone.utc)
        tz = org_timezone(self.organizations.get_by_id(organization_id))
        today_local = now_local(tz).date()
        day_start, day_end = local_day_bounds_utc(today_local, tz)
        since_30 = now - timedelta(days=30)

        upcoming = self.appointments.list_upcoming(
            organization_id, now, limit=5, professional_id=professional_id,
        )
        # Misma fuente y criterio que /payments/summary: el dashboard no puede
        # mostrar una deuda distinta a la que el usuario ve en Pagos.
        debts = self.collections.get_summary(
            organization_id, professional_id=professional_id,
        )

        return DashboardSummary(
            appointments_today=self.appointments.count_active_between(
                organization_id,
                start=day_start,
                end=day_end,
                professional_id=professional_id,
            ),
            unclosed_attended=self.appointments.count_unclosed_attended(
                organization_id, professional_id=professional_id,
            ),
            overdue_unresolved=self.appointments.count_overdue_unresolved(
                organization_id, now, professional_id=professional_id,
            ),
            upcoming_unconfirmed=self.appointments.count_upcoming_pending(
                organization_id, now, professional_id=professional_id,
            ),
            private_debt_total=debts.private_debt_total,
            insurance_debt_total=debts.insurance_debt_total,
            patients_with_debt=self._count_patients_with_debt(
                organization_id, professional_id,
            ),
            pending_insurance_claims=debts.pending_insurance_claims,
            no_shows_last_30_days=self.appointments.count_no_shows_since(
                organization_id, since_30, professional_id=professional_id,
            ),
            upcoming_appointments=[AppointmentResponse.model_validate(a) for a in upcoming],
        )

    def _count_patients_with_debt(
        self,
        organization_id: uuid.UUID,
        professional_id: uuid.UUID | None,
    ) -> int:
        if professional_id is None:
            return self.payments.count_patients_with_debt(organization_id)
        # Deuda particular atribuida por Appointment.professional_id (igual que la
        # solapa "particulares" de Pagos), no por quien registró el cobro.
        rows = self.collections.list_items(
            organization_id, "private", professional_id=professional_id,
        )
        return len({row.patient_id for row in rows})
