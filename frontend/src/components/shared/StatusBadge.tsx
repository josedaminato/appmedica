import { Badge } from "@/components/ui/badge"
import type { AppointmentClosureStatus, AppointmentStatus } from "@/types/api"

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
