import { useEffect, useMemo, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ChevronLeft, ChevronRight, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { FeedbackBanner } from "@/components/shared/FeedbackBanner"
import { PageHeader } from "@/components/shared/PageHeader"
import { AppointmentStatusBadge, ClosureStatusBadge } from "@/components/shared/StatusBadge"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { formatDate, formatMoney, formatTime, toDateParam } from "@/lib/format"
import { ApiError } from "@/lib/api-client"
import type {
  Appointment,
  AppointmentClosureStatus,
  AppointmentStatus,
} from "@/types/api"

const VALID_STATUSES = new Set<AppointmentStatus>([
  "pending",
  "confirmed",
  "attended",
  "no_show",
  "cancelled",
  "rescheduled",
])

const VALID_CLOSURES = new Set<AppointmentClosureStatus>([
  "none",
  "paid",
  "pending",
  "partial",
  "insurance_pending",
])

function readClosureParam(params: URLSearchParams): string {
  const raw = params.get("closure") ?? params.get("closure_status")
  if (raw && VALID_CLOSURES.has(raw as AppointmentClosureStatus)) return raw
  return "all"
}
import { listHealthInsurances } from "@/features/insurances/api"
import { listTeam } from "@/features/users/api"
import * as apptApi from "../api"
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

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["appointments"] })
  qc.invalidateQueries({ queryKey: ["dashboard"] })
  qc.invalidateQueries({ queryKey: ["patient-admin"] })
}

