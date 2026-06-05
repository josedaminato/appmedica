from decimal import Decimal

from pydantic import BaseModel, Field


class OrganizationSettingsResponse(BaseModel):
    default_appointment_duration_minutes: int
    default_private_session_amount: Decimal | None = None
    future_private_amounts_updated: int = 0
    future_durations_updated: int = 0

    model_config = {"from_attributes": True}


class OrganizationSettingsUpdate(BaseModel):
    default_appointment_duration_minutes: int = Field(ge=5, le=240)
    default_private_session_amount: Decimal | None = Field(default=None, ge=0)
