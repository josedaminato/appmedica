import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import unauthorized
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository

security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
) -> User:
    if not credentials or not credentials.credentials:
        raise unauthorized("Token requerido")

    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise unauthorized("Token inválido") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise unauthorized("Token inválido")

    user = UserRepository(db).get_by_id(uuid.UUID(str(user_id)))
    if not user or not user.is_active:
        raise unauthorized("Usuario no encontrado o inactivo")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]
