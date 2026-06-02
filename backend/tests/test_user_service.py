"""Tests del servicio de gestión de usuarios."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import AppException
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import CreateUserRequest, UpdateUserRequest
from app.services.user_service import UserService


def _user(
    *,
    role: UserRole = UserRole.OWNER,
    user_id: uuid.UUID | None = None,
    org_id: uuid.UUID | None = None,
    is_active: bool = True,
) -> User:
    return User(
        id=user_id or uuid.uuid4(),
        organization_id=org_id or uuid.uuid4(),
        email="owner@test.com",
        password_hash="hash",
        full_name="Owner Test",
        role=role,
        is_active=is_active,
    )


@pytest.fixture
def db():
    return MagicMock()


def test_create_member_as_owner(db):
    owner = _user(role=UserRole.OWNER)
    service = UserService(db)
    service.users.get_by_email = MagicMock(return_value=None)
    service.users.create = MagicMock(side_effect=lambda u: u)

    created = User(
        id=uuid.uuid4(),
        organization_id=owner.organization_id,
        email="pro@test.com",
        password_hash="x",
        full_name="Dr. Pro",
        role=UserRole.PROFESSIONAL,
        is_active=True,
    )
    db.commit = MagicMock()
    db.refresh = MagicMock(side_effect=lambda u: setattr(u, "id", created.id))

    def fake_create(user):
        user.id = created.id
        user.created_at = datetime.now(timezone.utc)
        return user

    service.users.create = MagicMock(side_effect=fake_create)
    db.refresh = MagicMock(side_effect=lambda u: None)

    result = service.create_member(
        owner,
        CreateUserRequest(
            full_name="Dr. Pro",
            email="pro@test.com",
            password="password123",
            role=UserRole.PROFESSIONAL,
        ),
    )

    assert result.email == "pro@test.com"
    assert result.role == UserRole.PROFESSIONAL
    db.commit.assert_called_once()


def test_create_member_rejects_non_owner(db):
    staff = _user(role=UserRole.STAFF)
    service = UserService(db)

    with pytest.raises(AppException) as exc:
        service.create_member(
            staff,
            CreateUserRequest(
                full_name="Nuevo",
                email="n@test.com",
                password="password123",
                role=UserRole.STAFF,
            ),
        )
    assert exc.value.status_code == 403


def test_cannot_deactivate_self(db):
    owner = _user(role=UserRole.OWNER)
    service = UserService(db)
    service.users.get_by_id_in_organization = MagicMock(return_value=owner)

    with pytest.raises(AppException) as exc:
        service.update_member(owner, owner.id, UpdateUserRequest(is_active=False))
    assert exc.value.status_code == 400


def test_cannot_deactivate_last_owner(db):
    owner = _user(role=UserRole.OWNER)
    other = _user(role=UserRole.OWNER, user_id=uuid.uuid4(), org_id=owner.organization_id)
    service = UserService(db)
    service.users.get_by_id_in_organization = MagicMock(return_value=other)
    service.users.count_by_role = MagicMock(return_value=1)

    with pytest.raises(AppException) as exc:
        service.update_member(owner, other.id, UpdateUserRequest(is_active=False))
    assert exc.value.status_code == 400
