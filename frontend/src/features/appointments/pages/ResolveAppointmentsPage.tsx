import { useMemo, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { FeedbackBanner } from "@/components/shared/FeedbackBanner"
import { PageHeader } from "@/components/shared/PageHeader"
import {
  AppointmentStatusBadge,
  AttentionTypeBadge,
  ClosureStatusBadge,
} from "@/components/shared/StatusBadge"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { EmptyState } from "@/components/shared/EmptyState"
import { QueryErrorState } from "@/components/shared/QueryErrorState"
import {
  appointmentDurationMinutes,
  formatDate,
  formatMoney,
  formatTimeRange,
  isoToLocalDateParam,
} from "@/lib/format"
import { ApiError } from "@/lib/api-client"
import type { Appointment, AppointmentClosureStatus } from "@/types/api"
import { listHealthInsurances } from "@/features/insurances/api"
import * as apptApi from "../api"
import type { ToResolveKind } from "../api"
import { CloseAppointmentDialog } from "../components/CloseAppointmentDialog"
import { AddPaymentDialog } from "../components/AddPaymentDialog"
import {
  RescheduleAppointmentDialog,
  type ReschedulePayload,
} from "../components/RescheduleAppointmentDialog"

const CLOSURE_SUCCESS: Record<AppointmentClosureStatus, string> = {
  none: "",
  paid: "Turno cerrado como cobrado",
  pending: "Turno cerrado — pendiente de cobro",
  partial: "Cobro parcial registrado",
  insurance_pending: "Turno cerrado — obra social pendiente",
}

function isToResolveKind(value: string | null): value is ToResolveKind {
  return value === "unclosed" || value === "overdue"
}

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["appointments"] })
  qc.invalidateQueries({ queryKey: ["appointments-to-resolve"] })
  qc.invalidateQueries({ queryKey: ["dashboard"] })
  qc.invalidateQueries({ queryKey: ["dashboard-alerts"] })
  qc.invalidateQueries({ queryKey: ["patient-admin"] })
}

type RowAction = {
  id: string
  label: string
  variant?: "default" | "secondary" | "outline" | "ghost" | "destructive"
  primary?: boolean
}

function buildActions(a: Appointment): RowAction[] {
  const actions: RowAction[] = []
  const needsClose = a.status === "attended" && a.closure_status === "none"

  if (a.status === "pending") {
    actions.push({ id: "confirm", label: "Confirmar", variant: "secondary", primary: true })
  }
  if (a.status === "pending" || a.status === "confirmed") {
    actions.push({
      id: "attend",
      label: "Asistió",
      primary: a.status === "confirmed",
    })
    actions.push({ id: "no_show", label: "Ausente", variant: "outline" })
    actions.push({ id: "reschedule", label: "Reprogramar", variant: "ghost" })
    actions.push({ id: "cancel", label: "Cancelar", variant: "ghost" })
  }
  if (needsClose) {
    actions.push({ id: "close", label: "Cerrar", primary: true })
  }
  if (a.closure_status === "pending" || a.closure_status === "partial") {
    actions.push({
      id: "payment",
      label: "Cobrar",
      variant: "outline",
      primary: !needsClose && a.status !== "pending" && a.status !== "confirmed",
    })
  }
  if (!actions.some((act) => act.primary) && actions.length > 0) actions[0].primary = true
  return actions
}

