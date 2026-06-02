import { TOKEN_KEY } from "@/lib/constants"

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1"

export async function downloadExport(
  resource: "patients" | "payments" | "claims" | "debt",
  format: "xlsx" | "csv" = "xlsx",
) {
  const token = localStorage.getItem(TOKEN_KEY)
  const response = await fetch(`${API_URL}/exports/${resource}?format=${format}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    throw new Error("No se pudo exportar")
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `${resource}.${format}`
  a.click()
  URL.revokeObjectURL(url)
}
