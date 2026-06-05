from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.enums import (
    AppointmentClosureStatus,
    AppointmentStatus,
    InsuranceClaimStatus,
)
from app.models.health_insurance import HealthInsurance
from app.models.insurance_claim import InsuranceClaim
from app.models.patient import Patient
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.insurance_claim_repository import InsuranceClaimRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.collections import CollectionRow, CollectionTab, CollectionsSummary

STATUS_LABELS_PRIVATE = {
    AppointmentClosureStatus.PENDING: "Pendiente de cobro",
    AppointmentClosureStatus.PARTIAL: "Cobro parcial",
    AppointmentClosureStatus.PAID: "Cobrado",
}

CLAIM_LABELS = {
    InsuranceClaimStatus.PENDING: "Pendiente",
    InsuranceClaimStatus.INVOICED: "Facturado",
    InsuranceClaimStatus.COLLECTED: "Cobrado",
    InsuranceClaimStatus.REJECTED: "Rechazado",
}


class CollectionsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.appointments = AppointmentRepository(db)
        self.payments = PaymentRepository(db)
        self.claims = InsuranceClaimRepository(db)

    def get_summary(
        self,
        organization_id: uuid.UUID,
        *,
        professional_id: uuid.UUID | None = None,
    ) -> CollectionsSummary:
        now = datetime.now(timezone.utc)
        today_start = datetime.combine(now.date(), datetime.min.time(), tzinfo=timezone.utc)
        today_end = today_start + timedelta(days=1)

        if professional_id is None:
            paid_total, paid_count = self.payments.sum_paid_between(
                organization_id, today_start, today_end,
            )
            return CollectionsSummary(
                private_debt_total=self.payments.sum_private_debt(organization_id),
                insurance_debt_total=self.claims.sum_insurance_debt(organization_id),
                payments_today_total=paid_total,
                payments_today_count=paid_count,
                pending_insurance_claims=self.claims.count_pending(organization_id),
                unclosed_attended=self.appointments.count_unclosed_attended(organization_id),
                overdue_unresolved=self.appointments.count_overdue_unresolved(organization_id, now),
            )

        private_rows = self._list_private_debt(organization_id, professional_id)
        private_debt = sum((Decimal(r.balance_pending) for r in private_rows), Decimal("0"))
        insurance_rows = self._list_insurance_open(organization_id, professional_id)
        insurance_debt = sum((Decimal(r.balance_pending) for r in insurance_rows), Decimal("0"))
        paid_total, paid_count = self.payments.sum_paid_between_for_professional(
            organization_id, professional_id, today_start, today_end,
        )
        pending_claims = len(insurance_rows)
        unclosed = self.appointments.count_unclosed_attended(
            organization_id, professional_id=professional_id,
        )
        overdue = self.appointments.count_overdue_unresolved(
            organization_id, now, professional_id=professional_id,
        )
        return CollectionsSummary(
            private_debt_total=private_debt,
            insurance_debt_total=insurance_debt,
            payments_today_total=paid_total,
            payments_today_count=paid_count,
            pending_insurance_claims=pending_claims,
            unclosed_attended=unclosed,
            overdue_unresolved=overdue,
        )

    def list_items(
        self,
        organization_id: uuid.UUID,
        tab: CollectionTab,
        *,
        professional_id: uuid.UUID | None = None,
    ) -> list[CollectionRow]:
        if tab == "private":
            return self._list_private_debt(organization_id, professional_id)
        if tab == "insurance":
            return self._list_insurance_open(organization_id, professional_id)
        if tab == "recent":
            return self._list_recent_payments(organization_id, professional_id)
        return self._list_all_pending(organization_id, professional_id)

    def _list_private_debt(
        self,
        organization_id: uuid.UUID,
        professional_id: uuid.UUID | None,
    ) -> list[CollectionRow]:
        stmt = (
            select(Appointment, Patient, User)
            .join(Patient, Appointment.patient_id == Patient.id)
            .outerjoin(User, Appointment.professional_id == User.id)
            .where(
                Appointment.organization_id == organization_id,
                Appointment.closure_status.in_(
                    [
                        AppointmentClosureStatus.PENDING,
                        AppointmentClosureStatus.PARTIAL,
                    ],
                ),
            )
            .order_by(Appointment.start_at.desc())
        )
        if professional_id:
            stmt = stmt.where(Appointment.professional_id == professional_id)

        rows: list[CollectionRow] = []
        today = date.today()
        for appt, patient, prof in self.db.execute(stmt).all():
            balance = self.payments.sum_pending_by_appointment(appt.id)
            if balance <= 0:
                continue
            paid = self.payments.sum_paid_by_appointment(appt.id)
            total = appt.expected_amount or (paid + balance)
            service_day = appt.start_at.date()
            rows.append(
                CollectionRow(
                    row_id=str(appt.id),
                    kind="private",
                    patient_id=patient.id,
                    patient_name=f"{patient.last_name}, {patient.first_name}",
                    professional_name=prof.full_name if prof else None,
                    appointment_id=appt.id,
                    service_date=service_day,
                    status_label=STATUS_LABELS_PRIVATE.get(
                        appt.closure_status, appt.closure_status.value,
                    ),
                    status_code=appt.closure_status.value,
                    payment_method=None,
                    total_amount=total,
                    balance_pending=balance,
                    days_pending=max(0, (today - service_day).days),
                    can_collect=True,
                    can_mark_insurance=False,
                ),
            )
        return rows

    def _list_insurance_open(
        self,
        organization_id: uuid.UUID,
        professional_id: uuid.UUID | None = None,
    ) -> list[CollectionRow]:
        stmt = (
            select(InsuranceClaim, Patient, HealthInsurance)
            .join(Patient, InsuranceClaim.patient_id == Patient.id)
            .join(HealthInsurance, InsuranceClaim.health_insurance_id == HealthInsurance.id)
            .outerjoin(Appointment, InsuranceClaim.appointment_id == Appointment.id)
            .where(
                InsuranceClaim.organization_id == organization_id,
                InsuranceClaim.status.in_(
                    [InsuranceClaimStatus.PENDING, InsuranceClaimStatus.INVOICED],
                ),
            )
            .order_by(InsuranceClaim.service_date.desc())
        )
        if professional_id:
            stmt = stmt.where(Appointment.professional_id == professional_id)
        today = date.today()
        rows: list[CollectionRow] = []
        for claim, patient, insurance in self.db.execute(stmt).all():
            rows.append(
                CollectionRow(
                    row_id=str(claim.id),
                    kind="insurance",
                    patient_id=patient.id,
                    patient_name=f"{patient.last_name}, {patient.first_name}",
                    professional_name=None,
                    appointment_id=claim.appointment_id,
                    service_date=claim.service_date,
                    health_insurance_name=insurance.name,
                    status_label=CLAIM_LABELS.get(claim.status, claim.status.value),
                    status_code=claim.status.value,
                    payment_method=None,
                    total_amount=claim.expected_amount,
                    balance_pending=claim.expected_amount,
                    days_pending=max(0, (today - claim.service_date).days),
                    can_collect=False,
                    can_mark_insurance=True,
                ),
            )
        return rows

    def _list_recent_payments(
        self,
        organization_id: uuid.UUID,
        professional_id: uuid.UUID | None = None,
    ) -> list[CollectionRow]:
        rows: list[CollectionRow] = []
        for payment, patient, prof in self.payments.list_recent_paid(
            organization_id, limit=50, professional_id=professional_id,
        ):
            paid_day = (
                payment.paid_at.date()
                if payment.paid_at
                else payment.created_at.date()
            )
            rows.append(
                CollectionRow(
                    row_id=str(payment.id),
                    kind="payment",
                    patient_id=patient.id,
                    patient_name=f"{patient.last_name}, {patient.first_name}",
                    professional_name=prof.full_name if prof else None,
                    appointment_id=payment.appointment_id,
                    service_date=paid_day,
                    status_label="Cobrado",
                    status_code="paid",
                    payment_method=payment.method.value,
                    total_amount=payment.amount,
                    balance_pending=Decimal("0"),
                    days_pending=0,
                    can_collect=False,
                    can_mark_insurance=False,
                ),
            )
        return rows

    def _list_all_pending(
        self,
        organization_id: uuid.UUID,
        professional_id: uuid.UUID | None,
    ) -> list[CollectionRow]:
        private_rows = self._list_private_debt(organization_id, professional_id)
        insurance_rows = self._list_insurance_open(organization_id, professional_id)
        combined = private_rows + insurance_rows
        combined.sort(key=lambda r: r.days_pending, reverse=True)
        return combined