export function ResolveAppointmentsPage() {
  const qc = useQueryClient()
  const [searchParams] = useSearchParams()
  const rawKind = searchParams.get("kind")
  const kind = isToResolveKind(rawKind) ? rawKind : null

  const [closeTarget, setCloseTarget] = useState<Appointment | null>(null)
  const [paymentTarget, setPaymentTarget] = useState<Appointment | null>(null)
  const [rescheduleTarget, setRescheduleTarget] = useState<Appointment | null>(null)
  const [actionError, setActionError] = useState("")
  const [actionSuccess, setActionSuccess] = useState("")

  const { data: appointments = [], isLoading, isError, error, refetch } = useQuery({
    queryKey: ["appointments-to-resolve", kind],
    queryFn: () => apptApi.listAppointmentsToResolve(kind!),
    enabled: kind != null,
  })

  const { data: insurances = [] } = useQuery({
    queryKey: ["insurances"],
    queryFn: () => listHealthInsurances(),
    enabled: kind != null,
  })

  const title = kind === "overdue" ? "Turnos vencidos" : "Turnos sin cerrar"
  const description =
    kind === "overdue"
      ? "Turnos que ya pasaron y siguen pendientes o confirmados, de cualquier fecha."
      : "Turnos que asistieron y todavía no tienen cierre administrativo, de cualquier fecha."

  const action = useMutation({
    mutationFn: async ({ id, action: act }: { id: string; action: string }) => {
      if (act === "confirm") return apptApi.confirmAppointment(id)
      if (act === "attend") return apptApi.attendAppointment(id)
      if (act === "no_show") return apptApi.noShowAppointment(id)
      if (act === "cancel") return apptApi.cancelAppointment(id)
    },
    onSuccess: (data, variables) => {
      setActionError("")
      invalidateAll(qc)
      if (variables.action === "confirm") setActionSuccess("Turno confirmado")
      if (variables.action === "cancel") setActionSuccess("Turno cancelado")
      if (variables.action === "no_show") setActionSuccess("Marcado como ausente")
      if (variables.action === "attend" && data && "status" in (data as object)) {
        setActionSuccess("Paciente asistió — completá el cierre")
        setCloseTarget(data as Appointment)
      }
    },
    onError: (err) => {
      setActionError(err instanceof ApiError ? err.message : "Error en la acción")
    },
  })

  const rescheduleMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: ReschedulePayload }) =>
      apptApi.rescheduleAppointment(id, data),
    onSuccess: (newAppt) => {
      setRescheduleTarget(null)
      setActionError("")
      invalidateAll(qc)
      setActionSuccess(`Turno reprogramado al ${formatDate(newAppt.start_at)}`)
    },
    onError: (err) => {
      setActionError(err instanceof ApiError ? err.message : "Error al reprogramar")
    },
  })

  const closeMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: apptApi.ClosePayload }) =>
      apptApi.closeAppointment(id, data),
    onSuccess: (_data, variables) => {
      setCloseTarget(null)
      setActionError("")
      setActionSuccess(CLOSURE_SUCCESS[variables.data.closure_type] || "Turno cerrado")
      invalidateAll(qc)
    },
    onError: (err) => {
      setActionError(err instanceof ApiError ? err.message : "Error al cerrar turno")
    },
  })

  const paymentMutation = useMutation({
    mutationFn: ({ id, amount, method }: { id: string; amount: number; method: string }) =>
      apptApi.addPaymentToAppointment(id, { amount, method }),
    onSuccess: () => {
      setPaymentTarget(null)
      setActionError("")
      setActionSuccess("Cobro registrado correctamente")
      invalidateAll(qc)
    },
    onError: (err) => {
      setActionError(err instanceof ApiError ? err.message : "Error al registrar cobro")
    },
  })

  const pending = action.isPending || closeMutation.isPending || paymentMutation.isPending || rescheduleMutation.isPending

  function handleAction(appointment: Appointment, act: string) {
    if (act === "close") {
      setCloseTarget(appointment)
      return
    }
    if (act === "payment") {
      setPaymentTarget(appointment)
      return
    }
    if (act === "reschedule") {
      setRescheduleTarget(appointment)
      return
    }
    action.mutate({ id: appointment.id, action: act })
  }

  const emptyTitle = kind === "overdue" ? "No hay turnos vencidos" : "No hay turnos sin cerrar"
  const emptyDescription =
    kind === "overdue"
      ? "Cuando un turno pase y siga pendiente o confirmado, va a aparecer acá."
      : "Cuando un paciente asista y falte el cierre, el turno va a aparecer acá."

  return (
    <div>
      <PageHeader
        title={kind ? title : "A resolver"}
        description={kind ? description : "Elegí qué pendientes querés resolver."}
        action={
          <Button asChild variant="outline" size="sm">
            <Link to="/inicio">
              <ArrowLeft className="h-4 w-4 mr-1" />
              Volver al inicio
            </Link>
          </Button>
        }
      />

      {actionSuccess && <FeedbackBanner message={actionSuccess} variant="success" />}
      {actionError && <FeedbackBanner message={actionError} variant="error" />}

      {!kind && (
        <EmptyState
          title="Falta el tipo de pendientes"
          description="Entrá desde Inicio para ver turnos sin cerrar o vencidos."
        />
      )}

      {kind && isLoading && <LoadingSkeleton rows={4} />}
      {kind && isError && <QueryErrorState error={error} onRetry={() => refetch()} />}
      {kind && !isLoading && !isError && appointments.length === 0 && (
        <EmptyState title={emptyTitle} description={emptyDescription} />
      )}
      {kind && !isLoading && !isError && appointments.length > 0 && (
        <ul className="space-y-3">
          {appointments.map((a) => (
            <ResolveRow
              key={a.id}
              appointment={a}
              disabled={pending}
              onAction={(act) => handleAction(a, act)}
            />
          ))}
        </ul>
      )}

      <CloseAppointmentDialog
        open={!!closeTarget}
        onOpenChange={(o) => !o && setCloseTarget(null)}
        appointment={closeTarget}
        insurances={insurances}
        onSubmit={async (data) => {
          if (closeTarget) await closeMutation.mutateAsync({ id: closeTarget.id, data })
        }}
        loading={closeMutation.isPending}
      />
      <AddPaymentDialog
        open={!!paymentTarget}
        onOpenChange={(o) => !o && setPaymentTarget(null)}
        patientName={
          paymentTarget?.patient
            ? `${paymentTarget.patient.last_name}, ${paymentTarget.patient.first_name}`
            : undefined
        }
        onSubmit={async (amount, method) => {
          if (paymentTarget) await paymentMutation.mutateAsync({ id: paymentTarget.id, amount, method })
        }}
        loading={paymentMutation.isPending}
      />
      <RescheduleAppointmentDialog
        open={!!rescheduleTarget}
        onOpenChange={(o) => !o && setRescheduleTarget(null)}
        appointment={rescheduleTarget}
        onSubmit={async (data) => {
          if (rescheduleTarget) await rescheduleMutation.mutateAsync({ id: rescheduleTarget.id, data })
        }}
        loading={rescheduleMutation.isPending}
      />
    </div>
  )
}

