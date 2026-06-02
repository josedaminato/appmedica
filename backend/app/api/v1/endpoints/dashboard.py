from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(current_user: CurrentUser, db: DbSession) -> DashboardSummary:
    return DashboardService(db).get_summary(current_user.organization_id)
