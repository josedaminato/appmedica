import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.repositories.base import BaseRepository


class PatientRepository(BaseRepository[Patient]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Patient)

    def _base_query(self, organization_id: uuid.UUID):
        return select(Patient).where(
            Patient.organization_id == organization_id,
            Patient.deleted_at.is_(None),
        )

    def get_by_id(self, organization_id: uuid.UUID, patient_id: uuid.UUID) -> Patient | None:
        stmt = self._base_query(organization_id).where(Patient.id == patient_id)
        return self.db.scalars(stmt).first()

    def get_by_dni(self, organization_id: uuid.UUID, dni: str) -> Patient | None:
        stmt = self._base_query(organization_id).where(Patient.dni == dni)
        return self.db.scalars(stmt).first()

    def list_paginated(
        self,
        organization_id: uuid.UUID,
        *,
        page: int,
        page_size: int,
        q: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Patient], int]:
        base = self._base_query(organization_id)

        if is_active is not None:
            base = base.where(Patient.is_active == is_active)

        if q:
            term = f"%{q.strip().lower()}%"
            base = base.where(
                or_(
                    func.lower(Patient.first_name).like(term),
                    func.lower(Patient.last_name).like(term),
                    func.lower(Patient.dni).like(term),
                    func.lower(func.coalesce(Patient.phone, "")).like(term),
                    func.lower(func.coalesce(Patient.email, "")).like(term),
                )
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = self.db.scalar(count_stmt) or 0

        stmt = (
            base.order_by(Patient.last_name.asc(), Patient.first_name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self.db.scalars(stmt).all())
        return items, total

    def create(self, patient: Patient) -> Patient:
        self.db.add(patient)
        self.db.flush()
        return patient

    def update(self, patient: Patient) -> Patient:
        self.db.add(patient)
        self.db.flush()
        return patient
