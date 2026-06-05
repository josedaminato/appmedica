import { Badge } from "@/components/ui/badge"
import { attentionLabel } from "@/lib/attention-label"
import type { AppointmentClosureStatus, AppointmentStatus, AttentionType } from "@/types/api"

const statusLabels: Record<AppointmentStatus, string> = {
  pending: "Pendiente",
  confirmed: "Confirmado",
  attended: "Asistió",
  no_show: "Ausente",
  cancelled: "Cancelado",
  rescheduled: "Reprogramado",
}

const closureLabels: Record<AppointmentClosureStatus, string> = {
  none: "Sin cerrar",
  paid: "Cobrado",
  pending: "Debe",
  partial: "Parcial",
  insurance_pending: "OS pendiente",
}

const statusVariant: Record<string, "default" | "secondary" | "success" | "warning" | "destructive" | "outline"> = {
  pending: "secondary",
  confirmed: "default",
  attended: "success",
  no_show: "destructive",
  cancelled: "outline",
  rescheduled: "outline",
}

const closureVariant: Record<string, "default" | "secondary" | "success" | "warning" | "destructive"> = {
  none: "warning",
  paid: "success",
  pending: "destructive",
  partial: "warning",
  insurance_pending: "secondary",
}

export function AppointmentStatusBadge({ status }: { status: AppointmentStatus }) {
  return <Badge variant={statusVariant[status] ?? "secondary"}>{statusLabels[status]}</Badge>
}

export function AttentionTypeBadge({
  attentionType,
  healthInsuranceName,
}: {
  attentionType: AttentionType
  healthInsuranceName?: string | null
}) {
  const label = attentionLabel(attentionType, healthInsuranceName)
  const isPrivate = attentionType === "private"
  return (
    <Badge
      variant={isPrivate ? "outline" : "secondary"}
      className={isPrivate ? "" : "bg-sky-500/15 text-sky-900 dark:text-sky-100 border-sky-500/30"}
    >
      {label}
    </Badge>
  )
}

export function ClosureStatusBadge({
  status,
  showUnclosed,
}: {
  status: AppointmentClosureStatus
  showUnclosed?: boolean
}) {
  if (status === "none") {
    if (showUnclosed) {
      return <Badge variant="warning">Sin cerrar</Badge>
    }
    return null
  }
  return <Badge variant={closureVariant[status] ?? "secondary"}>{closureLabels[status]}</Badge>
}
