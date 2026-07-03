import { platformApiRequest } from "@/lib/platform-api-client"

export interface PlatformAuthResponse {
  access_token: string
  token_type: string
  username: string
}

export interface PlatformTenantRow {
  id: string
  name: string
  owner_email: string | null
  owner_name: string | null
  service_started_at: string
  paid_until: string | null
  monthly_fee: string
  payment_status: "overdue" | "due_today" | "due_soon" | "current" | "unknown"
  days_until_due: number | null
  users_count: number
  patients_count: number
  appointments_count: number
}

export interface PlatformDashboard {
  total_clients: number
  payments_due: number
  due_soon: number
  tenants: PlatformTenantRow[]
}

export function platformLogin(username: string, password: string) {
  return platformApiRequest<PlatformAuthResponse>("/platform/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
    skipAuth: true,
  })
}

export function getPlatformDashboard() {
  return platformApiRequest<PlatformDashboard>("/platform/dashboard")
}

export function markTenantPaid(organizationId: string) {
  return platformApiRequest<{ id: string; paid_until: string; payment_status: string }>(
    `/platform/tenants/${organizationId}/mark-paid`,
    { method: "POST" },
  )
}

export function deleteTenant(organizationId: string) {
  return platformApiRequest<{ message: string }>(`/platform/tenants/${organizationId}`, {
    method: "DELETE",
  })
}
