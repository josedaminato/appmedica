import { apiRequest } from "@/lib/api-client"
import type { DashboardAlerts, DashboardSummary } from "@/types/api"

export function getDashboardSummary() {
  return apiRequest<DashboardSummary>("/dashboard/summary")
}

export function getDashboardAlerts(claimsOldDays = 45) {
  return apiRequest<DashboardAlerts>(`/dashboard/alerts?claims_old_days=${claimsOldDays}`)
}
