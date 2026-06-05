from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.organization import OrganizationSettingsResponse, OrganizationSettingsUpdate
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/settings", response_model=OrganizationSettingsResponse)
def get_organization_settings(
    current_user: CurrentUser,
    db: DbSession,
) -> OrganizationSettingsResponse:
    return OrganizationService(db).get_settings(current_user.organization_id)


@router.patch("/settings", response_model=OrganizationSettingsResponse)
def update_organization_settings(
    data: OrganizationSettingsUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> OrganizationSettingsResponse:
    return OrganizationService(db).update_settings(current_user, data)
