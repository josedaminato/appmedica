"""Forgot-password debe fallar visible si SMTP no puede enviar."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import AppException
from app.schemas.auth import ForgotPasswordRequest
from app.services.auth_service import AuthService


def test_forgot_password_raises_when_smtp_fails():
    user = MagicMock()
    user.id = uuid4()
    user.email = "owner@example.com"
    user.full_name = "Owner"

    db = MagicMock()
    service = AuthService(db)
    service.users.get_by_email = MagicMock(return_value=user)
    service.reset_tokens.create = MagicMock()

    mock_settings = MagicMock()
    mock_settings.public_app_url = "https://daminatoweb.com"
    mock_settings.app_name = "AppMedica"
    mock_settings.email_provider = "smtp"
    mock_settings.is_production = True

    mock_provider = MagicMock()
    mock_provider.send_sync.side_effect = RuntimeError("SMTP down")

    with (
        patch("app.services.auth_service.get_settings", return_value=mock_settings),
        patch("app.services.auth_service.get_email_provider", return_value=mock_provider),
    ):
        with pytest.raises(AppException) as exc:
            service.forgot_password(ForgotPasswordRequest(email="owner@example.com"))

    assert exc.value.status_code == 503
    assert "email" in exc.value.detail["message"].lower()
    db.commit.assert_called()


def test_forgot_password_unknown_email_is_silent():
    db = MagicMock()
    service = AuthService(db)
    service.users.get_by_email = MagicMock(return_value=None)
    service.reset_tokens = MagicMock()

    msg = service.forgot_password(ForgotPasswordRequest(email="nobody@example.com"))
    assert "email" in msg.lower()
    service.reset_tokens.create.assert_not_called()
