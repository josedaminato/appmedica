import { TOKEN_KEY } from "@/lib/constants"
import { apiRequest } from "@/lib/api-client"

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
  const token = localStorage.getItem(TOKEN_KEY)
  const base = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1"
  const params = new URLSearchParams({
    year: String(year),
    month: String(month),
    format,
  })
  const response = await fetch(`${base}/reports/monthly/export?${params}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    throw new Error("No se pudo exportar el reporte")
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `reporte-${year}-${String(month).padStart(2, "0")}.${format}`
  a.click()
  URL.revokeObjectURL(url)
}
