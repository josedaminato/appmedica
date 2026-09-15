from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.core.dependencies import CurrentUser, DbSession
from app.core.rbac import resolve_professional_filter
from app.schemas.report import MonthlyReport
from app.services.export_service import ExportService
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])

ExportFormat = Literal["xlsx", "csv"]


@router.get("/monthly", response_model=MonthlyReport)
def get_monthly_report(
    current_user: CurrentUser,
    db: DbSession,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
) -> MonthlyReport:
    professional_id = resolve_professional_filter(current_user, None)
    return ReportService(db).get_monthly_report(
        current_user.organization_id, year, month, professional_id=professional_id,
    )


@router.get("/monthly/export")
def export_monthly_report(
    current_user: CurrentUser,
    db: DbSession,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    format: ExportFormat = Query("xlsx", alias="format"),
) -> Response:
    professional_id = resolve_professional_filter(current_user, None)
    content, media, filename = ExportService(db).export_monthly_report(
        current_user.organization_id, year, month, format, professional_id=professional_id,
    )
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
