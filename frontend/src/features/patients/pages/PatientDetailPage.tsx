import { useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, Pencil, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { QueryErrorState } from "@/components/shared/QueryErrorState"
import { AppointmentStatusBadge, ClosureStatusBadge } from "@/components/shared/StatusBadge"
import { formatDate, formatMoney, formatTime } from "@/lib/format"
import { ApiError } from "@/lib/api-client"
import { useRoleScope } from "@/hooks/use-role-scope"
import { PatientFormDialog } from "../components/PatientFormDialog"
import * as patientsApi from "../api"

export function PatientDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { isStaff } = useRoleScope()
  const [editOpen, setEditOpen] = useState(false)
  const [error, setError] = useState("")

  const { data: patient, isLoading, isError, error: queryError, refetch } = useQuery({
    queryKey: ["patient", id],
    queryFn: () => patientsApi.getPatient(id!),
    enabled: !!id,
  })

  const { data: admin } = useQuery({
    queryKey: ["patient-admin", id],
    queryFn: () => patientsApi.getPatientAdminSummary(id!),
    enabled: !!id,
  })

  const updateMutation = useMutation({
    mutationFn: (payload: patientsApi.PatientPayload) =>
      patientsApi.updatePatient(id!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patient", id] })
      queryClient.invalidateQueries({ queryKey: ["patient-admin", id] })
      queryClient.invalidateQueries({ queryKey: ["patients"] })
      setEditOpen(false)
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Error al guardar"),
  })

  const deleteMutation = useMutation({
    mutationFn: () => patientsApi.deletePatient(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patients"] })
      navigate("/patients")
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Error al eliminar"),
  })

  if (isLoading) return <LoadingSkeleton rows={4} />
  if (isError) {
    return (
      <QueryErrorState
        title={queryError instanceof ApiError && queryError.status === 404 ? "Paciente no encontrado" : undefined}
        error={queryError}
        onRetry={() => refetch()}
      />
    )
  }
  if (!patient) return <p className="text-muted-foreground">Paciente no encontrado</p>

  return (
    <div>
      <div className="mb-6 flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/patients"><ArrowLeft className="h-4 w-4" /></Link>
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-semibold">{patient.last_name}, {patient.first_name}</h1>
          <p className="text-sm text-muted-foreground">DNI {patient.dni}</p>
        </div>
        <Badge variant={patient.is_active ? "success" : "secondary"}>
          {patient.is_active ? "Activo" : "Inactivo"}
        </Badge>
      </div>

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}

      {admin && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-6">
          <SummaryCard label="Deuda particular" value={formatMoney(admin.private_debt)} alert={Number(admin.private_debt) > 0} />
          <SummaryCard label="Deuda obra social" value={formatMoney(admin.insurance_debt)} alert={Number(admin.insurance_debt) > 0} />
          <SummaryCard label="Ausencias totales" value={String(admin.no_show_count)} />
          <SummaryCard label="Ausencias (30 d)" value={String(admin.no_shows_last_30_days)} />
        </div>
      )}

      <div className="mb-4 flex gap-2">
        <Button variant="outline" onClick={() => setEditOpen(true)}>
          <Pencil className="h-4 w-4 mr-2" />Editar
        </Button>
        {!isStaff && (
          <Button
            variant="destructive"
            onClick={() => { if (confirm("¿Dar de baja?")) deleteMutation.mutate() }}
            disabled={deleteMutation.isPending}
          >
            <Trash2 className="h-4 w-4 mr-2" />Dar de baja
          </Button>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Información</CardTitle></CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2 text-sm">
            <Info label="Teléfono" value={patient.phone} />
            <Info label="Email" value={patient.email} />
            <Info label="Nacimiento" value={patient.birth_date ? formatDate(patient.birth_date) : null} />
            <Info label="Nº afiliado" value={patient.affiliate_number} />
            <Info label="Observaciones" value={patient.notes} className="sm:col-span-2" />
          </CardContent>
        </Card>

        {admin && (
          <Card>
            <CardHeader><CardTitle className="text-base">Próximos turnos</CardTitle></CardHeader>
            <CardContent>
              {admin.upcoming_appointments.length === 0 ? (
                <p className="text-sm text-muted-foreground">Sin turnos próximos</p>
              ) : (
                <ul className="space-y-2 text-sm">
                  {admin.upcoming_appointments.map((a) => (
                    <li key={a.id} className="flex justify-between">
                      <span>{formatDate(a.start_at)} {formatTime(a.start_at)}</span>
                      <AppointmentStatusBadge status={a.status} />
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {admin && (
        <>
          <Card className="mt-6">
            <CardHeader><CardTitle className="text-base">Timeline administrativa</CardTitle></CardHeader>
            <CardContent>
              {admin.timeline.length === 0 ? (
                <p className="text-sm text-muted-foreground">Sin actividad registrada</p>
              ) : (
                <ul className="space-y-3">
                  {admin.timeline.map((e) => (
                    <li key={`${e.event_type}-${e.id}`} className="flex gap-3 text-sm border-l-2 border-primary/30 pl-3">
                      <div className="flex-1">
                        <p className="font-medium">{e.title}</p>
                        {e.subtitle && <p className="text-muted-foreground">{e.subtitle}</p>}
                      </div>
                      <div className="text-right text-muted-foreground shrink-0">
                        {e.amount && <p>{formatMoney(e.amount)}</p>}
                        <p className="text-xs">{formatDate(e.occurred_at)}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2 mt-6">
            <Card>
              <CardHeader><CardTitle className="text-base">Historial de turnos</CardTitle></CardHeader>
              <CardContent className="space-y-2 text-sm">
                {admin.recent_appointments.map((a) => (
                  <div key={a.id} className="flex justify-between items-center border-b pb-2 last:border-0">
                    <span>{formatDate(a.start_at)} — {a.status === "attended" ? "Asistió" : a.status}</span>
                    <ClosureStatusBadge status={a.closure_status} />
                  </div>
                ))}
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">Últimos pagos</CardTitle></CardHeader>
              <CardContent className="space-y-2 text-sm">
                {admin.recent_payments.length === 0 ? (
                  <p className="text-muted-foreground">Sin pagos</p>
                ) : (
                  admin.recent_payments.map((p) => (
                    <div key={p.id} className="flex justify-between border-b pb-2">
                      <span>{p.method} — {p.status}</span>
                      <span className="font-medium">{formatMoney(p.amount)}</span>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}

      <PatientFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        patient={patient}
        onSubmit={async (payload) => updateMutation.mutateAsync(payload)}
        loading={updateMutation.isPending}
      />
    </div>
  )
}

function SummaryCard({ label, value, alert }: { label: string; value: string; alert?: boolean }) {
  return (
    <Card className={alert ? "border-destructive/40 bg-destructive/5" : ""}>
      <CardContent className="pt-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-xl font-bold mt-1">{value}</p>
      </CardContent>
    </Card>
  )
}

function Info({ label, value, className }: { label: string; value: string | null; className?: string }) {
  return (
    <div className={className}>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium">{value || "—"}</p>
    </div>
  )
}
