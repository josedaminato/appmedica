"""Registro público deshabilitado."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    return TestClient(app)


def test_register_disabled_returns_403(client, monkeypatch):
    monkeypatch.setenv("REGISTRATION_ENABLED", "false")
    get_settings.cache_clear()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Test Org",
            "full_name": "Test User",
            "email": "disabled-reg@example.com",
            "password": "testpass123",
        },
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "FORBIDDEN"
    get_settings.cache_clear()


def test_register_enabled_by_default(client, monkeypatch):
    monkeypatch.delenv("REGISTRATION_ENABLED", raising=False)
    get_settings.cache_clear()

    settings = Settings(_env_file=None, app_env="development")
    assert settings.registration_enabled is True
    get_settings.cache_clear()
