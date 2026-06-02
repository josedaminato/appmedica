import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, not_found
from app.models.appointment import Appointment
from app.models.enums import (
    AppointmentClosureStatus,
    AppointmentStatus,
    AttentionType,
    InsuranceClaimStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.models.insurance_claim import InsuranceClaim
from app.models.payment import Payment
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.health_insurance_repository import HealthInsuranceRepository
from app.repositories.insurance_claim_repository import InsuranceClaimRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.appointment import AddPaymentRequest, AppointmentResponse, CloseAppointmentRequest


class AppointmentClosureService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.appointments = AppointmentRepository(db)
        self.payments = PaymentRepository(db)
        self.claims = InsuranceClaimRepository(db)
        self.insurances = HealthInsuranceRepository(db)

    def close_appointment(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
        data: CloseAppointmentRequest,
        professional_id: uuid.UUID | None,
    ) -> AppointmentResponse:
        appointment = self.appointments.get_by_id(organization_id, appointment_id)
        if not appointment:
            raise not_found("Turno")
        if appointment.status != AppointmentStatus.ATTENDED:
            raise bad_request("Solo se puede cerrar administrativamente un turno marcado como asistió")
        if appointment.closure_status != AppointmentClosureStatus.NONE:
            raise bad_request("Este turno ya fue cerrado administrativamente")

        closure = data.closure_type
        if closure == AppointmentClosureStatus.NONE:
            raise bad_request("closure_type inválido")

        if closure == AppointmentClosureStatus.INSURANCE_PENDING:
            self._close_insurance(appointment, organization_id, data, professional_id)
        else:
            self._close_private(appointment, organization_id, data, professional_id, closure)

        self.db.commit()
        refreshed = self.appointments.get_by_id(organization_id, appointment_id)
        return AppointmentResponse.model_validate(refreshed)

    def _close_private(
        self,
        appointment: Appointment,
        organization_id: uuid.UUID,
        data: CloseAppointmentRequest,
        professional_id: uuid.UUID | None,
        closure: AppointmentClosureStatus,
    ) -> None:
        method = PaymentMethod.CASH
        if data.method:
            try:
                method = PaymentMethod(data.method)
            except ValueError as exc:
                raise bad_request("Método de pago inválido") from exc

        now = datetime.now(timezone.utc)
        prof = professional_id or appointment.professional_id

        if closure == AppointmentClosureStatus.PAID:
            self.payments.create(
                Payment(
                    organization_id=organization_id,
                    patient_id=appointment.patient_id,
                    appointment_id=appointment.id,
                    professional_id=prof,
                    amount=data.amount,
                    method=method,
                    status=PaymentStatus.PAID,
                    paid_at=now,
                    notes=data.notes,
                ),
            )
            appointment.closure_status = AppointmentClosureStatus.PAID

        elif closure == AppointmentClosureStatus.PENDING:
            self.payments.create(
                Payment(
                    organization_id=organization_id,
                    patient_id=appointment.patient_id,
                    appointment_id=appointment.id,
                    professional_id=prof,
                    amount=data.amount,
                    method=method,
                    status=PaymentStatus.PENDING,
                    notes=data.notes,
                ),
            )
            appointment.closure_status = AppointmentClosureStatus.PENDING

        elif closure == AppointmentClosureStatus.PARTIAL:
            paid_now = data.paid_amount or Decimal("0")
            if paid_now <= 0 or paid_now >= data.amount:
                raise bad_request("paid_amount debe ser mayor a 0 y menor al monto total")
            self.payments.create(
                Payment(
                    organization_id=organization_id,
                    patient_id=appointment.patient_id,
                    appointment_id=appointment.id,
                    professional_id=prof,
                    amount=paid_now,
                    method=method,
                    status=PaymentStatus.PAID,
                    paid_at=now,
                    notes=data.notes,
                ),
            )
            self.payments.create(
                Payment(
                    organization_id=organization_id,
                    patient_id=appointment.patient_id,
                    appointment_id=appointment.id,
                    professional_id=prof,
                    amount=data.amount - paid_now,
                    method=method,
                    status=PaymentStatus.PENDING,
                    notes="Saldo pendiente",
                ),
            )
            appointment.closure_status = AppointmentClosureStatus.PARTIAL

        appointment.expected_amount = data.amount
        self.appointments.update(appointment)

    def _close_insurance(
        self,
        appointment: Appointment,
        organization_id: uuid.UUID,
        data: CloseAppointmentRequest,
        professional_id: uuid.UUID | None,
    ) -> None:
        hi_id = data.health_insurance_id or appointment.health_insurance_id
        if not hi_id:
            raise bad_request("Obra social requerida")
        if not self.insurances.get_by_id(organization_id, hi_id):
            raise not_found("Obra social")

        claim = InsuranceClaim(
            organization_id=organization_id,
            patient_id=appointment.patient_id,
            appointment_id=appointment.id,
            health_insurance_id=hi_id,
            expected_amount=data.amount,
            service_date=appointment.start_at.date(),
            status=InsuranceClaimStatus.PENDING,
            notes=data.notes,
        )
        self.claims.create(claim)
        appointment.closure_status = AppointmentClosureStatus.INSURANCE_PENDING
        appointment.expected_amount = data.amount
        appointment.attention_type = AttentionType.HEALTH_INSURANCE
        appointment.health_insurance_id = hi_id
        self.appointments.update(appointment)

    def add_payment_to_appointment(
        self,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
        data: AddPaymentRequest,
        professional_id: uuid.UUID | None,
    ) -> AppointmentResponse:
        appointment = self.appointments.get_by_id(organization_id, appointment_id)
        if not appointment:
            raise not_found("Turno")
        if appointment.closure_status not in (
            AppointmentClosureStatus.PARTIAL,
            AppointmentClosureStatus.PENDING,
        ):
            raise bad_request("Este turno no admite pagos adicionales en su estado actual")

        try:
            method = PaymentMethod(data.method)
        except ValueError as exc:
            raise bad_request("Método de pago inválido") from exc

        now = datetime.now(timezone.utc)
        amount = Decimal(str(data.amount))
        remaining = amount

        pending_payments = [
            p for p in self.payments.list_by_appointment(appointment.id)
            if p.status == PaymentStatus.PENDING
        ]

        for pending in pending_payments:
            if remaining <= 0:
                break
            if remaining >= pending.amount:
                pending.status = PaymentStatus.PAID
                pending.paid_at = now
                remaining -= pending.amount
                self.payments.update(pending)
            else:
                pending.amount -= remaining
                self.payments.create(
                    Payment(
                        organization_id=organization_id,
                        patient_id=appointment.patient_id,
                        appointment_id=appointment.id,
                        professional_id=professional_id or appointment.professional_id,
                        amount=remaining,
                        method=method,
                        status=PaymentStatus.PAID,
                        paid_at=now,
                        notes=data.notes,
                    ),
                )
                remaining = Decimal("0")
                self.payments.update(pending)

        if remaining > 0 and not pending_payments:
            self.payments.create(
                Payment(
                    organization_id=organization_id,
                    patient_id=appointment.patient_id,
                    appointment_id=appointment.id,
                    professional_id=professional_id or appointment.professional_id,
                    amount=remaining,
                    method=method,
                    status=PaymentStatus.PAID,
                    paid_at=now,
                    notes=data.notes,
                ),
            )

        pending_left = self.payments.sum_pending_by_appointment(appointment.id)
        if pending_left <= 0:
            appointment.closure_status = AppointmentClosureStatus.PAID
        else:
            appointment.closure_status = AppointmentClosureStatus.PARTIAL

        self.appointments.update(appointment)
        self.db.commit()
        refreshed = self.appointments.get_by_id(organization_id, appointment_id)
        return AppointmentResponse.model_validate(refreshed)
