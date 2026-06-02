from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: DbSession) -> AuthResponse:
    return AuthService(db).register(data)


@router.post("/login", response_model=AuthResponse)
def login(data: LoginRequest, db: DbSession) -> AuthResponse:
    return AuthService(db).login(data)


@router.post("/logout", response_model=MessageResponse)
def logout() -> MessageResponse:
    return MessageResponse(message="Sesión cerrada correctamente")


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(data: ForgotPasswordRequest, db: DbSession) -> MessageResponse:
    message = AuthService(db).forgot_password(data)
    return MessageResponse(message=message)


@router.post("/reset-password", response_model=TokenResponse)
def reset_password(data: ResetPasswordRequest, db: DbSession) -> TokenResponse:
    return AuthService(db).reset_password(data)


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser, db: DbSession) -> UserResponse:
    return AuthService(db).get_me(current_user.id)
