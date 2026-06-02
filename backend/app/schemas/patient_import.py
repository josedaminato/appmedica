from typing import Any, Literal

from pydantic import BaseModel, Field


class PatientImportMapping(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    dni: str | None = None
    phone: str | None = None
    email: str | None = None
    birth_date: str | None = None
    health_insurance_name: str | None = None
    affiliate_number: str | None = None
    notes: str | None = None


class PatientImportRowPayload(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    dni: str = Field(min_length=7, max_length=20)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = None
    birth_date: str | None = None
    health_insurance_id: str | None = None
    affiliate_number: str | None = Field(default=None, max_length=50)
    notes: str | None = None
    is_active: bool = True


class PatientImportPreviewRow(BaseModel):
    row_number: int
    status: Literal["valid", "error", "duplicate", "skip"]
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    data: PatientImportRowPayload | None = None


class PatientImportAnalyzeRequest(BaseModel):
    """Datos ya leídos en el navegador (evita subir el archivo Excel al servidor)."""

    columns: list[str] = Field(min_length=1)
    rows: list[dict[str, Any]] = Field(max_length=2000)
    mapping: PatientImportMapping | None = None


class PatientImportPreviewResponse(BaseModel):
    columns: list[str]
    suggested_mapping: PatientImportMapping
    target_fields: list[dict[str, str]]
    rows: list[PatientImportPreviewRow]
    summary: dict[str, int]


class PatientImportCommitRequest(BaseModel):
    rows: list[PatientImportRowPayload]
    on_duplicate: Literal["skip", "fail"] = "skip"


class PatientImportCommitResponse(BaseModel):
    created: int
    skipped: int
    failed: int
    errors: list[str] = Field(default_factory=list)
