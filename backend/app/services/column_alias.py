"""Detección de columnas equivalentes en importaciones de planillas."""

from __future__ import annotations

import re
import unicodedata

# Orden de prioridad: campos compuestos antes que simples para evitar conflictos
# (p. ej. "Nombre y apellido" → nombre completo, no nombre).
MATCH_ORDER: tuple[str, ...] = (
    "full_name",
    "first_name",
    "last_name",
    "dni",
    "phone",
    "email",
    "birth_date",
    "health_insurance_name",
    "affiliate_number",
    "notes",
)

COLUMN_ALIASES: dict[str, list[str]] = {
    "full_name": [
        "paciente",
        "nombre completo",
        "nombre paciente",
        "nombre y apellido",
        "nombre_apellido",
        "nombre-apellido",
        "full name",
        "full_name",
        "nombre apellido",
        "apellido y nombre",
    ],
    "first_name": [
        "nombre",
        "nombres",
        "first name",
        "first_name",
        "name",
    ],
    "last_name": [
        "apellido",
        "apellidos",
        "last name",
        "last_name",
        "surname",
    ],
    "dni": [
        "dni",
        "documento",
        "doc",
        "nro documento",
        "número documento",
        "numero documento",
        "documento identidad",
        "cedula",
        "cédula",
        "cuil",
        "nro doc",
        "n documento",
    ],
    "phone": [
        "telefono",
        "teléfono",
        "tel",
        "celular",
        "móvil",
        "movil",
        "mobile",
        "phone",
        "cel",
        "contacto",
    ],
    "email": [
        "email",
        "correo",
        "correo electrónico",
        "correo electronico",
        "mail",
        "e-mail",
        "e mail",
    ],
    "birth_date": [
        "fecha nacimiento",
        "fecha de nacimiento",
        "nacimiento",
        "fecha nac",
        "f nac",
        "f. nacimiento",
        "f nacimiento",
        "fnac",
        "birth date",
        "birth_date",
        "fecha nac.",
    ],
    "health_insurance_name": [
        "obra social",
        "obrasocial",
        "prepaga",
        "cobertura",
        "insurance",
        "health insurance",
        "os",
        "mutual",
    ],
    "affiliate_number": [
        "afiliado",
        "nro afiliado",
        "número afiliado",
        "numero afiliado",
        "nº afiliado",
        "n afiliado",
        "affiliate",
        "credencial",
        "nro credencial",
    ],
    "notes": [
        "notas",
        "observaciones",
        "comentarios",
        "notes",
        "obs",
    ],
}


def normalize_column_name(value: str) -> str:
    """Minúsculas, sin tildes, espacios unificados, _ y - como espacio."""
    text = value.strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[_\-.]+", " ", text)
    text = re.sub(r"[º°ª.]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _alias_matches_column(norm_alias: str, norm_col: str) -> bool:
    if norm_col == norm_alias:
        return True
    if norm_col.startswith(f"{norm_alias} ") or norm_col.endswith(f" {norm_alias}"):
        return True
    if f" {norm_alias} " in f" {norm_col} ":
        return True
    return False


def detect_column_mapping(columns: list[str]) -> dict[str, str | None]:
    """Devuelve mapeo campo → columna original detectada automáticamente."""
    normalized_cols: dict[str, str] = {}
    for col in columns:
        norm = normalize_column_name(col)
        if norm and norm not in normalized_cols:
            normalized_cols[norm] = col

    used_columns: set[str] = set()
    mapping: dict[str, str | None] = {field: None for field in COLUMN_ALIASES}

    for field in MATCH_ORDER:
        aliases = COLUMN_ALIASES[field]
        norm_aliases = [normalize_column_name(a) for a in aliases]

        for norm_alias in sorted(norm_aliases, key=len, reverse=True):
            if norm_alias in normalized_cols:
                col = normalized_cols[norm_alias]
                if col not in used_columns:
                    mapping[field] = col
                    used_columns.add(col)
                    break
        if mapping[field]:
            continue

        best_col: str | None = None
        best_score = 0
        for norm_col, original in normalized_cols.items():
            if original in used_columns:
                continue
            for norm_alias in norm_aliases:
                if _alias_matches_column(norm_alias, norm_col):
                    score = len(norm_alias)
                    if score > best_score:
                        best_score = score
                        best_col = original
        if best_col:
            mapping[field] = best_col
            used_columns.add(best_col)

    return mapping
