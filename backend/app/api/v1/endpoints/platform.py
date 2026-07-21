import uuid

from fastapi import APIRouter, Request, status

from app.core.rate_limit import limiter, login_limit
from app.schemas.common import MessageResponse
from app.schemas.platform import (
    PlatformAuthResponse,
    PlatformDashboardResponse,
    PlatformDiagnosticsResponse,
    PlatformLoginRequest,
    PlatformMarkPaidResponse,
)
from app.services.platform_service import PlatformAdmin, PlatformService
from app.core.dependencies import DbSession

router = APIRouter(prefix="/platform", tags=["platform"])


@router.post("/login", response_model=PlatformAuthResponse)
@limiter.limit(login_limit)
def platform_login(request: Request, data: PlatformLoginRequest, db: DbSession) -> PlatformAuthResponse:
    return PlatformService(db).login(data)


@router.get("/dashboard", response_model=PlatformDashboardResponse)
def platform_dashboard(_admin: PlatformAdmin, db: DbSession) -> PlatformDashboardResponse:
    return PlatformService(db).dashboard()


@router.get("/diagnostics", response_model=PlatformDiagnosticsResponse)
def platform_diagnostics(_admin: PlatformAdmin, db: DbSession) -> PlatformDiagnosticsResponse:
    return PlatformService(db).diagnostics()


@router.post("/tenants/{organization_id}/mark-paid", response_model=PlatformMarkPaidResponse)
def platform_mark_paid(
    organization_id: uuid.UUID,
    _admin: PlatformAdmin,
    db: DbSession,
) -> PlatformMarkPaidResponse:
    return PlatformService(db).mark_paid(organization_id)


@router.delete("/tenants/{organization_id}", response_model=MessageResponse)
def platform_delete_tenant(
    organization_id: uuid.UUID,
    _admin: PlatformAdmin,
    db: DbSession,
) -> MessageResponse:
    return PlatformService(db).delete_tenant(organization_id)
