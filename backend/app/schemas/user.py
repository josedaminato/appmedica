import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import UserRole


class TeamMemberResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


class CreateUserRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole

    @field_validator("role")
    @classmethod
    def role_not_owner(cls, value: UserRole) -> UserRole:
        if value == UserRole.OWNER:
            raise ValueError("El rol owner no se puede asignar al crear usuarios")
        return value


class UpdateUserRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    role: UserRole | None = None
    is_active: bool | None = None


class UserDetailResponse(TeamMemberResponse):
    created_at: datetime
