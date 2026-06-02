import json

from fastapi import APIRouter, File, Form, UploadFile, status

from app.core.dependencies import CurrentUser, DbSession
from app.core.exceptions import bad_request
from app.schemas.patient_import import (
    PatientImportAnalyzeRequest,
    PatientImportCommitRequest,
    PatientImportCommitResponse,
    PatientImportMapping,
    PatientImportPreviewResponse,
)
from app.services.patient_import_service import PatientImportService

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/patients/analyze", response_model=PatientImportPreviewResponse)
def analyze_patient_import(
    data: PatientImportAnalyzeRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> PatientImportPreviewResponse:
    """Valida filas leídas en el cliente (sin subir el archivo Excel)."""
    return PatientImportService(db).preview_from_rows(
        current_user.organization_id,
        data.columns,
        data.rows,
        data.mapping,
    )


@router.post("/patients/preview", response_model=PatientImportPreviewResponse)
async def preview_patient_import(
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    mapping: str | None = Form(default=None),
) -> PatientImportPreviewResponse:
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise bad_request("Subí un archivo Excel (.xlsx)")
    content = await file.read()
    parsed_mapping: PatientImportMapping | None = None
    if mapping:
        try:
            parsed_mapping = PatientImportMapping.model_validate(json.loads(mapping))
        except (json.JSONDecodeError, ValueError) as exc:
            raise bad_request("Mapeo de columnas inválido") from exc
    return PatientImportService(db).preview_from_file(
        current_user.organization_id,
        content,
        parsed_mapping,
    )


@router.post(
    "/patients/commit",
    response_model=PatientImportCommitResponse,
    status_code=status.HTTP_201_CREATED,
)
def commit_patient_import(
    data: PatientImportCommitRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> PatientImportCommitResponse:
    return PatientImportService(db).commit(current_user.organization_id, data)
