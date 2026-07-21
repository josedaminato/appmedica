import { apiRequest } from "@/lib/api-client"
import type {
  Appointment,
  AppointmentClosureStatus,
  AppointmentStatus,
  AttentionType,
  AppointmentModality,
} from "@/types/api"

export interface AppointmentPayload {
  patient_id: string
  professional_id?: string | null
  start_at: string
  end_at: string
  modality?: AppointmentModality
  attention_type?: AttentionType
  expected_amount?: number | null
  health_insurance_id?: string | null
  notes?: string | null
  recurring_weekly?: boolean
  weeks?: number
}

export interface AppointmentCreateResult {
  created_count: number
  series_id: string | null
  appointments: Appointment[]
}

export interface ClosePayload {
  closure_type: AppointmentClosureStatus
  amount: number
  method?: string
  paid_amount?: number
  health_insurance_id?: string
  notes?: string
}

export function listAppointments(params: {
  date: string
  view?: "day" | "week"
  professional_id?: string
  status?: AppointmentStatus
  patient_q?: string
  closure_status?: AppointmentClosureStatus
}) {
  const qs = new URLSearchParams({ date: params.date, view: params.view ?? "day" })
  if (params.professional_id) qs.set("professional_id", params.professional_id)
  if (params.status) qs.set("status", params.status)
  if (params.patient_q) qs.set("patient_q", params.patient_q)
  if (params.closure_status) qs.set("closure_status", params.closure_status)
  return apiRequest<Appointment[]>(`/appointments?${qs}`)
}

export function createAppointment(data: AppointmentPayload) {
  return apiRequest<AppointmentCreateResult>("/appointments", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export function confirmAppointment(id: string) {
  return apiRequest<Appointment>(`/appointments/${id}/confirm`, { method: "POST" })
}

export function attendAppointment(id: string) {
  return apiRequest<Appointment>(`/appointments/${id}/attend`, { method: "POST" })
}

export function noShowAppointment(id: string) {
  return apiRequest<Appointment>(`/appointments/${id}/no-show`, { method: "POST" })
}

export function cancelAppointment(id: string) {
  return apiRequest<Appointment>(`/appointments/${id}/cancel`, { method: "POST" })
}

export function cancelAppointmentSeries(id: string) {
  return apiRequest<{ message: string }>(`/appointments/${id}/cancel-series`, { method: "POST" })
}

export function rescheduleAppointment(
  id: string,
  data: { start_at: string; end_at: string; professional_id?: string | null; notes?: string | null },
) {
  return apiRequest<Appointment>(`/appointments/${id}/reschedule`, {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export function closeAppointment(id: string, data: ClosePayload) {
  return apiRequest<Appointment>(`/appointments/${id}/close`, {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export function addPaymentToAppointment(id: string, data: { amount: number; method: string; notes?: string }) {
  return apiRequest<Appointment>(`/appointments/${id}/payments`, {
    method: "POST",
    body: JSON.stringify(data),
  })
}
