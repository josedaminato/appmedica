"""Verifica que la app no arranque en produccion con secretos inseguros."""

import pytest

from app.core.config import DEFAULT_JWT_SECRET, Settings

STRONG_SECRET = "a" * 48
SAFE_DB_URL = "postgresql+psycopg://appmedica:Str0ng-Pass-9182@db:5432/appmedica"


def _settings(**overrides) -> Settings:
    base = dict(
        _env_file=None,
        app_env="production",
        jwt_secret=STRONG_SECRET,
        database_url=SAFE_DB_URL,
        cors_origins="https://app.daminatoweb.com",
    )
    base.update(overrides)
    return Settings(**base)


def test_production_rejects_default_jwt_secret():
    with pytest.raises(ValueError, match="JWT_SECRET"):
        _settings(jwt_secret=DEFAULT_JWT_SECRET)


def test_production_rejects_short_jwt_secret():
    with pytest.raises(ValueError, match="JWT_SECRET"):
        _settings(jwt_secret="too-short")


def test_production_rejects_default_db_password():
    with pytest.raises(ValueError, match="DATABASE_URL"):
        _settings(database_url="postgresql+psycopg://appmedica:appmedica_secret@db:5432/appmedica")


def test_production_rejects_wildcard_cors():
    with pytest.raises(ValueError, match="CORS"):
        _settings(cors_origins="*")


def test_production_rejects_background_reminder_loop():
    with pytest.raises(ValueError, match="REMINDER_BACKGROUND_LOOP"):
        _settings(reminder_background_loop=True)


def test_production_rejects_mock_email():
    with pytest.raises(ValueError, match="EMAIL_PROVIDER"):
        _settings(reminder_background_loop=False, email_provider="mock")


def test_production_rejects_incomplete_smtp():
    with pytest.raises(ValueError, match="SMTP"):
        _settings(
            reminder_background_loop=False,
            email_provider="smtp",
            smtp_host="smtp.hostinger.com",
            smtp_user="",
            smtp_password="",
        )


def test_production_accepts_strong_config():
    settings = _settings(
        reminder_background_loop=False,
        registration_enabled=True,
        email_provider="smtp",
        smtp_host="smtp.hostinger.com",
        smtp_user="contacto@daminatoweb.com",
        smtp_password="real-password-not-placeholder",
        smtp_from_email="contacto@daminatoweb.com",
    )
    assert settings.is_production is True
    assert settings.jwt_secret == STRONG_SECRET


def test_development_allows_defaults():
    settings = Settings(_env_file=None, app_env="development")
    assert settings.is_production is False
    assert settings.jwt_secret == DEFAULT_JWT_SECRET
