from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from difflib import SequenceMatcher
from typing import Any

from email_validator import EmailNotValidError, validate_email
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request
from app.models.patient import Patient
from app.repositories.health_insurance_repository import HealthInsuranceRepository
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient_import import (
    PatientImportCommitRequest,
    PatientImportCommitResponse,
    PatientImportMapping,
    PatientImportPreviewResponse,
    PatientImportPreviewRow,
    PatientImportRowPayload,
)
from app.services.excel_parser import parse_spreadsheet

TARGET_FIELDS = [
    {"key": "first_name", "label": "Nombre"},
    {"key": "last_name", "label": "Apellido"},
    {"key": "full_name", "label": "Nombre completo"},
    {"key": "dni", "label": "DNI"},
    {"key": "phone", "label": "Teléfono"},
    {"key": "email", "label": "Email"},
    {"key": "birth_date", "label": "Fecha de nacimiento"},
    {"key": "health_insurance_name", "label": "Obra social"},
    {"key": "affiliate_number", "label": "Número de afiliado"},
    {"key": "notes", "label": "Notas"},
]

COLUMN_ALIASES: dict[str, list[str]] = {
    "first_name": ["nombre", "nombres", "first name", "first_name", "name"],
    "last_name": ["apellido", "apellidos", "last name", "last_name", "surname"],
    "full_name": [
        "nombre completo",
        "nombre y apellido",
        "paciente",
        "full name",
        "full_name",
        "nombre apellido",
    ],
    "dni": ["dni", "documento", "doc", "nro documento", "número documento", "cuil"],
    "phone": ["telefono", "teléfono", "tel", "celular", "phone", "móvil", "movil"],
    "email": ["email", "correo", "mail", "e-mail"],
    "birth_date": [
        "fecha nacimiento",
        "fecha de nacimiento",
        "nacimiento",
        "birth date",
        "birth_date",
        "fnac",
    ],
    "health_insurance_name": [
        "obra social",
        "obrasocial",
        "os",
        "prepaga",
        "health insurance",
        "cobertura",
    ],
    "affiliate_number": ["afiliado", "nro afiliado", "número afiliado", "affiliate", "credencial"],
    "notes": ["notas", "observaciones", "comentarios", "notes"],
}


class PatientImportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.patient_repo = PatientRepository(db)
        self.insurance_repo = HealthInsuranceRepository(db)

    def preview_from_file(
        self,
        organization_id: uuid.UUID,
        file_bytes: bytes,
        mapping: PatientImportMapping | None = None,
    ) -> PatientImportPreviewResponse:
        columns, raw_rows = parse_spreadsheet(file_bytes)
        return self.preview_from_rows(organization_id, columns, raw_rows, mapping)

    def preview_from_rows(
        self,
        organization_id: uuid.UUID,
        columns: list[str],
        raw_rows: list[dict[str, Any]],
        mapping: PatientImportMapping | None = None,
    ) -> PatientImportPreviewResponse:
        if not columns:
            raise bad_request("No se detectaron columnas")
        if len(raw_rows) > 2000:
            raise bad_request("Máximo 2000 filas por importación")

        suggested = mapping or self._suggest_mapping(columns)
        insurances = self.insurance_repo.list_all(organization_id)
        preview_rows: list[PatientImportPreviewRow] = []

        for index, raw in enumerate(raw_rows, start=2):
            preview_rows.append(
                self._build_preview_row(
                    organization_id,
                    row_number=index,
                    raw=raw,
                    mapping=suggested,
                    insurances=insurances,
                )
            )

        summary = self._summarize(preview_rows)
        return PatientImportPreviewResponse(
            columns=columns,
            suggested_mapping=suggested,
            target_fields=TARGET_FIELDS,
            rows=preview_rows,
            summary=summary,
        )

    def commit(
        self,
        organization_id: uuid.UUID,
        data: PatientImportCommitRequest,
    ) -> PatientImportCommitResponse:
        if not data.rows:
            raise bad_request("No hay filas para importar")

        if len(data.rows) > 2000:
            raise bad_request("Máximo 2000 filas por importación")

        created = 0
        skipped = 0
        failed = 0
        errors: list[str] = []

        for index, row in enumerate(data.rows, start=1):
            dni = self._normalize_dni(row.dni)
            existing = self.patient_repo.get_by_dni(organization_id, dni)
            if existing:
                if data.on_duplicate == "fail":
                    failed += 1
                    errors.append(f"Fila {index}: DNI {dni} ya existe")
                    continue
                skipped += 1
                continue

            email: str | None = None
            if row.email:
                try:
                    email = str(validate_email(row.email, check_deliverability=False).email)
                except EmailNotValidError:
                    failed += 1
                    errors.append(f"Fila {index}: email inválido")
                    continue

            birth_date = self._parse_date(row.birth_date) if row.birth_date else None
            if row.birth_date and birth_date is None:
                failed += 1
                errors.append(f"Fila {index}: fecha de nacimiento inválida")
                continue

            insurance_id: uuid.UUID | None = None
            if row.health_insurance_id:
                try:
                    insurance_id = uuid.UUID(row.health_insurance_id)
                except ValueError:
                    failed += 1
                    errors.append(f"Fila {index}: obra social inválida")
                    continue
                if not self.insurance_repo.get_by_id(organization_id, insurance_id):
                    failed += 1
                    errors.append(f"Fila {index}: obra social no encontrada")
                    continue

            patient = Patient(
                organization_id=organization_id,
                first_name=row.first_name.strip(),
                last_name=row.last_name.strip(),
                dni=dni,
                phone=row.phone,
                email=email,
                birth_date=birth_date,
                health_insurance_id=insurance_id,
                affiliate_number=row.affiliate_number,
                notes=row.notes,
                is_active=row.is_active,
            )
            self.patient_repo.create(patient)
            created += 1

        if created:
            self.db.commit()
        else:
            self.db.rollback()

        return PatientImportCommitResponse(
            created=created,
            skipped=skipped,
            failed=failed,
            errors=errors[:50],
        )

    def _suggest_mapping(self, columns: list[str]) -> PatientImportMapping:
        normalized_cols = {self._norm(col): col for col in columns}
        mapping: dict[str, str | None] = {key: None for key in COLUMN_ALIASES}

        for field, aliases in COLUMN_ALIASES.items():
            for alias in aliases:
                norm_alias = self._norm(alias)
                if norm_alias in normalized_cols:
                    mapping[field] = normalized_cols[norm_alias]
                    break
            if mapping[field]:
                continue
            for norm_col, original in normalized_cols.items():
                if any(norm_alias in norm_col or norm_col in norm_alias for norm_alias in aliases):
                    mapping[field] = original
                    break

        return PatientImportMapping(**mapping)

    def _build_preview_row(
        self,
        organization_id: uuid.UUID,
        *,
        row_number: int,
        raw: dict[str, Any],
        mapping: PatientImportMapping,
        insurances: list,
    ) -> PatientImportPreviewRow:
        errors: list[str] = []
        warnings: list[str] = []

        first_name, last_name, name_warnings = self._resolve_name(raw, mapping)
        warnings.extend(name_warnings)

        dni_raw = self._get_cell(raw, mapping.dni)
        if not dni_raw:
            errors.append("Falta DNI")
            dni = ""
        else:
            dni = self._normalize_dni(dni_raw)
            if len(dni) < 7:
                errors.append("DNI demasiado corto")

        if not first_name:
            errors.append("Falta nombre")
        if not last_name:
            errors.append("Falta apellido")

        phone = self._normalize_phone(self._get_cell(raw, mapping.phone))
        email_raw = self._get_cell(raw, mapping.email)
        email: str | None = None
        if email_raw:
            try:
                email = str(validate_email(email_raw, check_deliverability=False).email)
            except EmailNotValidError:
                errors.append("Email inválido")

        birth_raw = self._get_cell(raw, mapping.birth_date)
        birth_date: date | None = None
        if birth_raw:
            birth_date = self._parse_date(birth_raw)
            if birth_date is None:
                errors.append("Fecha de nacimiento inválida")

        insurance_name = self._get_cell(raw, mapping.health_insurance_name)
        insurance_id, insurance_warnings = self._match_insurance(insurance_name, insurances)
        warnings.extend(insurance_warnings)

        affiliate = self._get_cell(raw, mapping.affiliate_number) or None
        notes = self._get_cell(raw, mapping.notes) or None

        if errors:
            return PatientImportPreviewRow(
                row_number=row_number,
                status="error",
                errors=errors,
                warnings=warnings,
            )

        assert first_name and last_name
        existing = self.patient_repo.get_by_dni(organization_id, dni)
        if existing:
            return PatientImportPreviewRow(
                row_number=row_number,
                status="duplicate",
                warnings=["Ya existe un paciente con este DNI"],
                data=PatientImportRowPayload(
                    first_name=first_name,
                    last_name=last_name,
                    dni=dni,
                    phone=phone,
                    email=email,
                    birth_date=birth_date.isoformat() if birth_date else None,
                    health_insurance_id=str(insurance_id) if insurance_id else None,
                    affiliate_number=affiliate,
                    notes=notes,
                ),
            )

        return PatientImportPreviewRow(
            row_number=row_number,
            status="valid",
            warnings=warnings,
            data=PatientImportRowPayload(
                first_name=first_name,
                last_name=last_name,
                dni=dni,
                phone=phone,
                email=email,
                birth_date=birth_date.isoformat() if birth_date else None,
                health_insurance_id=str(insurance_id) if insurance_id else None,
                affiliate_number=affiliate,
                notes=notes,
            ),
        )

    def _resolve_name(
        self, raw: dict[str, Any], mapping: PatientImportMapping
    ) -> tuple[str | None, str | None, list[str]]:
        warnings: list[str] = []
        first = self._get_cell(raw, mapping.first_name)
        last = self._get_cell(raw, mapping.last_name)
        if first and last:
            return first, last, warnings

        full = self._get_cell(raw, mapping.full_name)
        if full:
            parts = full.split()
            if len(parts) == 1:
                return parts[0], parts[0], ["Nombre completo con una sola palabra"]
            return " ".join(parts[:-1]), parts[-1], warnings

        if first and not last:
            return first, first, ["Apellido inferido del nombre"]
        if last and not first:
            return last, last, ["Nombre inferido del apellido"]
        return None, None, warnings

    def _match_insurance(
        self, name: str | None, insurances: list
    ) -> tuple[uuid.UUID | None, list[str]]:
        if not name:
            return None, []
        warnings: list[str] = []
        norm_name = self._norm(name)
        best_id: uuid.UUID | None = None
        best_score = 0.0
        for ins in insurances:
            score = SequenceMatcher(None, norm_name, self._norm(ins.name)).ratio()
            if score > best_score:
                best_score = score
                best_id = ins.id
        if best_score >= 0.72 and best_id:
            if best_score < 0.95:
                warnings.append(f"Obra social asignada por similitud ({name})")
            return best_id, warnings
        warnings.append(f"No se encontró obra social: {name}")
        return None, warnings

    def _summarize(self, rows: list[PatientImportPreviewRow]) -> dict[str, int]:
        return {
            "total": len(rows),
            "valid": sum(1 for r in rows if r.status == "valid"),
            "duplicate": sum(1 for r in rows if r.status == "duplicate"),
            "error": sum(1 for r in rows if r.status == "error"),
        }

    @staticmethod
    def _get_cell(raw: dict[str, Any], column: str | None) -> str:
        if not column:
            return ""
        value = raw.get(column, "")
        return str(value).strip() if value is not None else ""

    @staticmethod
    def _norm(value: str) -> str:
        return re.sub(r"\s+", " ", value.strip().lower())

    @staticmethod
    def _normalize_dni(value: str) -> str:
        return re.sub(r"[^\d]", "", value.strip())

    @staticmethod
    def _normalize_phone(value: str | None) -> str | None:
        if not value:
            return None
        cleaned = re.sub(r"[^\d+]", "", value)
        return cleaned or None

    @staticmethod
    def _parse_date(value: str | date | datetime) -> date | None:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        text = str(value).strip()
        if not text:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(text[:10], fmt).date()
            except ValueError:
                continue
        return None
