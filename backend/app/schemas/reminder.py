import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ReminderChannel, ReminderStatus


class ReminderJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID | None
    channel: ReminderChannel
    status: ReminderStatus
    scheduled_at: datetime
    payload: dict | None
    error_message: str | None
    created_at: datetime


class ReminderProcessResult(BaseModel):
    processed: int
    sent: int
    failed: int
