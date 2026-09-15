import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatDate, formatTime } from "@/lib/format"
import type { Consultation } from "@/types/api"

type Props = {
  consultation: Consultation
  patientName: string
  appointmentStartAt?: string | null
  professionalName?: string | null
}

export function ConsultationReadOnlyView({
  consultation,
  patientName,
  appointmentStartAt,
  professionalName,
}: Props) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base">Consulta</CardTitle>
          <Badge variant={consultation.status === "finalized" ? "success" : "secondary"}>
            {consultation.status === "finalized" ? "Finalizada" : "Borrador"}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">{patientName}</p>
        {consultation.amends_id && consultation.amend_reason && (
          <p className="text-sm text-muted-foreground">
            Corrección · {consultation.amend_reason}
          </p>
        )}
        {(appointmentStartAt || consultation.occurred_at) && (
          <p className="text-sm text-muted-foreground">
            {formatDate(appointmentStartAt || consultation.occurred_at!)}{" "}
            {formatTime(appointmentStartAt || consultation.occurred_at!)}
            {professionalName ? ` · ${professionalName}` : ""}
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <Section title="Motivo de consulta" value={consultation.reason} />
        <Section title="Evolución / observaciones" value={consultation.evolution} large />
        <Section title="Diagnóstico" value={consultation.diagnosis} />
        <Section title="Indicaciones / tratamiento" value={consultation.indications} large />
      </CardContent>
    </Card>
  )
}

function Section({ title, value, large }: { title: string; value: string | null; large?: boolean }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">{title}</p>
      <p className={`whitespace-pre-wrap ${large ? "min-h-[4rem]" : ""}`}>
        {value?.trim() || "—"}
      </p>
    </div>
  )
}
