import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import not_found
from app.models.health_insurance import HealthInsurance
from app.repositories.health_insurance_repository import HealthInsuranceRepository
from app.schemas.health_insurance import (
    HealthInsuranceCreate,
    HealthInsuranceResponse,
    HealthInsuranceUpdate,
)


class HealthInsuranceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = HealthInsuranceRepository(db)

    def list_insurances(self, organization_id: uuid.UUID, q: str | None = None) -> list[HealthInsuranceResponse]:
        items = self.repo.list_all(organization_id, q=q)
        return [HealthInsuranceResponse.model_validate(i) for i in items]

    def get_insurance(self, organization_id: uuid.UUID, insurance_id: uuid.UUID) -> HealthInsuranceResponse:
        item = self.repo.get_by_id(organization_id, insurance_id)
        if not item:
            raise not_found("Obra social")
        return HealthInsuranceResponse.model_validate(item)

    def create_insurance(
        self,
        organization_id: uuid.UUID,
        data: HealthInsuranceCreate,
    ) -> HealthInsuranceResponse:
        entity = HealthInsurance(organization_id=organization_id, **data.model_dump())
        self.repo.create(entity)
        self.db.commit()
        return HealthInsuranceResponse.model_validate(entity)

    def update_insurance(
        self,
        organization_id: uuid.UUID,
        insurance_id: uuid.UUID,
        data: HealthInsuranceUpdate,
    ) -> HealthInsuranceResponse:
        entity = self.repo.get_by_id(organization_id, insurance_id)
        if not entity:
            raise not_found("Obra social")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(entity, field, value)
        self.repo.update(entity)
        self.db.commit()
        return HealthInsuranceResponse.model_validate(entity)
