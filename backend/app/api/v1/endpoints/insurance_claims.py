import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DbSession
from app.models.enums import InsuranceClaimStatus
from app.schemas.common import PaginatedResponse
from app.schemas.insurance_claim import InsuranceClaimListItem, InsuranceClaimUpdate
from app.services.insurance_claim_service import InsuranceClaimService

router = APIRouter(prefix="/insurance-claims", tags=["insurance-claims"])


@router.get("", response_model=PaginatedResponse[InsuranceClaimListItem])
def list_insurance_claims(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: InsuranceClaimStatus | None = Query(None),
    health_insurance_id: uuid.UUID | None = Query(None),
    open_only: bool = Query(False),
) -> PaginatedResponse[InsuranceClaimListItem]:
    return InsuranceClaimService(db).list_claims(
        current_user.organization_id,
        page=page,
        page_size=page_size,
        status=status,
        health_insurance_id=health_insurance_id,
        open_only=open_only,
    )


@router.get("/{claim_id}", response_model=InsuranceClaimListItem)
def get_insurance_claim(
    claim_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> InsuranceClaimListItem:
    return InsuranceClaimService(db).get_claim(current_user.organization_id, claim_id)


@router.patch("/{claim_id}", response_model=InsuranceClaimListItem)
def update_insurance_claim(
    claim_id: uuid.UUID,
    data: InsuranceClaimUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> InsuranceClaimListItem:
    return InsuranceClaimService(db).update_claim(
        current_user.organization_id,
        claim_id,
        data,
    )
