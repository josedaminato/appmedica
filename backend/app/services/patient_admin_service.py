import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import not_found
from app.models.enums import (
    AppointmentClosureStatus,
    AppointmentStatus,
    InsuranceClaimStatus,
    PaymentStatus,
)
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.insurance_claim_repository import InsuranceClaimRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.appointment import AppointmentResponse
from app.schemas.insurance_claim import InsuranceClaimResponse
from app.schemas.patient_admin import PatientAdminSummary, TimelineEvent
from app.schemas.payment import PaymentResponse


class PatientAdminService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.patients = PatientRepository(db)
        self.appointments = AppointmentRepository(db)
        self.payments = PaymentRepository(db)
        self.claims = InsuranceClaimRepository(db)

    def get_admin_summary(
        self,
        organization_id: uuid.UUID,
        patient_id: uuid.UUID,
    ) -> PatientAdminSummary:
        patient = self.patients.get_by_id(organization_id, patient_id)
        if not patient:
            raise not_found("Paciente")

        now = datetime.now(timezone.utc)
        since_30 = now - timedelta(days=30)

        private_debt = self.payments.sum_patient_debt(organization_id, patient_id)
        insurance_debt = self.claims.sum_patient_insurance_debt(organization_id, patient_id)

        upcoming = self.appointments.list_by_patient(
            organization_id, patient_id, upcoming_only=True, limit=5,
        )
        recent_appts = self.appointments.list_by_patient(
            organization_id, patient_id, upcoming_only=False, limit=10,
        )
        recent_payments = self.payments.list_by_patient(organization_id, patient_id, limit=5)
        pending_claims = self.claims.list_by_patient(
            organization_id, patient_id, open_only=True, limit=10,
        )

        timeline = self._build_timeline(recent_appts, recent_payments, pending_claims)

        return PatientAdminSummary(
            patient_id=patient_id,
            private_debt=private_debt,
            insurance_debt=insurance_debt,
            total_debt=private_debt + insurance_debt,
            no_show_count=self.appointments.count_no_shows(organization_id, patient_id),
            no_shows_last_30_days=self.appointments.count_no_shows_since(
                organization_id, since_30, patient_id,
            ),
            upcoming_appointments=[AppointmentResponse.model_validate(a) for a in upcoming],
            recent_appointments=[AppointmentResponse.model_validate(a) for a in recent_appts],
            recent_payments=[PaymentResponse.model_validate(p) for p in recent_payments],
            pending_claims=[InsuranceClaimResponse.model_validate(c) for c in pending_claims],
            timeline=timeline,
        )

    def _build_timeline(self, appointments, payments, claims) -> list[TimelineEvent]:
        events: list[TimelineEvent] = []

        status_labels = {
            AppointmentStatus.ATTENDED: "Asistió",
            AppointmentStatus.NO_SHOW: "Ausente",
            AppointmentStatus.CANCELLED: "Cancelado",
            AppointmentStatus.CONFIRMED: "Confirmado",
            AppointmentStatus.PENDING: "Pendiente",
        }
        closure_labels = {
            AppointmentClosureStatus.PAID: "Cobrado",
            AppointmentClosureStatus.PENDING: "Pendiente de cobro",
            AppointmentClosureStatus.PARTIAL: "Cobro parcial",
            AppointmentClosureStatus.INSURANCE_PENDING: "Obra social pendiente",
        }

        for a in appointments:
            title = status_labels.get(a.status, a.status.value)
            subtitle = None
            if a.status == AppointmentStatus.ATTENDED and a.closure_status != AppointmentClosureStatus.NONE:
                subtitle = closure_labels.get(a.closure_status, a.closure_status.value)
            events.append(
                TimelineEvent(
                    id=a.id,
                    event_type="appointment",
                    title=f"Turno — {title}",
                    subtitle=subtitle,
                    amount=a.expected_amount,
                    status=a.status.value,
                    occurred_at=a.start_at,
                ),
            )

        for p in payments:
            events.append(
                TimelineEvent(
                    id=p.id,
                    event_type="payment",
                    title=f"Pago — {p.method.value}",
                    subtitle=p.status.value,
                    amount=p.amount,
                    status=p.status.value,
                    occurred_at=p.paid_at or p.created_at,
                ),
            )

        for c in claims:
            events.append(
                TimelineEvent(
                    id=c.id,
                    event_type="insurance_claim",
                    title="Prestación obra social",
                    subtitle=c.status.value,
                    amount=c.expected_amount,
                    status=c.status.value,
                    occurred_at=datetime.combine(
                        c.service_date, datetime.min.time(), tzinfo=timezone.utc,
                    ),
                ),
            )

        events.sort(key=lambda e: e.occurred_at, reverse=True)
        return events[:20]
