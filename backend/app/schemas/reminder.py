import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ReminderChannel, ReminderKind, ReminderStatus


class ReminderJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    appointment_id: uuid.UUID
    patient_id: uuid.UUID | None
    kind: ReminderKind
    channel: ReminderChannel
    status: ReminderStatus
    scheduled_at: datetime
    next_attempt_at: datetime
    sent_at: datetime | None
    attempt_count: int
    provider: str | None
    payload: dict | None
    error_code: str | None
    error_message: str | None
    created_at: datetime


class ReminderProcessResult(BaseModel):
    processed: int
    sent: int
    failed: int
    skipped: int = 0
    retried: int = 0
