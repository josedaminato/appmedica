import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DbSession
from app.core.rbac import assert_owner
from app.schemas.reminder import ReminderJobResponse, ReminderProcessResult
from app.services.reminder_service import ReminderService

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderJobResponse])
def list_reminders(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
) -> list[ReminderJobResponse]:
    jobs = ReminderService(db).list_jobs(current_user.organization_id, limit=limit)
    return [ReminderJobResponse.model_validate(j) for j in jobs]


@router.post("/process-due", response_model=ReminderProcessResult)
async def process_due_reminders(
    current_user: CurrentUser,
    db: DbSession,
) -> ReminderProcessResult:
    assert_owner(current_user)
    result = await ReminderService(db).process_due_jobs(
        organization_id=current_user.organization_id,
    )
    return ReminderProcessResult(**result)


@router.post("/appointments/{appointment_id}/schedule", response_model=list[ReminderJobResponse])
def schedule_appointment_reminders(
    appointment_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> list[ReminderJobResponse]:
    jobs = ReminderService(db).schedule_for_appointment(
        current_user.organization_id,
        appointment_id,
    )
    return [ReminderJobResponse.model_validate(j) for j in jobs]
