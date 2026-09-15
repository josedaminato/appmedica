import { apiRequest, ApiError } from "@/lib/api-client"
import type { Consultation, ConsultationListItem, PatientClinicalProfile } from "@/types/api"

export type PatientClinicalUpdatePayload = Partial<
  Pick<
    PatientClinicalProfile,
    "medical_history" | "allergies" | "current_medications" | "clinical_notes"
  >
>

export interface ConsultationUpdatePayload {
  reason?: string | null
  evolution?: string | null
  diagnosis?: string | null
  indications?: string | null
}

export function getAppointmentConsultation(appointmentId: string) {
  return apiRequest<Consultation>(`/appointments/${appointmentId}/consultation`)
}

export function createAppointmentConsultation(appointmentId: string) {
  return apiRequest<Consultation>(`/appointments/${appointmentId}/consultation`, {
    method: "POST",
  })
}

export function updateConsultation(id: string, data: ConsultationUpdatePayload) {
  return apiRequest<Consultation>(`/consultations/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

export function finalizeConsultation(id: string) {
  return apiRequest<Consultation>(`/consultations/${id}/finalize`, { method: "POST" })
}

export function getConsultation(id: string) {
  return apiRequest<Consultation>(`/consultations/${id}`)
}

export function listPatientConsultations(patientId: string) {
  return apiRequest<ConsultationListItem[]>(`/patients/${patientId}/consultations`)
}

export function createPatientConsultation(
  patientId: string,
  data: { occurred_at?: string | null } = {},
) {
  return apiRequest<Consultation>(`/patients/${patientId}/consultations`, {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export function createConsultationAmendment(consultationId: string, amendReason: string) {
  return apiRequest<Consultation>(`/consultations/${consultationId}/amendments`, {
    method: "POST",
    body: JSON.stringify({ amend_reason: amendReason }),
  })
}

export function getPatientClinical(patientId: string) {
  return apiRequest<PatientClinicalProfile>(`/patients/${patientId}/clinical`)
}

export function updatePatientClinical(
  patientId: string,
  data: PatientClinicalUpdatePayload,
) {
  return apiRequest<PatientClinicalProfile>(`/patients/${patientId}/clinical`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

/** Obtiene consulta existente o crea draft. Tolera 404 en GET y 409 en POST. */
export async function getOrCreateConsultation(appointmentId: string): Promise<Consultation> {
  try {
    return await getAppointmentConsultation(appointmentId)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      try {
        return await createAppointmentConsultation(appointmentId)
      } catch (createErr) {
        if (createErr instanceof ApiError && createErr.status === 409) {
          return getAppointmentConsultation(appointmentId)
        }
        throw createErr
      }
    }
    throw err
  }
}
