import secrets
import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.billing import extend_paid_period, initial_paid_until, payment_status
from app.core.config import get_settings
from app.core.dependencies import DbSession
from app.core.exceptions import forbidden, not_found, unauthorized
from app.core.security import create_access_token, decode_access_token
from app.models.appointment import Appointment
from app.models.enums import UserRole
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.common import MessageResponse
from app.schemas.platform import (
    PlatformAuthResponse,
    PlatformDashboardResponse,
    PlatformLoginRequest,
    PlatformMarkPaidResponse,
    PlatformTenantRow,
)

PLATFORM_ADMIN_SUBJECT = "platform:admin"
PLATFORM_ADMIN_ROLE = "platform_admin"

platform_security = HTTPBearer(auto_error=False)


def require_platform_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(platform_security)],
) -> dict:
    if not credentials or not credentials.credentials:
        raise unauthorized("Token requerido")

    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise unauthorized("Token inválido") from exc

    if payload.get("sub") != PLATFORM_ADMIN_SUBJECT or payload.get("role") != PLATFORM_ADMIN_ROLE:
        raise forbidden("Acceso solo para operación interna")

    return payload


PlatformAdmin = Annotated[dict, Depends(require_platform_admin)]


class PlatformService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.orgs = OrganizationRepository(db)

    def login(self, data: PlatformLoginRequest) -> PlatformAuthResponse:
        settings = get_settings()
        if not settings.platform_admin_username or not settings.platform_admin_password:
            raise forbidden("Panel interno no configurado")

        if not secrets.compare_digest(data.username, settings.platform_admin_username):
            raise unauthorized("Usuario o contraseña incorrectos")

        if not secrets.compare_digest(data.password, settings.platform_admin_password):
            raise unauthorized("Usuario o contraseña incorrectos")

        token = create_access_token(
            PLATFORM_ADMIN_SUBJECT,
            extra_claims={"role": PLATFORM_ADMIN_ROLE},
        )
        return PlatformAuthResponse(access_token=token, username=data.username)

    def dashboard(self) -> PlatformDashboardResponse:
        orgs = self.db.scalars(select(Organization).order_by(Organization.created_at.desc())).all()
        rows: list[PlatformTenantRow] = []
        payments_due = 0
        due_soon = 0

        for org in orgs:
            row = self._tenant_row(org)
            rows.append(row)
            if row.payment_status in {"overdue", "due_today"}:
                payments_due += 1
            elif row.payment_status == "due_soon":
                due_soon += 1

        return PlatformDashboardResponse(
            total_clients=len(rows),
            payments_due=payments_due,
            due_soon=due_soon,
            tenants=rows,
        )

    def mark_paid(self, organization_id: uuid.UUID) -> PlatformMarkPaidResponse:
        org = self.orgs.get_by_id(organization_id)
        if not org:
            raise not_found("Consultorio no encontrado")

        org.paid_until = extend_paid_period(org.paid_until)
        self.db.commit()
        self.db.refresh(org)

        status, days = payment_status(org.paid_until)
        return PlatformMarkPaidResponse(
            id=org.id,
            paid_until=org.paid_until,
            payment_status=status,
            days_until_due=days,
        )

    def delete_tenant(self, organization_id: uuid.UUID) -> MessageResponse:
        org = self.orgs.get_by_id(organization_id)
        if not org:
            raise not_found("Consultorio no encontrado")

        name = org.name
        self.db.execute(delete(Organization).where(Organization.id == organization_id))
        self.db.commit()
        return MessageResponse(message=f"Consultorio «{name}» eliminado junto con sus usuarios y datos.")

    def _tenant_row(self, org: Organization) -> PlatformTenantRow:
        owner = self.db.scalar(
            select(User)
            .where(User.organization_id == org.id, User.role == UserRole.OWNER)
            .order_by(User.created_at.asc())
            .limit(1)
        )
        users_count = self.db.scalar(
            select(func.count()).select_from(User).where(User.organization_id == org.id)
        ) or 0
        patients_count = self.db.scalar(
            select(func.count()).select_from(Patient).where(Patient.organization_id == org.id)
        ) or 0
        appointments_count = self.db.scalar(
            select(func.count()).select_from(Appointment).where(Appointment.organization_id == org.id)
        ) or 0

        status, days = payment_status(org.paid_until)
        return PlatformTenantRow(
            id=org.id,
            name=org.name,
            owner_email=owner.email if owner else None,
            owner_name=owner.full_name if owner else None,
            service_started_at=org.service_started_at,
            paid_until=org.paid_until,
            monthly_fee=org.monthly_fee,
            payment_status=status,
            days_until_due=days,
            users_count=users_count,
            patients_count=patients_count,
            appointments_count=appointments_count,
        )


def organization_billing_kwargs() -> dict:
    from datetime import datetime, timezone

    from app.core.billing import DEFAULT_MONTHLY_FEE

    started = datetime.now(timezone.utc)
    return {
        "service_started_at": started,
        "paid_until": initial_paid_until(started),
        "monthly_fee": DEFAULT_MONTHLY_FEE,
    }