export function AgendaPage() {
  const qc = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialDate = searchParams.get("date")
  const initialStatus = searchParams.get("status")
  const [date, setDate] = useState(() =>
    initialDate ? new Date(initialDate + "T12:00:00") : new Date(),
  )
  const [view, setView] = useState<"day" | "week">("day")
  const [professionalId, setProfessionalId] = useState<string>(
    () => searchParams.get("professional_id") ?? "all",
  )
  const [statusFilter, setStatusFilter] = useState<string>(() =>
    initialStatus && VALID_STATUSES.has(initialStatus as AppointmentStatus)
      ? initialStatus
      : "all",
  )
  const [closureFilter, setClosureFilter] = useState<string>(() => readClosureParam(searchParams))
  const [search, setSearch] = useState(() => searchParams.get("q") ?? "")

  function syncUrl(updates: {
    date?: string
    status?: string
    closure?: string
    professional_id?: string
    q?: string
  }) {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (updates.date !== undefined) {
          if (updates.date) next.set("date", updates.date)
          else next.delete("date")
        }
        if (updates.status !== undefined) {
          if (updates.status && updates.status !== "all") next.set("status", updates.status)
          else next.delete("status")
        }
        if (updates.closure !== undefined) {
          if (updates.closure && updates.closure !== "all") next.set("closure", updates.closure)
          else next.delete("closure")
          next.delete("closure_status")
        }
        if (updates.professional_id !== undefined) {
          if (updates.professional_id && updates.professional_id !== "all") {
            next.set("professional_id", updates.professional_id)
          } else next.delete("professional_id")
        }
        if (updates.q !== undefined) {
          if (updates.q) next.set("q", updates.q)
          else next.delete("q")
        }
        return next
      },
      { replace: true },
    )
  }
  const [closeTarget, setCloseTarget] = useState<Appointment | null>(null)
  const [paymentTarget, setPaymentTarget] = useState<Appointment | null>(null)
  const [rescheduleTarget, setRescheduleTarget] = useState<Appointment | null>(null)
  const [actionError, setActionError] = useState("")
  const [actionSuccess, setActionSuccess] = useState("")

  useEffect(() => {
    if (!actionSuccess) return
    const t = setTimeout(() => setActionSuccess(""), 4500)
    return () => clearTimeout(t)
  }, [actionSuccess])

  const dateParam = toDateParam(date)

  const { data: appointments = [], isLoading } = useQuery({
    queryKey: [
      "appointments",
      dateParam,
      view,
      professionalId,
      statusFilter,
      closureFilter,
      search,
    ],
    queryFn: () =>
      apptApi.listAppointments({
        date: dateParam,
        view,
        professional_id: professionalId === "all" ? undefined : professionalId,
        status: statusFilter === "all" ? undefined : (statusFilter as AppointmentStatus),
        closure_status:
          closureFilter === "all" ? undefined : (closureFilter as AppointmentClosureStatus),
        patient_q: search || undefined,
      }),
  })

  const { data: team = [] } = useQuery({ queryKey: ["team"], queryFn: listTeam })
  const { data: insurances = [] } = useQuery({ queryKey: ["insurances"], queryFn: () => listHealthInsurances() })

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
      if (variables.action === "attend" && data) {
        setActionSuccess("Paciente asistió — completá el cierre")
        setCloseTarget(data)
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
      const d = toDateParam(new Date(newAppt.start_at))
      setDate(new Date(d + "T12:00:00"))
      setActionSuccess(`Turno reprogramado al ${formatDate(d)}`)
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

  const grouped = useMemo(() => {
    if (view === "day") return { [dateParam]: appointments }
    const groups: Record<string, Appointment[]> = {}
    for (const a of appointments) {
      const d = a.start_at.slice(0, 10)
      if (!groups[d]) groups[d] = []
      groups[d].push(a)
    }
    return groups
  }, [appointments, view, dateParam])

  function shiftDate(days: number) {
    const d = new Date(date)
    d.setDate(d.getDate() + days)
    setDate(d)
    syncUrl({ date: toDateParam(d) })
  }

  function handleDateChange(value: string) {
    setDate(new Date(value + "T12:00:00"))
    syncUrl({ date: value })
  }

  const patientLabel = (a: Appointment) =>
    a.patient ? `${a.patient.last_name}, ${a.patient.first_name}` : "Paciente"

  return (
    <div>
      <PageHeader
        title="Agenda"
        description="Gestioná turnos y cerrá el resultado administrativo en segundos."
        action={
          <Button size="sm" asChild>
            <Link to="/agenda/new"><Plus className="h-4 w-4 mr-1" />Nuevo turno</Link>
          </Button>
        }
      />

      {actionSuccess && <FeedbackBanner message={actionSuccess} variant="success" />}
      {actionError && <FeedbackBanner message={actionError} variant="error" />}

      <div className="mb-4 flex flex-wrap gap-2 items-center">
        <Button variant="outline" size="icon" onClick={() => shiftDate(view === "week" ? -7 : -1)}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <Input
          type="date"
          className="w-40"
          value={dateParam}
          onChange={(e) => handleDateChange(e.target.value)}
        />
        <Button variant="outline" size="icon" onClick={() => shiftDate(view === "week" ? 7 : 1)}>
          <ChevronRight className="h-4 w-4" />
        </Button>
        <Select value={view} onValueChange={(v) => setView(v as "day" | "week")}>
          <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="day">Día</SelectItem>
            <SelectItem value="week">Semana</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={professionalId}
          onValueChange={(v) => {
            setProfessionalId(v)
            syncUrl({ professional_id: v })
          }}
        >
          <SelectTrigger className="w-44"><SelectValue placeholder="Profesional" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            {team.map((m) => (
              <SelectItem key={m.id} value={m.id}>{m.full_name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={statusFilter}
          onValueChange={(v) => {
            setStatusFilter(v)
            syncUrl({ status: v })
          }}
        >
          <SelectTrigger className="w-36"><SelectValue placeholder="Estado" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="pending">Pendiente</SelectItem>
            <SelectItem value="confirmed">Confirmado</SelectItem>
            <SelectItem value="attended">Asistió</SelectItem>
            <SelectItem value="no_show">Ausente</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={closureFilter}
          onValueChange={(v) => {
            setClosureFilter(v)
            syncUrl({ closure: v })
          }}
        >
          <SelectTrigger className="w-40"><SelectValue placeholder="Cierre" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Cierre: todos</SelectItem>
            <SelectItem value="none">Sin cerrar</SelectItem>
            <SelectItem value="paid">Cobrado</SelectItem>
            <SelectItem value="pending">Pendiente cobro</SelectItem>
            <SelectItem value="partial">Cobro parcial</SelectItem>
            <SelectItem value="insurance_pending">OS pendiente</SelectItem>
          </SelectContent>
        </Select>
        <Input
          placeholder="Buscar paciente..."
          className="max-w-xs"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            syncUrl({ q: e.target.value })
          }}
        />
      </div>

      {isLoading ? (
        <LoadingSkeleton />
      ) : appointments.length === 0 ? (
        <div className="rounded-xl border border-dashed py-12 text-center">
          <p className="text-muted-foreground text-sm">No hay turnos en este período</p>
          <Button size="sm" className="mt-4" asChild>
            <Link to="/agenda/new">Crear turno</Link>
          </Button>
        </div>
      ) : (
        Object.entries(grouped)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([day, items]) => (
            <div key={day} className="mb-6">
              {view === "week" && (
                <h3 className="text-sm font-medium text-muted-foreground mb-2">{formatDate(day)}</h3>
              )}
              <div className="space-y-2">
                {items.map((a) => (
                  <AppointmentRow
                    key={a.id}
                    appointment={a}
                    onAction={(act) => {
                      if (act === "close") setCloseTarget(a)
                      else if (act === "payment") setPaymentTarget(a)
                      else if (act === "reschedule") setRescheduleTarget(a)
                      else action.mutate({ id: a.id, action: act })
                    }}
                    actionPending={action.isPending}
                  />
                ))}
              </div>
            </div>
          ))
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

      <RescheduleAppointmentDialog
        open={!!rescheduleTarget}
        onOpenChange={(o) => !o && setRescheduleTarget(null)}
        appointment={rescheduleTarget}
        onSubmit={async (data) => {
          if (rescheduleTarget) {
            await rescheduleMutation.mutateAsync({ id: rescheduleTarget.id, data })
          }
        }}
        loading={rescheduleMutation.isPending}
      />

      <AddPaymentDialog
        open={!!paymentTarget}
        onOpenChange={(o) => !o && setPaymentTarget(null)}
        patientName={paymentTarget ? patientLabel(paymentTarget) : undefined}
        onSubmit={async (amount, method) => {
          if (paymentTarget) {
            await paymentMutation.mutateAsync({ id: paymentTarget.id, amount, method })
          }
        }}
        loading={paymentMutation.isPending}
      />
    </div>
  )
}

function AppointmentRow({
  appointment: a,
  onAction,
  actionPending,
}: {
  appointment: Appointment
  onAction: (action: string) => void
  actionPending: boolean
}) {
  const needsClose = a.status === "attended" && a.closure_status === "none"
  const patientName = a.patient
    ? `${a.patient.last_name}, ${a.patient.first_name}`
    : "Paciente"

  const rowClass = needsClose
    ? "border-amber-500/40 bg-amber-500/5"
    : a.closure_status === "paid"
      ? "border-emerald-500/30"
      : a.closure_status === "pending" || a.closure_status === "partial"
        ? "border-red-500/20"
        : ""

  return (
    <div className={`flex flex-col sm:flex-row sm:items-center gap-3 rounded-lg border p-3 bg-card transition-colors ${rowClass}`}>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-sm tabular-nums">{formatTime(a.start_at)}</span>
          <Link to={`/patients/${a.patient_id}`} className="font-medium hover:text-primary truncate">
            {patientName}
          </Link>
          <AppointmentStatusBadge status={a.status} />
          <ClosureStatusBadge status={a.closure_status} showUnclosed={needsClose} />
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">
          {a.modality === "online" ? "Online" : "Presencial"} ·{" "}
          {a.attention_type === "health_insurance" ? "Obra social" : "Particular"}
          {a.expected_amount ? ` · ${formatMoney(a.expected_amount)}` : ""}
        </p>
      </div>
      <div className="flex flex-wrap gap-1 shrink-0">
        {a.status === "pending" && (
          <Button size="sm" variant="secondary" disabled={actionPending} onClick={() => onAction("confirm")}>
            Confirmar
          </Button>
        )}
        {(a.status === "pending" || a.status === "confirmed") && (
          <>
            <Button size="sm" disabled={actionPending} onClick={() => onAction("attend")}>
              Asistió
            </Button>
            <Button size="sm" variant="outline" disabled={actionPending} onClick={() => onAction("no_show")}>
              Ausente
            </Button>
            <Button size="sm" variant="ghost" disabled={actionPending} onClick={() => onAction("reschedule")}>
              Reprogramar
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="text-destructive hover:text-destructive"
              disabled={actionPending}
              onClick={() => onAction("cancel")}
            >
              Cancelar
            </Button>
          </>
        )}
        {a.status === "no_show" && (
          <Button size="sm" variant="ghost" disabled={actionPending} onClick={() => onAction("reschedule")}>
            Reprogramar
          </Button>
        )}
        {needsClose && (
          <Button size="sm" onClick={() => onAction("close")}>
            Cerrar
          </Button>
        )}
        {(a.closure_status === "pending" || a.closure_status === "partial") && (
          <Button size="sm" variant="outline" onClick={() => onAction("payment")}>
            Cobrar
          </Button>
        )}
      </div>
    </div>
  )
}
