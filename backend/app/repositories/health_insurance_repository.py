import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.health_insurance import HealthInsurance
from app.repositories.base import BaseRepository


class HealthInsuranceRepository(BaseRepository[HealthInsurance]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, HealthInsurance)

    def _base(self, organization_id: uuid.UUID):
        return select(HealthInsurance).where(
            HealthInsurance.organization_id == organization_id,
            HealthInsurance.deleted_at.is_(None),
        )

    def get_by_id(self, organization_id: uuid.UUID, insurance_id: uuid.UUID) -> HealthInsurance | None:
        stmt = self._base(organization_id).where(HealthInsurance.id == insurance_id)
        return self.db.scalars(stmt).first()

    def list_all(self, organization_id: uuid.UUID, q: str | None = None) -> list[HealthInsurance]:
        stmt = self._base(organization_id).order_by(HealthInsurance.name.asc())
        if q:
            term = f"%{q.strip().lower()}%"
            stmt = stmt.where(func.lower(HealthInsurance.name).like(term))
        return list(self.db.scalars(stmt).all())

    def create(self, entity: HealthInsurance) -> HealthInsurance:
        self.db.add(entity)
        self.db.flush()
        return entity

    def update(self, entity: HealthInsurance) -> HealthInsurance:
        self.db.add(entity)
        self.db.flush()
        return entity
