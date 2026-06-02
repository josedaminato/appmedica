import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.health_insurance import (
    HealthInsuranceCreate,
    HealthInsuranceResponse,
    HealthInsuranceUpdate,
)
from app.schemas.health_insurance_analytics import InsuranceRankingResponse
from app.services.health_insurance_analytics_service import HealthInsuranceAnalyticsService
from app.services.health_insurance_service import HealthInsuranceService

router = APIRouter(prefix="/health-insurances", tags=["health-insurances"])


@router.get("/ranking", response_model=InsuranceRankingResponse)
def get_insurance_ranking(
    current_user: CurrentUser,
    db: DbSession,
) -> InsuranceRankingResponse:
    return HealthInsuranceAnalyticsService(db).get_ranking(current_user.organization_id)


@router.get("", response_model=list[HealthInsuranceResponse])
def list_health_insurances(
    current_user: CurrentUser,
    db: DbSession,
    q: str | None = Query(None, max_length=100),
) -> list[HealthInsuranceResponse]:
    return HealthInsuranceService(db).list_insurances(current_user.organization_id, q=q)


@router.post("", response_model=HealthInsuranceResponse, status_code=status.HTTP_201_CREATED)
def create_health_insurance(
    data: HealthInsuranceCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> HealthInsuranceResponse:
    return HealthInsuranceService(db).create_insurance(current_user.organization_id, data)


@router.patch("/{insurance_id}", response_model=HealthInsuranceResponse)
def update_health_insurance(
    insurance_id: uuid.UUID,
    data: HealthInsuranceUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> HealthInsuranceResponse:
    return HealthInsuranceService(db).update_insurance(
        current_user.organization_id, insurance_id, data,
    )
