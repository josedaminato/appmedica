from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, conflict, not_found
from app.core.rbac import assert_owner
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import CreateUserRequest, TeamMemberResponse, UpdateUserRequest, UserDetailResponse


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def list_team(self, organization_id: uuid.UUID, *, active_only: bool = True) -> list[TeamMemberResponse]:
        members = self.users.list_by_organization(organization_id, active_only=active_only)
        return [TeamMemberResponse.model_validate(m) for m in members]

    def list_all(self, actor: User) -> list[UserDetailResponse]:
        assert_owner(actor)
        members = self.users.list_by_organization(actor.organization_id, active_only=False)
        return [UserDetailResponse.model_validate(m) for m in members]

    def create_member(self, actor: User, data: CreateUserRequest) -> UserDetailResponse:
        assert_owner(actor)
        if data.role == UserRole.OWNER:
            raise bad_request("No podés crear otro usuario owner desde acá")

        email = data.email.lower()
        if self.users.get_by_email(email):
            raise conflict("El email ya está registrado")

        user = User(
            organization_id=actor.organization_id,
            email=email,
            password_hash=hash_password(data.password),
            full_name=data.full_name.strip(),
            role=data.role,
            is_active=True,
        )
        self.users.create(user)
        self.db.commit()
        self.db.refresh(user)
        return UserDetailResponse.model_validate(user)

    def update_member(
        self,
        actor: User,
        user_id: uuid.UUID,
        data: UpdateUserRequest,
    ) -> UserDetailResponse:
        assert_owner(actor)
        user = self.users.get_by_id_in_organization(actor.organization_id, user_id)
        if not user:
            raise not_found("Usuario")

        if user.id == actor.id:
            if data.role is not None and data.role != user.role:
                raise bad_request("No podés cambiar tu propio rol")
            if data.is_active is False:
                raise bad_request("No podés desactivarte a vos mismo")

        if data.role == UserRole.OWNER and user.role != UserRole.OWNER:
            raise bad_request("No podés promover usuarios a owner")

        if data.role is not None and user.role == UserRole.OWNER and data.role != UserRole.OWNER:
            if self.users.count_by_role(actor.organization_id, UserRole.OWNER) <= 1:
                raise bad_request("Debe quedar al menos un owner activo en el consultorio")

        if data.is_active is False and user.role == UserRole.OWNER:
            if self.users.count_by_role(actor.organization_id, UserRole.OWNER, active_only=True) <= 1:
                raise bad_request("No podés desactivar al único owner del consultorio")

        if data.full_name is not None:
            user.full_name = data.full_name.strip()
        if data.role is not None:
            user.role = data.role
        if data.is_active is not None:
            user.is_active = data.is_active

        self.users.update(user)
        self.db.commit()
        self.db.refresh(user)
        return UserDetailResponse.model_validate(user)
