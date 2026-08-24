from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.core.rbac import resolve_professional_filter
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(current_user: CurrentUser, db: DbSession) -> DashboardSummary:
    prof_filter = resolve_professional_filter(current_user, None)
    return DashboardService(db).get_summary(
        current_user.organization_id, professional_id=prof_filter,
    )
