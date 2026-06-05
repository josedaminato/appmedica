"""Tests de reglas RBAC (filtro por profesional)."""

from uuid import uuid4

import pytest

from types import SimpleNamespace

from app.core.rbac import (
    assert_can_access_appointment,
    assert_can_delete,
    assert_owner,
    forbidden,
    resolve_professional_filter,
)
from app.core.exceptions import AppException
from app.models.enums import UserRole
from app.models.user import User


def _user(role: UserRole) -> User:
    return User(
        id=uuid4(),
        organization_id=uuid4(),
        email=f"{role.value}@test.com",
        password_hash="x",
        full_name="Test",
        role=role,
        is_active=True,
    )


def test_resolve_professional_filter_owner_uses_request():
    owner = _user(UserRole.OWNER)
    requested = uuid4()
    assert resolve_professional_filter(owner, requested) == requested


def test_resolve_professional_filter_professional_locked():
    prof = _user(UserRole.PROFESSIONAL)
    other = uuid4()
    assert resolve_professional_filter(prof, other) == prof.id
    assert resolve_professional_filter(prof, None) == prof.id


def test_assert_owner_allows_owner():
    assert_owner(_user(UserRole.OWNER))


def test_assert_owner_blocks_staff():
    with pytest.raises(AppException) as exc:
        assert_owner(_user(UserRole.STAFF))
    assert exc.value.status_code == 403


def test_assert_can_delete_blocks_staff():
    with pytest.raises(AppException):
        assert_can_delete(_user(UserRole.STAFF))


def test_forbidden_message():
    err = forbidden("custom")
    assert err.detail["message"] == "custom"  # type: ignore[index]


def test_professional_can_access_own_appointment():
    prof = _user(UserRole.PROFESSIONAL)
    appt = SimpleNamespace(professional_id=prof.id)
    assert_can_access_appointment(prof, appt)  # no raise


def test_professional_cannot_access_other_appointment():
    prof = _user(UserRole.PROFESSIONAL)
    appt = SimpleNamespace(professional_id=uuid4())
    with pytest.raises(AppException) as exc:
        assert_can_access_appointment(prof, appt)
    assert exc.value.status_code == 403


def test_owner_can_access_any_appointment():
    owner = _user(UserRole.OWNER)
    appt = SimpleNamespace(professional_id=uuid4())
    assert_can_access_appointment(owner, appt)  # no raise


def test_staff_can_access_any_appointment():
    staff = _user(UserRole.STAFF)
    appt = SimpleNamespace(professional_id=uuid4())
    assert_can_access_appointment(staff, appt)  # no raise
