from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "change-me-in-production"
DEFAULT_DB_PASSWORD = "appmedica_secret"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AppMedica API"
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://appmedica:appmedica_secret@localhost:5432/appmedica"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Registro público de nuevos consultorios desde /register
    registration_enabled: bool = True

    # Rate limiting (anti fuerza bruta en endpoints de autenticacion)
    rate_limit_enabled: bool = True
    rate_limit_login: str = "10/minute"
    rate_limit_register: str = "5/hour"
    rate_limit_password_reset: str = "5/minute"

    # Recordatorios de turnos
    reminders_enabled: bool = True
    reminder_hours_before: int = 24
    reminder_background_loop: bool = True
    reminder_processor_interval_seconds: int = 60

    # Email: mock (logs) | smtp (Hostinger/gratis) | disabled
    email_provider: str = "mock"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True
    # Si true (o puerto 465), usa SMTP_SSL. Si falla, el adapter prueba el otro modo.
    smtp_use_ssl: bool = False

    # WhatsApp: disabled ($0) | mock (logs) | twilio | meta (de pago)
    whatsapp_provider: str = "disabled"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""
    meta_whatsapp_token: str = ""
    meta_whatsapp_phone_number_id: str = ""

    public_app_url: str = "http://localhost:5173"

    # Panel interno del operador (clientes y cobros del SaaS)
    platform_admin_username: str = ""
    platform_admin_password: str = ""

    # Resumen diario por email (agenda del día siguiente)
    daily_agenda_digest_enabled: bool = True
    daily_agenda_digest_hour: int = 21
    daily_agenda_digest_minute: int = 0
    daily_agenda_digest_check_interval_seconds: int = 900

    # Feed iCal (suscripción Google Calendar / Outlook / Apple)
    calendar_feed_days_past: int = 7
    calendar_feed_days_future: int = 90

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @model_validator(mode="after")
    def _enforce_production_safety(self) -> "Settings":
        """En producción, rechaza arrancar con secretos por defecto o débiles.

        Critico al vender a múltiples clientes: un JWT_SECRET por defecto
        permitiría falsificar tokens y acceder a cualquier consultorio.
        """
        if not self.is_production:
            return self

        problems: list[str] = []
        if self.jwt_secret == DEFAULT_JWT_SECRET or len(self.jwt_secret) < 32:
            problems.append(
                "JWT_SECRET inseguro: configurá un valor único de >=32 caracteres "
                "(generá uno con: openssl rand -hex 32)."
            )
        if DEFAULT_DB_PASSWORD in self.database_url:
            problems.append(
                "DATABASE_URL usa la contraseña por defecto: definí una contraseña fuerte."
            )
        if "*" in self.cors_origins_list:
            problems.append("CORS_ORIGINS no debe ser '*' en producción.")
        if self.reminder_background_loop:
            problems.append(
                "REMINDER_BACKGROUND_LOOP debe ser false en producción; "
                "usá cron con scripts/process_reminders.py y scripts/send_daily_agenda.py."
            )

        email_provider = (self.email_provider or "").lower()
        if email_provider != "smtp":
            problems.append(
                "EMAIL_PROVIDER debe ser smtp en producción "
                "(sin eso no llegan recuperación de contraseña ni emails)."
            )
        else:
            if not self.smtp_host or not self.smtp_user or not self.smtp_password:
                problems.append(
                    "SMTP incompleto: configurá SMTP_HOST, SMTP_USER y SMTP_PASSWORD."
                )
            if not self.smtp_from_email:
                problems.append("SMTP_FROM_EMAIL vacío: usá el mismo correo del buzón (ej. contacto@daminatoweb.com).")
            if "CAMBIAR" in (self.smtp_password or ""):
                problems.append("SMTP_PASSWORD todavía tiene el valor de ejemplo (CAMBIAR...).")

        if problems:
            raise ValueError(
                "Configuración insegura para producción (APP_ENV=production):\n- "
                + "\n- ".join(problems)
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
