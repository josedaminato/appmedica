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
from app.core.ops_events import count_by_severity, list_events
from app.core.security import create_access_token, decode_access_token
from app.integrations.reminders.email_adapter import EmailReminderProvider
from app.models.appointment import Appointment
from app.models.enums import UserRole
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.common import MessageResponse
from app.schemas.platform import (
    PlatformAuthResponse,
    PlatformCheckResult,
    PlatformDashboardResponse,
    PlatformDiagnosticsResponse,
    PlatformLoginRequest,
    PlatformMarkPaidResponse,
    PlatformOpsEvent,
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

    def diagnostics(self) -> PlatformDiagnosticsResponse:
        """Chequeos de salud del producto para operar el SaaS sin SSH."""
        from datetime import datetime, timezone

        from sqlalchemy import text

        settings = get_settings()
        checks: list[PlatformCheckResult] = []

        # DB
        try:
            self.db.execute(text("SELECT 1"))
            checks.append(
                PlatformCheckResult(
                    key="database",
                    label="Base de datos",
                    status="ok",
                    message="PostgreSQL responde correctamente.",
                )
            )
        except Exception as exc:
            checks.append(
                PlatformCheckResult(
                    key="database",
                    label="Base de datos",
                    status="error",
                    message=f"No responde: {exc}",
                    action="Revisá el contenedor appmedica-db y docker compose ps.",
                )
            )

        # Email / SMTP
        provider = (settings.email_provider or "").lower()
        if provider != "smtp":
            checks.append(
                PlatformCheckResult(
                    key="email",
                    label="Email (recuperar contraseña)",
                    status="error",
                    message=f"EMAIL_PROVIDER={provider or '(vacío)'}. Debe ser smtp.",
                    action="En backend/.env.prod poné EMAIL_PROVIDER=smtp y redesplegá.",
                )
            )
        elif not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
            checks.append(
                PlatformCheckResult(
                    key="email",
                    label="Email (recuperar contraseña)",
                    status="error",
                    message="Faltan SMTP_HOST, SMTP_USER o SMTP_PASSWORD.",
                    action="Completá SMTP en backend/.env.prod (correo Hostinger) y redesplegá.",
                )
            )
        else:
            try:
                EmailReminderProvider(settings).verify_connection()
                checks.append(
                    PlatformCheckResult(
                        key="email",
                        label="Email (recuperar contraseña)",
                        status="ok",
                        message=f"SMTP OK ({settings.smtp_host}:{settings.smtp_port} como {settings.smtp_user}).",
                    )
                )
            except Exception as exc:
                checks.append(
                    PlatformCheckResult(
                        key="email",
                        label="Email (recuperar contraseña)",
                        status="error",
                        message=str(exc)[:300],
                        action="Verificá la clave del correo en hPanel → Email. Luego: bash scripts/test-smtp.sh tu@email.com",
                    )
                )

        # Registro público
        if settings.registration_enabled:
            checks.append(
                PlatformCheckResult(
                    key="registration",
                    label="Registro de consultorios",
                    status="ok",
                    message="Abierto: cualquiera puede crear cuenta en /register.",
                )
            )
        else:
            checks.append(
                PlatformCheckResult(
                    key="registration",
                    label="Registro de consultorios",
                    status="warn",
                    message="Cerrado: nadie puede auto-registrarse.",
                    action="Si querés altas públicas: REGISTRATION_ENABLED=true y redesplegá.",
                )
            )

        # URL pública (links de reset)
        public = (settings.public_app_url or "").rstrip("/")
        if public.startswith("https://") and "daminatoweb.com" in public:
            checks.append(
                PlatformCheckResult(
                    key="public_url",
                    label="URL pública (emails)",
                    status="ok",
                    message=f"PUBLIC_APP_URL={public}",
                )
            )
        else:
            checks.append(
                PlatformCheckResult(
                    key="public_url",
                    label="URL pública (emails)",
                    status="warn",
                    message=f"PUBLIC_APP_URL={public or '(vacío)'} — los links de reset pueden salir mal.",
                    action="Usá https://daminatoweb.com en producción.",
                )
            )

        # Panel ops credentials
        if settings.platform_admin_username and settings.platform_admin_password:
            checks.append(
                PlatformCheckResult(
                    key="ops_login",
                    label="Acceso panel Operación",
                    status="ok",
                    message="Credenciales PLATFORM_ADMIN configuradas.",
                )
            )
        else:
            checks.append(
                PlatformCheckResult(
                    key="ops_login",
                    label="Acceso panel Operación",
                    status="error",
                    message="Faltan PLATFORM_ADMIN_USERNAME / PLATFORM_ADMIN_PASSWORD.",
                    action="Definilas en backend/.env.prod.",
                )
            )

        counts = count_by_severity()
        recent = [
            PlatformOpsEvent(**e.to_dict())
            for e in list_events(limit=30)
            if e.severity in {"error", "warning"}
        ]

        statuses = {c.status for c in checks}
        if "error" in statuses or counts["error"] > 0:
            overall = "error"
        elif "warn" in statuses or counts["warning"] > 0:
            overall = "warn"
        else:
            overall = "ok"

        return PlatformDiagnosticsResponse(
            overall_status=overall,
            checked_at=datetime.now(timezone.utc),
            checks=checks,
            recent_errors=recent,
            error_count_window=counts["error"],
            warning_count_window=counts["warning"],
        )

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
