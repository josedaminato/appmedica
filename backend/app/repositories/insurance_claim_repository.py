import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import InsuranceClaimStatus
from app.models.health_insurance import HealthInsurance
from app.models.insurance_claim import InsuranceClaim
from app.models.patient import Patient
from app.repositories.base import BaseRepository


class InsuranceClaimRepository(BaseRepository[InsuranceClaim]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, InsuranceClaim)

    def get_by_id(self, organization_id: uuid.UUID, claim_id: uuid.UUID) -> InsuranceClaim | None:
        stmt = select(InsuranceClaim).where(
            InsuranceClaim.organization_id == organization_id,
            InsuranceClaim.id == claim_id,
        )
        return self.db.scalars(stmt).first()

    def get_with_details(
        self, organization_id: uuid.UUID, claim_id: uuid.UUID,
    ) -> tuple[InsuranceClaim, Patient, HealthInsurance] | None:
        stmt = (
            select(InsuranceClaim, Patient, HealthInsurance)
            .join(Patient, InsuranceClaim.patient_id == Patient.id)
            .join(HealthInsurance, InsuranceClaim.health_insurance_id == HealthInsurance.id)
            .where(
                InsuranceClaim.organization_id == organization_id,
                InsuranceClaim.id == claim_id,
            )
        )
        row = self.db.execute(stmt).first()
        if not row:
            return None
        return row[0], row[1], row[2]

    def get_by_appointment(self, appointment_id: uuid.UUID) -> InsuranceClaim | None:
        stmt = select(InsuranceClaim).where(InsuranceClaim.appointment_id == appointment_id)
        return self.db.scalars(stmt).first()

    def sum_insurance_debt(self, organization_id: uuid.UUID) -> Decimal:
        stmt = select(func.coalesce(func.sum(InsuranceClaim.expected_amount), 0)).where(
            InsuranceClaim.organization_id == organization_id,
            InsuranceClaim.status.in_([InsuranceClaimStatus.PENDING, InsuranceClaimStatus.INVOICED]),
        )
        return Decimal(str(self.db.scalar(stmt) or 0))

    def sum_patient_insurance_debt(self, organization_id: uuid.UUID, patient_id: uuid.UUID) -> Decimal:
        stmt = select(func.coalesce(func.sum(InsuranceClaim.expected_amount), 0)).where(
            InsuranceClaim.organization_id == organization_id,
            InsuranceClaim.patient_id == patient_id,
            InsuranceClaim.status.in_([InsuranceClaimStatus.PENDING, InsuranceClaimStatus.INVOICED]),
        )
        return Decimal(str(self.db.scalar(stmt) or 0))

    def count_pending(self, organization_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(InsuranceClaim).where(
            InsuranceClaim.organization_id == organization_id,
            InsuranceClaim.status.in_([InsuranceClaimStatus.PENDING, InsuranceClaimStatus.INVOICED]),
        )
        return self.db.scalar(stmt) or 0

    def list_paginated(
        self,
        organization_id: uuid.UUID,
        *,
        page: int,
        page_size: int,
        status: InsuranceClaimStatus | None = None,
        health_insurance_id: uuid.UUID | None = None,
        open_only: bool = False,
    ) -> tuple[list[tuple[InsuranceClaim, Patient, HealthInsurance]], int]:
        base = (
            select(InsuranceClaim, Patient, HealthInsurance)
            .join(Patient, InsuranceClaim.patient_id == Patient.id)
            .join(HealthInsurance, InsuranceClaim.health_insurance_id == HealthInsurance.id)
            .where(InsuranceClaim.organization_id == organization_id)
        )
        if status is not None:
            base = base.where(InsuranceClaim.status == status)
        elif open_only:
            base = base.where(
                InsuranceClaim.status.in_(
                    [InsuranceClaimStatus.PENDING, InsuranceClaimStatus.INVOICED],
                ),
            )
        if health_insurance_id is not None:
            base = base.where(InsuranceClaim.health_insurance_id == health_insurance_id)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = self.db.scalar(count_stmt) or 0

        stmt = (
            base.order_by(InsuranceClaim.service_date.desc(), InsuranceClaim.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list(self.db.execute(stmt).all())
        return rows, total

    def list_all_with_insurance(
        self, organization_id: uuid.UUID,
    ) -> list[tuple[InsuranceClaim, HealthInsurance]]:
        stmt = (
            select(InsuranceClaim, HealthInsurance)
            .join(HealthInsurance, InsuranceClaim.health_insurance_id == HealthInsurance.id)
            .where(InsuranceClaim.organization_id == organization_id)
            .order_by(InsuranceClaim.service_date.desc())
        )
        return list(self.db.execute(stmt).all())

    def sum_collected_between(
        self,
        organization_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> tuple[Decimal, int]:
        stmt = select(
            func.coalesce(func.sum(InsuranceClaim.expected_amount), 0),
            func.count(),
        ).where(
            InsuranceClaim.organization_id == organization_id,
            InsuranceClaim.status == InsuranceClaimStatus.COLLECTED,
            InsuranceClaim.collected_at.isnot(None),
            InsuranceClaim.collected_at >= start,
            InsuranceClaim.collected_at < end,
        )
        row = self.db.execute(stmt).one()
        return Decimal(str(row[0] or 0)), int(row[1] or 0)

    def count_by_service_date_range(
        self,
        organization_id: uuid.UUID,
        start_date: date,
        end_date_exclusive: date,
    ) -> int:
        stmt = select(func.count()).select_from(InsuranceClaim).where(
            InsuranceClaim.organization_id == organization_id,
            InsuranceClaim.service_date >= start_date,
            InsuranceClaim.service_date < end_date_exclusive,
        )
        return self.db.scalar(stmt) or 0

    def list_by_patient(
        self,
        organization_id: uuid.UUID,
        patient_id: uuid.UUID,
        *,
        open_only: bool = False,
        limit: int = 10,
    ) -> list[InsuranceClaim]:
        stmt = select(InsuranceClaim).where(
            InsuranceClaim.organization_id == organization_id,
            InsuranceClaim.patient_id == patient_id,
        )
        if open_only:
            stmt = stmt.where(
                InsuranceClaim.status.in_(
                    [InsuranceClaimStatus.PENDING, InsuranceClaimStatus.INVOICED],
                ),
            )
        stmt = stmt.order_by(InsuranceClaim.service_date.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())

    def create(self, claim: InsuranceClaim) -> InsuranceClaim:
        self.db.add(claim)
        self.db.flush()
        return claim

    def update(self, claim: InsuranceClaim) -> InsuranceClaim:
        self.db.add(claim)
        self.db.flush()
        return claim
