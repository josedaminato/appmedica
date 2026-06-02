import { apiRequest } from "@/lib/api-client"
import type {
  HealthInsurance,
  InsuranceClaim,
  InsuranceClaimStatus,
  InsuranceRankingResponse,
  PaginatedResponse,
} from "@/types/api"

export function listHealthInsurances(q?: string) {
  const qs = q ? `?q=${encodeURIComponent(q)}` : ""
  return apiRequest<HealthInsurance[]>(`/health-insurances${qs}`)
}

export function createHealthInsurance(data: {
  name: string
  coverage_percent?: number | null
  estimated_payment_days?: number | null
  notes?: string | null
}) {
  return apiRequest<HealthInsurance>("/health-insurances", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export function getInsuranceRanking() {
  return apiRequest<InsuranceRankingResponse>("/health-insurances/ranking")
}

export function listInsuranceClaims(params: {
  page?: number
  page_size?: number
  status?: InsuranceClaimStatus
  health_insurance_id?: string
  open_only?: boolean
}) {
  const search = new URLSearchParams()
  if (params.page) search.set("page", String(params.page))
  if (params.page_size) search.set("page_size", String(params.page_size))
  if (params.status) search.set("status", params.status)
  if (params.health_insurance_id) search.set("health_insurance_id", params.health_insurance_id)
  if (params.open_only) search.set("open_only", "true")
  const qs = search.toString()
  return apiRequest<PaginatedResponse<InsuranceClaim>>(`/insurance-claims${qs ? `?${qs}` : ""}`)
}

export function updateInsuranceClaim(
  id: string,
  data: {
    status?: InsuranceClaimStatus
    invoiced_at?: string | null
    collected_at?: string | null
    notes?: string | null
  },
) {
  return apiRequest<InsuranceClaim>(`/insurance-claims/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

export function updateHealthInsurance(
  id: string,
  data: Partial<{ name: string; coverage_percent: number | null; estimated_payment_days: number | null; notes: string | null }>,
) {
  return apiRequest<HealthInsurance>(`/health-insurances/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}
