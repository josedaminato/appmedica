from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.core.dependencies import CurrentUser, DbSession
from app.services.export_service import ExportService

router = APIRouter(prefix="/exports", tags=["exports"])

ExportKind = Literal["patients", "payments", "claims", "debt"]
ExportFormat = Literal["xlsx", "csv"]


@router.get("/{resource}")
def export_resource(
    resource: ExportKind,
    current_user: CurrentUser,
    db: DbSession,
    format: ExportFormat = Query("xlsx", alias="format"),
) -> Response:
    service = ExportService(db)
    org_id = current_user.organization_id

    if resource == "patients":
        content, media, filename = service.export_patients(org_id, format)
    elif resource == "payments":
        content, media, filename = service.export_payments(org_id, format)
    elif resource == "claims":
        content, media, filename = service.export_claims(org_id, format)
    else:
        content, media, filename = service.export_debt(org_id, format)

    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
