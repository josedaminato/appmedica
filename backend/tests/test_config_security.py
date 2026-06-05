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


def test_production_accepts_strong_config():
    settings = _settings()
    assert settings.is_production is True
    assert settings.jwt_secret == STRONG_SECRET


def test_development_allows_defaults():
    settings = Settings(_env_file=None, app_env="development")
    assert settings.is_production is False
    assert settings.jwt_secret == DEFAULT_JWT_SECRET
