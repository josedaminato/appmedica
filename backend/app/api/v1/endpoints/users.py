import uuid

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.user import (
    CreateUserRequest,
    TeamMemberResponse,
    UpdateUserRequest,
    UserDetailResponse,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/team", response_model=list[TeamMemberResponse])
def list_team(current_user: CurrentUser, db: DbSession) -> list[TeamMemberResponse]:
    """Miembros activos del consultorio (selectores de agenda, etc.)."""
    return UserService(db).list_team(current_user.organization_id, active_only=True)


@router.get("", response_model=list[UserDetailResponse])
def list_users(current_user: CurrentUser, db: DbSession) -> list[UserDetailResponse]:
    """Todos los usuarios del consultorio, incluidos inactivos (solo owner)."""
    return UserService(db).list_all(current_user)


@router.post("", response_model=UserDetailResponse, status_code=201)
def create_user(
    data: CreateUserRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> UserDetailResponse:
    return UserService(db).create_member(current_user, data)


@router.patch("/{user_id}", response_model=UserDetailResponse)
def update_user(
    user_id: uuid.UUID,
    data: UpdateUserRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> UserDetailResponse:
    return UserService(db).update_member(current_user, user_id, data)
