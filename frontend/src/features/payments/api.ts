import { apiRequest } from "@/lib/api-client"

export type CollectionTab = "private" | "insurance" | "recent" | "pending"

export type CollectionsSummary = {
  private_debt_total: string
  insurance_debt_total: string
  payments_today_total: string
  payments_today_count: number
  pending_insurance_claims: number
  unclosed_attended: number
  overdue_unresolved: number
}

export type CollectionRow = {
  row_id: string
  kind: "private" | "insurance" | "payment"
  patient_id: string
  patient_name: string
  professional_name: string | null
  appointment_id: string | null
  service_date: string
  health_insurance_name: string | null
  status_label: string
  status_code: string
  payment_method: string | null
  total_amount: string
  balance_pending: string
  days_pending: number
  can_collect: boolean
  can_mark_insurance: boolean
}

export function getCollectionsSummary() {
  return apiRequest<CollectionsSummary>("/payments/summary")
}

export function listCollectionItems(tab: CollectionTab, professionalId?: string) {
  const params = new URLSearchParams({ tab })
  if (professionalId) params.set("professional_id", professionalId)
  return apiRequest<CollectionRow[]>(`/payments/items?${params}`)
}
