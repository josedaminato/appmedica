import { apiDownload, apiRequest } from "@/lib/api-client"

export type MonthlyReport = {
  year: number
  month: number
  period_label: string
  appointments_total: number
  appointments_attended: number
  appointments_no_show: number
  appointments_cancelled: number
  private_collected_total: string
  private_payments_count: number
  insurance_collected_total: string
  insurance_collected_count: number
  insurance_services_count: number
  total_collected: string
}

export function getMonthlyReport(year: number, month: number) {
  const params = new URLSearchParams({
    year: String(year),
    month: String(month),
  })
  return apiRequest<MonthlyReport>(`/reports/monthly?${params}`)
}

export async function downloadMonthlyReport(
  year: number,
  month: number,
  format: "xlsx" | "csv" = "xlsx",
) {
  const params = new URLSearchParams({
    year: String(year),
    month: String(month),
    format,
  })
  await apiDownload(
    `/reports/monthly/export?${params}`,
    `reporte-${year}-${String(month).padStart(2, "0")}.${format}`,
  )
}
