from app.core.exceptions import AppException
from app.models.enums import UserRole
from app.models.user import User
from fastapi import status


def forbidden(message: str = "No tenés permiso para esta acción") -> AppException:
    return AppException(status.HTTP_403_FORBIDDEN, "FORBIDDEN", message)


def assert_can_delete(user: User) -> None:
    if user.role == UserRole.STAFF:
        raise forbidden("El rol staff no puede eliminar registros")


def assert_owner(user: User) -> None:
    if user.role != UserRole.OWNER:
        raise forbidden("Solo el owner puede gestionar el equipo")


def resolve_professional_filter(
    user: User,
    requested_professional_id,
):
    """Professional solo ve su cartera; owner/staff ven todo el consultorio."""
    if user.role == UserRole.PROFESSIONAL:
        return user.id
    return requested_professional_id
