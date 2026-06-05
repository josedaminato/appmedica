"""Rate limiting para endpoints sensibles (autenticacion).

Usa slowapi con almacenamiento en memoria (suficiente para 1 worker).
La clave es la IP del cliente; los limites se configuran por settings.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.rate_limit_enabled,
)


def login_limit() -> str:
    return get_settings().rate_limit_login


def register_limit() -> str:
    return get_settings().rate_limit_register


def password_reset_limit() -> str:
    return get_settings().rate_limit_password_reset
