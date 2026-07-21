import uuid
from datetime import date

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.core.rbac import resolve_professional_filter
from app.models.enums import AppointmentClosureStatus, AppointmentStatus
from app.schemas.appointment import (
    AddPaymentRequest,
    AppointmentCreate,
    AppointmentCreateResult,
    AppointmentRescheduleRequest,
    AppointmentResponse,
    AppointmentUpdate,
    CloseAppointmentRequest,
)
from app.schemas.common import MessageResponse
from app.services.appointment_closure_service import AppointmentClosureService
from app.services.appointment_service import AppointmentService

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("", response_model=list[AppointmentResponse])
def list_appointments(
    current_user: CurrentUser,
    db: DbSession,
    date_param: date = Query(..., alias="date"),
    view: str = Query("day", pattern="^(day|week)$"),
    professional_id: uuid.UUID | None = None,
    status: AppointmentStatus | None = None,
    patient_q: str | None = Query(None, max_length=100),
    closure_status: AppointmentClosureStatus | None = None,
) -> list[AppointmentResponse]:
    prof_filter = resolve_professional_filter(current_user, professional_id)
    return AppointmentService(db).list_appointments(
        current_user.organization_id,
        view=view,
        reference_date=date_param,
        professional_id=prof_filter,
        status=status,
        patient_q=patient_q,
        closure_status=closure_status,
    )


@router.post("", response_model=AppointmentCreateResult, status_code=status.HTTP_201_CREATED)
def create_appointment(
    data: AppointmentCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> AppointmentCreateResult:
    return AppointmentService(db).create_appointment(
        current_user.organization_id,
        data,
        current_user,
    )


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> AppointmentResponse:
    return AppointmentService(db).get_appointment(
        current_user.organization_id, appointment_id, current_user,
    )


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: uuid.UUID,
    data: AppointmentUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> AppointmentResponse:
    return AppointmentService(db).update_appointment(
        current_user.organization_id, appointment_id, data, current_user,
    )


@router.post("/{appointment_id}/confirm", response_model=AppointmentResponse)
def confirm_appointment(
    appointment_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> AppointmentResponse:
    return AppointmentService(db).confirm(current_user.organization_id, appointment_id, current_user)


@router.post("/{appointment_id}/attend", response_model=AppointmentResponse)
def attend_appointment(
    appointment_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> AppointmentResponse:
    return AppointmentService(db).mark_attended(current_user.organization_id, appointment_id, current_user)


@router.post("/{appointment_id}/no-show", response_model=AppointmentResponse)
def no_show_appointment(
    appointment_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> AppointmentResponse:
    return AppointmentService(db).mark_no_show(current_user.organization_id, appointment_id, current_user)


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(
    appointment_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> AppointmentResponse:
    return AppointmentService(db).cancel(current_user.organization_id, appointment_id, current_user)


@router.post("/{appointment_id}/cancel-series", response_model=MessageResponse)
def cancel_appointment_series(
    appointment_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    return AppointmentService(db).cancel_series_from(
        current_user.organization_id, appointment_id, current_user,
    )


@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
def reschedule_appointment(
    appointment_id: uuid.UUID,
    data: AppointmentRescheduleRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> AppointmentResponse:
    return AppointmentService(db).reschedule(
        current_user.organization_id, appointment_id, data, current_user,
    )


@router.post("/{appointment_id}/close", response_model=AppointmentResponse)
def close_appointment(
    appointment_id: uuid.UUID,
    data: CloseAppointmentRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> AppointmentResponse:
    return AppointmentClosureService(db).close_appointment(
        current_user.organization_id,
        appointment_id,
        data,
        current_user,
    )


@router.post("/{appointment_id}/payments", response_model=AppointmentResponse)
def add_payment_to_appointment(
    appointment_id: uuid.UUID,
    data: AddPaymentRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> AppointmentResponse:
    return AppointmentClosureService(db).add_payment_to_appointment(
        current_user.organization_id,
        appointment_id,
        data,
        current_user,
    )
