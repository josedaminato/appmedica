import asyncio
import hashlib
import logging
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import bad_request, conflict, unauthorized
from app.integrations.reminders.base import ReminderPayload
from app.integrations.reminders.factory import get_email_provider
from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import UserRole
from app.models.organization import Organization
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower().strip())
    slug = slug.strip("-") or "consultorio"
    return f"{slug}-{secrets.token_hex(3)}"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.orgs = OrganizationRepository(db)
        self.reset_tokens = PasswordResetRepository(db)

    def register(self, data: RegisterRequest) -> AuthResponse:
        email = data.email.lower()
        if self.users.get_by_email(email):
            raise conflict("El email ya está registrado")

        org = Organization(name=data.organization_name, slug=_slugify(data.organization_name))
        self.orgs.create(org)

        user = User(
            organization_id=org.id,
            email=email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            role=UserRole.OWNER,
            is_active=True,
        )
        self.users.create(user)
        self.db.commit()
        self.db.refresh(user)

        token = create_access_token(
            str(user.id),
            extra_claims={"organization_id": str(org.id), "role": user.role.value},
        )
        return AuthResponse(
            user=UserResponse.model_validate(user),
            access_token=token,
        )

    def login(self, data: LoginRequest) -> AuthResponse:
        user = self.users.get_by_email(data.email.lower())
        if not user or not verify_password(data.password, user.password_hash):
            raise unauthorized("Email o contraseña incorrectos")
        if not user.is_active:
            raise unauthorized("Usuario inactivo")

        token = create_access_token(
            str(user.id),
            extra_claims={
                "organization_id": str(user.organization_id),
                "role": user.role.value,
            },
        )
        return AuthResponse(
            user=UserResponse.model_validate(user),
            access_token=token,
        )

    def forgot_password(self, data: ForgotPasswordRequest) -> str:
        user = self.users.get_by_email(data.email.lower())
        message = "Si el email existe, recibirás instrucciones para restablecer la contraseña."

        if not user:
            return message

        raw_token = secrets.token_urlsafe(32)
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        )
        self.reset_tokens.create(token)
        self.db.commit()

        settings = get_settings()
        reset_url = f"{settings.public_app_url.rstrip('/')}/reset-password?token={raw_token}"
        body = (
            f"Hola {user.full_name},\n\n"
            f"Recibimos una solicitud para restablecer tu contraseña en {settings.app_name}.\n"
            f"Abrí este enlace (válido 2 horas):\n{reset_url}\n\n"
            "Si no pediste esto, ignorá el mensaje."
        )
        email_payload = ReminderPayload(
            patient_name=user.full_name,
            message=body,
            email=user.email,
            subject=f"{settings.app_name} — Restablecer contraseña",
        )
        provider = (settings.email_provider or "mock").lower()
        try:
            asyncio.run(get_email_provider(settings).send(email_payload))
        except Exception:
            logger.exception("No se pudo enviar email de reset a %s", user.email)
            if not settings.is_production:
                logger.warning(
                    "[DEV] Falló el envío de reset para %s. Revisá SMTP o usá EMAIL_PROVIDER=mock en desarrollo.",
                    user.email,
                )

        if provider == "mock" and not settings.is_production:
            logger.info(
                "[MOCK EMAIL] Password reset for %s | token: %s | expires: %s",
                user.email,
                raw_token,
                token.expires_at.isoformat(),
            )
        return message

    def reset_password(self, data: ResetPasswordRequest) -> TokenResponse:
        token_record = self.reset_tokens.get_valid_by_hash(_hash_token(data.token))
        if not token_record:
            raise bad_request("Token inválido o expirado")

        user = self.users.get_by_id(token_record.user_id)
        if not user:
            raise bad_request("Usuario no encontrado")

        user.password_hash = hash_password(data.new_password)
        token_record.used_at = datetime.now(timezone.utc)
        self.db.commit()

        access_token = create_access_token(
            str(user.id),
            extra_claims={
                "organization_id": str(user.organization_id),
                "role": user.role.value,
            },
        )
        return TokenResponse(access_token=access_token)

    def get_me(self, user_id: uuid.UUID) -> UserResponse:
        user = self.users.get_by_id(user_id)
        if not user:
            raise unauthorized("Usuario no encontrado")
        return UserResponse.model_validate(user)