function ResolveRow({
  appointment: a,
  disabled,
  onAction,
}: {
  appointment: Appointment
  disabled: boolean
  onAction: (action: string) => void
}) {
  const needsClose = a.status === "attended" && a.closure_status === "none"
  const patientName = a.patient
    ? `${a.patient.last_name}, ${a.patient.first_name}`
    : "Paciente"
  const actions = useMemo(() => buildActions(a), [a])
  const agendaDate = isoToLocalDateParam(a.start_at)

  return (
    <li className="flex flex-col gap-3 rounded-lg border p-3 bg-card sm:flex-row sm:items-center">
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium">{formatDate(a.start_at)}</span>
          <span className="text-sm tabular-nums">
            {formatTimeRange(a.start_at, a.end_at)}
            <span className="text-muted-foreground font-normal ml-1">
              ({appointmentDurationMinutes(a.start_at, a.end_at)} min)
            </span>
          </span>
          <Link to={`/patients/${a.patient_id}`} className="font-medium hover:text-primary truncate">
            {patientName}
          </Link>
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          <AttentionTypeBadge
            attentionType={a.attention_type}
            healthInsuranceName={a.health_insurance?.name}
          />
          <AppointmentStatusBadge status={a.status} />
          <ClosureStatusBadge status={a.closure_status} showUnclosed={needsClose} />
          {a.professional?.full_name && (
            <Badge variant="outline">{a.professional.full_name}</Badge>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          {a.expected_amount ? `${formatMoney(a.expected_amount)} · ` : null}
          <Link to={`/agenda?date=${agendaDate}`} className="hover:text-primary">
            Ver en agenda
          </Link>
        </p>
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-1">
        {actions.map((action) => (
          <Button
            key={action.id}
            size="sm"
            variant={action.variant ?? "default"}
            className={action.id === "cancel" ? "text-destructive hover:text-destructive" : undefined}
            disabled={disabled}
            onClick={() => onAction(action.id)}
          >
            {action.label}
          </Button>
        ))}
      </div>
    </li>
  )
}
