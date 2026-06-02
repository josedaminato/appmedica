from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import (
    AppointmentClosureStatus,
    AppointmentStatus,
    InsuranceClaimStatus,
    PaymentStatus,
)
from app.models.health_insurance import HealthInsurance
from app.models.insurance_claim import InsuranceClaim
from app.models.patient import Patient
from app.models.payment import Payment
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.insurance_claim_repository import InsuranceClaimRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.dashboard_alerts import (
    DashboardAlerts,
    OldInsuranceClaimsAlert,
    OldInsuranceClaimsByInsurance,
    OverdueAppointmentsAlert,
    PartialPaymentsAlert,
    TopDebtPatient,
    TopDebtPatientsAlert,
    UnclosedAppointmentsAlert,
)


class DashboardAlertsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.appointments = AppointmentRepository(db)
        self.payments = PaymentRepository(db)
        self.claims = InsuranceClaimRepository(db)

    def get_alerts(
        self,
        organization_id: uuid.UUID,
        *,
        claims_old_days: int = 45,
        top_patients_limit: int = 5,
    ) -> DashboardAlerts:
        today = date.today()

        unclosed_count = self.appointments.count_unclosed_attended(organization_id)
        now = datetime.now(timezone.utc)
        overdue_count = self.appointments.count_overdue_unresolved(organization_id, now)

        partial_count, partial_pending_total = self._partial_payments_alert(organization_id)
        old_claims = self._old_claims_by_insurance(
            organization_id,
            threshold_days=claims_old_days,
        )
        top_patients = self._top_debt_patients(
            organization_id,
            limit=top_patients_limit,
        )

        return DashboardAlerts(
            unclosed_attended=UnclosedAppointmentsAlert(count=unclosed_count),
            overdue_unresolved=OverdueAppointmentsAlert(count=overdue_count),
            partial_payments_pending=PartialPaymentsAlert(
                count=partial_count,
                pending_total=partial_pending_total,
            ),
            old_insurance_claims=OldInsuranceClaimsAlert(
                threshold_days=claims_old_days,
                items=old_claims,
            ),
            top_debt_patients=TopDebtPatientsAlert(items=top_patients),
        )

    def _partial_payments_alert(self, organization_id: uuid.UUID) -> tuple[int, Decimal]:
        # appointment is pending/partial and has at least one pending Payment; compute distinct appointments + total pending
        from app.models.appointment import Appointment

        stmt = (
            select(
                func.count(func.distinct(Payment.appointment_id)),
                func.coalesce(func.sum(Payment.amount), 0),
            )
            .select_from(Payment)
            .join(
                Appointment,
                Payment.appointment_id == Appointment.id,
            )
            .where(
                Payment.organization_id == organization_id,
                Payment.status == PaymentStatus.PENDING,
                Appointment.organization_id == organization_id,
                Appointment.closure_status.in_(
                    [AppointmentClosureStatus.PENDING, AppointmentClosureStatus.PARTIAL],
                ),
            )
        )
        row = self.db.execute(stmt).one()
        return int(row[0] or 0), Decimal(str(row[1] or 0))

    def _old_claims_by_insurance(
        self,
        organization_id: uuid.UUID,
        *,
        threshold_days: int,
    ) -> list[OldInsuranceClaimsByInsurance]:
        cutoff = date.today() - timedelta(days=threshold_days)
        # group by insurance, count + sum + avg days pending
        # avg days pending computed in python (portable)
        stmt = (
            select(InsuranceClaim, HealthInsurance)
            .join(HealthInsurance, InsuranceClaim.health_insurance_id == HealthInsurance.id)
            .where(
                InsuranceClaim.organization_id == organization_id,
                InsuranceClaim.status.in_([InsuranceClaimStatus.PENDING, InsuranceClaimStatus.INVOICED]),
                InsuranceClaim.service_date <= cutoff,
            )
            .order_by(InsuranceClaim.service_date.asc())
        )
        grouped: dict[uuid.UUID, list[InsuranceClaim]] = defaultdict(list)
        names: dict[uuid.UUID, str] = {}
        for claim, ins in self.db.execute(stmt).all():
            grouped[claim.health_insurance_id].append(claim)
            names[claim.health_insurance_id] = ins.name

        items: list[OldInsuranceClaimsByInsurance] = []
        today = date.today()
        for insurance_id, claims in grouped.items():
            debt_total = sum((c.expected_amount for c in claims), Decimal("0"))
            days = [(today - c.service_date).days for c in claims]
            avg_days = float(sum(days) / len(days)) if days else 0.0
            items.append(
                OldInsuranceClaimsByInsurance(
                    health_insurance_id=insurance_id,
                    name=names.get(insurance_id, "Obra social"),
                    claims_count=len(claims),
                    debt_total=debt_total,
                    avg_days_pending=round(avg_days, 1),
                ),
            )

        items.sort(key=lambda x: (x.debt_total, x.claims_count), reverse=True)
        return items[:6]

    def _top_debt_patients(
        self,
        organization_id: uuid.UUID,
        *,
        limit: int,
    ) -> list[TopDebtPatient]:
        # private debt by patient
        private_stmt = (
            select(Patient.id, Patient.first_name, Patient.last_name, func.coalesce(func.sum(Payment.amount), 0))
            .join(Payment, Payment.patient_id == Patient.id)
            .where(
                Patient.organization_id == organization_id,
                Payment.organization_id == organization_id,
                Payment.status == PaymentStatus.PENDING,
            )
            .group_by(Patient.id)
        )
        private = {
            row[0]: Decimal(str(row[3] or 0))
            for row in self.db.execute(private_stmt).all()
        }

        # insurance debt by patient
        insurance_stmt = (
            select(Patient.id, func.coalesce(func.sum(InsuranceClaim.expected_amount), 0))
            .join(InsuranceClaim, InsuranceClaim.patient_id == Patient.id)
            .where(
                Patient.organization_id == organization_id,
                InsuranceClaim.organization_id == organization_id,
                InsuranceClaim.status.in_([InsuranceClaimStatus.PENDING, InsuranceClaimStatus.INVOICED]),
            )
            .group_by(Patient.id)
        )
        insurance = {
            row[0]: Decimal(str(row[1] or 0))
            for row in self.db.execute(insurance_stmt).all()
        }

        combined_ids = set(private.keys()) | set(insurance.keys())
        if not combined_ids:
            return []

        patients_stmt = (
            select(Patient.id, Patient.first_name, Patient.last_name)
            .where(
                Patient.organization_id == organization_id,
                Patient.id.in_(list(combined_ids)),
            )
        )
        names = {
            row[0]: f"{row[2]}, {row[1]}"
            for row in self.db.execute(patients_stmt).all()
        }

        items = []
        for pid in combined_ids:
            p_debt = private.get(pid, Decimal("0"))
            i_debt = insurance.get(pid, Decimal("0"))
            total = p_debt + i_debt
            if total <= 0:
                continue
            items.append(
                TopDebtPatient(
                    patient_id=pid,
                    patient_name=names.get(pid, "Paciente"),
                    total_debt=total,
                    private_debt=p_debt,
                    insurance_debt=i_debt,
                ),
            )
        items.sort(key=lambda x: x.total_debt, reverse=True)
        return items[:limit]
