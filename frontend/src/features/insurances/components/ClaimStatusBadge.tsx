import { Badge } from "@/components/ui/badge"
import type { InsuranceClaimStatus } from "@/types/api"

const LABELS: Record<InsuranceClaimStatus, string> = {
  pending: "Pendiente",
  invoiced: "Facturado",
  collected: "Cobrado",
  rejected: "Rechazado",
}

const VARIANTS: Record<
  InsuranceClaimStatus,
  "secondary" | "warning" | "success" | "destructive"
> = {
  pending: "warning",
  invoiced: "secondary",
  collected: "success",
  rejected: "destructive",
}

export function ClaimStatusBadge({ status }: { status: InsuranceClaimStatus }) {
  return <Badge variant={VARIANTS[status]}>{LABELS[status]}</Badge>
}
