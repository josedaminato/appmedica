import { apiRequest } from "@/lib/api-client"
import type { ParsedSpreadsheet } from "@/lib/spreadsheet-parser"

export type PatientImportMapping = {
  first_name?: string | null
  last_name?: string | null
  full_name?: string | null
  dni?: string | null
  phone?: string | null
  email?: string | null
  birth_date?: string | null
  health_insurance_name?: string | null
  affiliate_number?: string | null
  notes?: string | null
}

export type PatientImportRowPayload = {
  first_name: string
  last_name: string
  dni: string
  phone?: string | null
  email?: string | null
  birth_date?: string | null
  health_insurance_id?: string | null
  affiliate_number?: string | null
  notes?: string | null
  is_active?: boolean
}

export type PatientImportPreviewRow = {
  row_number: number
  status: "valid" | "error" | "duplicate" | "skip"
  errors: string[]
  warnings: string[]
  data: PatientImportRowPayload | null
}

export type PatientImportPreview = {
  columns: string[]
  suggested_mapping: PatientImportMapping
  target_fields: { key: string; label: string }[]
  rows: PatientImportPreviewRow[]
  summary: {
    total: number
    valid: number
    duplicate: number
    error: number
  }
}

export type PatientImportCommitResult = {
  created: number
  skipped: number
  failed: number
  errors: string[]
}

/** Valida filas en el servidor (JSON; el Excel no se sube). */
export function analyzePatientImport(
  sheet: ParsedSpreadsheet,
  mapping?: PatientImportMapping,
) {
  return apiRequest<PatientImportPreview>("/imports/patients/analyze", {
    method: "POST",
    body: JSON.stringify({
      columns: sheet.columns,
      rows: sheet.rows,
      mapping: mapping ?? null,
    }),
  })
}

export function commitPatientImport(
  rows: PatientImportRowPayload[],
  onDuplicate: "skip" | "fail" = "skip",
) {
  return apiRequest<PatientImportCommitResult>("/imports/patients/commit", {
    method: "POST",
    body: JSON.stringify({ rows, on_duplicate: onDuplicate }),
  })
}
