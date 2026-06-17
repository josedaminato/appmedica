import { apiDownload } from "@/lib/api-client"

export async function downloadExport(
  resource: "patients" | "payments" | "claims" | "debt",
  format: "xlsx" | "csv" = "xlsx",
) {
  await apiDownload(`/exports/${resource}?format=${format}`, `${resource}.${format}`)
}
