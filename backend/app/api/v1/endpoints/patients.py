import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.core.rbac import assert_can_delete
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.patient import PatientAdminResponse, PatientCreate, PatientResponse, PatientUpdate
from app.schemas.patient_admin import PatientAdminSummary
from app.schemas.consultation import (
    ConsultationListItem,
    ConsultationResponse,
    PatientClinicalResponse,
    PatientClinicalUpdate,
    PatientConsultationCreate,
)
from app.services.patient_admin_service import PatientAdminService
from app.services.patient_service import PatientService
from app.services.consultation_service import ConsultationService

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=PaginatedResponse[PatientAdminResponse | PatientResponse])
def list_patients(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=100),
    is_active: bool | None = Query(None),
) -> PaginatedResponse[PatientAdminResponse | PatientResponse]:
    return PatientService(db).list_patients(
        current_user.organization_id,
        current_user,
        page=page,
        page_size=page_size,
        q=q,
        is_active=is_active,
    )


@router.post(
    "",
    response_model=PatientAdminResponse | PatientResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_patient(
    data: PatientCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> PatientAdminResponse | PatientResponse:
    return PatientService(db).create_patient(current_user.organization_id, data, current_user)


@router.get("/{patient_id}/admin-summary", response_model=PatientAdminSummary)
def get_patient_admin_summary(
    patient_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> PatientAdminSummary:
    return PatientAdminService(db).get_admin_summary(
        current_user.organization_id, patient_id, current_user,
    )


@router.get("/{patient_id}", response_model=PatientAdminResponse | PatientResponse)
def get_patient(
    patient_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> PatientAdminResponse | PatientResponse:
    return PatientService(db).get_patient(
        current_user.organization_id,
        patient_id,
        current_user,
    )


@router.patch("/{patient_id}", response_model=PatientAdminResponse | PatientResponse)
def update_patient(
    patient_id: uuid.UUID,
    data: PatientUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> PatientAdminResponse | PatientResponse:
    return PatientService(db).update_patient(
        current_user.organization_id,
        patient_id,
        data,
        current_user,
    )


@router.delete("/{patient_id}", response_model=MessageResponse)
def delete_patient(
    patient_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    assert_can_delete(current_user)
    PatientService(db).delete_patient(current_user.organization_id, patient_id)
    return MessageResponse(message="Paciente dado de baja correctamente")


@router.get("/{patient_id}/consultations", response_model=list[ConsultationListItem])
def list_patient_consultations(
    patient_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> list[ConsultationListItem]:
    return ConsultationService(db).list_patient_consultations(
        current_user.organization_id,
        patient_id,
        current_user,
    )


@router.post(
    "/{patient_id}/consultations",
    response_model=ConsultationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_patient_consultation(
    patient_id: uuid.UUID,
    data: PatientConsultationCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ConsultationResponse:
    return ConsultationService(db).create_for_patient(
        current_user.organization_id,
        patient_id,
        data,
        current_user,
    )


@router.get("/{patient_id}/clinical", response_model=PatientClinicalResponse)
def get_patient_clinical(
    patient_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> PatientClinicalResponse:
    return ConsultationService(db).get_patient_clinical(
        current_user.organization_id,
        patient_id,
        current_user,
    )


@router.patch("/{patient_id}/clinical", response_model=PatientClinicalResponse)
def update_patient_clinical(
    patient_id: uuid.UUID,
    data: PatientClinicalUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> PatientClinicalResponse:
    return ConsultationService(db).update_patient_clinical(
        current_user.organization_id,
        patient_id,
        data,
        current_user,
    )
