from fastapi import APIRouter, Request, status

from app.core.dependencies import CurrentUser, DbSession
from app.core.rate_limit import limiter, login_limit, password_reset_limit, register_limit
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
@limiter.limit(register_limit)
def register(request: Request, data: RegisterRequest, db: DbSession) -> AuthResponse:
    return AuthService(db).register(data)


@router.post("/login", response_model=AuthResponse)
@limiter.limit(login_limit)
def login(request: Request, data: LoginRequest, db: DbSession) -> AuthResponse:
    return AuthService(db).login(data)


@router.post("/logout", response_model=MessageResponse)
def logout() -> MessageResponse:
    return MessageResponse(message="Sesión cerrada correctamente")


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit(password_reset_limit)
def forgot_password(request: Request, data: ForgotPasswordRequest, db: DbSession) -> MessageResponse:
    message = AuthService(db).forgot_password(data)
    return MessageResponse(message=message)


@router.post("/reset-password", response_model=TokenResponse)
@limiter.limit(password_reset_limit)
def reset_password(request: Request, data: ResetPasswordRequest, db: DbSession) -> TokenResponse:
    return AuthService(db).reset_password(data)


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser, db: DbSession) -> UserResponse:
    return AuthService(db).get_me(current_user.id)
