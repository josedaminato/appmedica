import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import PaymentStatus
from app.models.patient import Patient
from app.models.payment import Payment
from app.models.user import User
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Payment)

    def get_by_id(self, organization_id: uuid.UUID, payment_id: uuid.UUID) -> Payment | None:
        stmt = select(Payment).where(
            Payment.organization_id == organization_id,
            Payment.id == payment_id,
        )
        return self.db.scalars(stmt).first()

    def sum_paid_by_appointment(self, appointment_id: uuid.UUID) -> Decimal:
        stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.appointment_id == appointment_id,
            Payment.status == PaymentStatus.PAID,
        )
        return Decimal(str(self.db.scalar(stmt) or 0))

    def sum_pending_by_appointment(self, appointment_id: uuid.UUID) -> Decimal:
        stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.appointment_id == appointment_id,
            Payment.status == PaymentStatus.PENDING,
        )
        return Decimal(str(self.db.scalar(stmt) or 0))

    def sum_private_debt(self, organization_id: uuid.UUID) -> Decimal:
        """Solo pagos pendientes = deuda real (lo cobrado no cuenta)."""
        stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.organization_id == organization_id,
            Payment.status == PaymentStatus.PENDING,
        )
        return Decimal(str(self.db.scalar(stmt) or 0))

    def sum_patient_debt(self, organization_id: uuid.UUID, patient_id: uuid.UUID) -> Decimal:
        stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.organization_id == organization_id,
            Payment.patient_id == patient_id,
            Payment.status == PaymentStatus.PENDING,
        )
        return Decimal(str(self.db.scalar(stmt) or 0))

    def count_patients_with_debt(self, organization_id: uuid.UUID) -> int:
        stmt = select(func.count(func.distinct(Payment.patient_id))).where(
            Payment.organization_id == organization_id,
            Payment.status == PaymentStatus.PENDING,
        )
        return self.db.scalar(stmt) or 0

    def list_by_patient(
        self,
        organization_id: uuid.UUID,
        patient_id: uuid.UUID,
        limit: int = 10,
    ) -> list[Payment]:
        stmt = (
            select(Payment)
            .where(
                Payment.organization_id == organization_id,
                Payment.patient_id == patient_id,
            )
            .order_by(Payment.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def sum_paid_between(
        self,
        organization_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> tuple[Decimal, int]:
        stmt = select(
            func.coalesce(func.sum(Payment.amount), 0),
            func.count(),
        ).where(
            Payment.organization_id == organization_id,
            Payment.status == PaymentStatus.PAID,
            Payment.paid_at.isnot(None),
            Payment.paid_at >= start,
            Payment.paid_at < end,
        )
        row = self.db.execute(stmt).one()
        return Decimal(str(row[0] or 0)), int(row[1] or 0)

    def sum_paid_between_for_professional(
        self,
        organization_id: uuid.UUID,
        professional_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> tuple[Decimal, int]:
        stmt = select(
            func.coalesce(func.sum(Payment.amount), 0),
            func.count(),
        ).where(
            Payment.organization_id == organization_id,
            Payment.professional_id == professional_id,
            Payment.status == PaymentStatus.PAID,
            Payment.paid_at.isnot(None),
            Payment.paid_at >= start,
            Payment.paid_at < end,
        )
        row = self.db.execute(stmt).one()
        return Decimal(str(row[0] or 0)), int(row[1] or 0)

    def list_recent_paid(
        self,
        organization_id: uuid.UUID,
        *,
        limit: int = 50,
        professional_id: uuid.UUID | None = None,
    ) -> list[tuple[Payment, Patient, User | None]]:
        stmt = (
            select(Payment, Patient, User)
            .join(Patient, Payment.patient_id == Patient.id)
            .outerjoin(User, Payment.professional_id == User.id)
            .where(
                Payment.organization_id == organization_id,
                Payment.status == PaymentStatus.PAID,
            )
            .order_by(Payment.paid_at.desc().nullslast(), Payment.created_at.desc())
            .limit(limit)
        )
        if professional_id:
            stmt = stmt.where(Payment.professional_id == professional_id)
        return list(self.db.execute(stmt).all())

    def list_by_appointment(self, appointment_id: uuid.UUID) -> list[Payment]:
        stmt = select(Payment).where(Payment.appointment_id == appointment_id).order_by(
            Payment.created_at.asc(),
        )
        return list(self.db.scalars(stmt).all())

    def create(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.flush()
        return payment

    def update(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.flush()
        return payment
