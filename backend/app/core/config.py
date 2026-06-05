from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # WhatsApp: disabled ($0) | mock (logs) | twilio | meta (de pago)
    whatsapp_provider: str = "disabled"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""
    meta_whatsapp_token: str = ""
    meta_whatsapp_phone_number_id: str = ""

    public_app_url: str = "http://localhost:5173"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
