import uuid

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.consultation import ConsultationAmendmentCreate, ConsultationResponse, ConsultationUpdate
from app.services.consultation_service import ConsultationService

router = APIRouter(prefix="/consultations", tags=["consultations"])


@router.get("/{consultation_id}", response_model=ConsultationResponse)
def get_consultation(
    consultation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> ConsultationResponse:
    return ConsultationService(db).get_consultation(
        current_user.organization_id,
        consultation_id,
        current_user,
    )


@router.patch("/{consultation_id}", response_model=ConsultationResponse)
def update_consultation(
    consultation_id: uuid.UUID,
    data: ConsultationUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> ConsultationResponse:
    return ConsultationService(db).update_consultation(
        current_user.organization_id,
        consultation_id,
        data,
        current_user,
    )


@router.post("/{consultation_id}/finalize", response_model=ConsultationResponse)
def finalize_consultation(
    consultation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> ConsultationResponse:
    return ConsultationService(db).finalize_consultation(
        current_user.organization_id,
        consultation_id,
        current_user,
    )


@router.post(
    "/{consultation_id}/amendments",
    response_model=ConsultationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_consultation_amendment(
    consultation_id: uuid.UUID,
    data: ConsultationAmendmentCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ConsultationResponse:
    return ConsultationService(db).create_amendment(
        current_user.organization_id,
        consultation_id,
        data,
        current_user,
    )
