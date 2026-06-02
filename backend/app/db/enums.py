import enum
from typing import TypeVar

from sqlalchemy import Enum

E = TypeVar("E", bound=enum.Enum)


def pg_enum(enum_class: type[E], name: str) -> Enum:
    """PostgreSQL enum usando los valores (ej. 'owner'), no los nombres (OWNER)."""
    return Enum(
        enum_class,
        name=name,
        values_callable=lambda x: [e.value for e in x],
    )
