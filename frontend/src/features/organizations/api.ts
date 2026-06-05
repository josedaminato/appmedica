import { apiRequest } from "@/lib/api-client"

export type OrganizationSettings = {
  default_appointment_duration_minutes: number
  default_private_session_amount: number | null
  future_private_amounts_updated?: number
  future_durations_updated?: number
}

export function getOrganizationSettings() {
  return apiRequest<OrganizationSettings>("/organizations/settings")
}

export function updateOrganizationSettings(data: OrganizationSettings) {
  return apiRequest<OrganizationSettings>("/organizations/settings", {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}
