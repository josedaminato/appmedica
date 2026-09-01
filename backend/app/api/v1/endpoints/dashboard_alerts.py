from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DbSession
from app.core.rbac import resolve_professional_filter
from app.schemas.dashboard_alerts import DashboardAlerts
from app.services.dashboard_alerts_service import DashboardAlertsService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/alerts", response_model=DashboardAlerts)
def get_dashboard_alerts(
    current_user: CurrentUser,
    db: DbSession,
    claims_old_days: int = Query(45, ge=7, le=365),
) -> DashboardAlerts:
    prof_filter = resolve_professional_filter(current_user, None)
    return DashboardAlertsService(db).get_alerts(
        current_user.organization_id,
        claims_old_days=claims_old_days,
        professional_id=prof_filter,
    )
