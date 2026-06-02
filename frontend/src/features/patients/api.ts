import { apiRequest } from "@/lib/api-client"
import type { MessageResponse, PaginatedResponse, Patient, PatientAdminSummary } from "@/types/api"

export interface PatientPayload {
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

export interface PatientListParams {
  page?: number
  page_size?: number
  q?: string
  is_active?: boolean
}

export function listPatients(params: PatientListParams = {}) {
  const search = new URLSearchParams()
  if (params.page) search.set("page", String(params.page))
  if (params.page_size) search.set("page_size", String(params.page_size))
  if (params.q) search.set("q", params.q)
  if (params.is_active !== undefined) search.set("is_active", String(params.is_active))
  const qs = search.toString()
  return apiRequest<PaginatedResponse<Patient>>(`/patients${qs ? `?${qs}` : ""}`)
}

export function getPatient(id: string) {
  return apiRequest<Patient>(`/patients/${id}`)
}

export function createPatient(data: PatientPayload) {
  return apiRequest<Patient>("/patients", { method: "POST", body: JSON.stringify(data) })
}

export function updatePatient(id: string, data: Partial<PatientPayload>) {
  return apiRequest<Patient>(`/patients/${id}`, { method: "PATCH", body: JSON.stringify(data) })
}

export function deletePatient(id: string) {
  return apiRequest<MessageResponse>(`/patients/${id}`, { method: "DELETE" })
}

export function getPatientAdminSummary(id: string) {
  return apiRequest<PatientAdminSummary>(`/patients/${id}/admin-summary`)
}
