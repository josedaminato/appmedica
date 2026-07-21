import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Activity,
  AlertTriangle,
  Building2,
  CheckCircle2,
  LogOut,
  RefreshCw,
  Trash2,
  Users,
} from "lucide-react"
import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { QueryErrorState } from "@/components/shared/QueryErrorState"
import { formatDate, formatDateTime, formatMoney } from "@/lib/format"
import { cn } from "@/lib/utils"
import {
  deleteTenant,
  getPlatformDashboard,
  getPlatformDiagnostics,
  markTenantPaid,
  type PlatformCheckResult,
  type PlatformTenantRow,
} from "../api"
import { usePlatformAuth } from "../PlatformAuthContext"

const STATUS_LABELS: Record<PlatformTenantRow["payment_status"], string> = {
  overdue: "Pago vencido",
  due_today: "Vence hoy",
  due_soon: "Vence pronto",
  current: "Al día",
  unknown: "Sin fecha",
}

function statusClass(status: PlatformTenantRow["payment_status"]) {
  if (status === "overdue" || status === "due_today") return "bg-destructive/10 text-destructive"
  if (status === "due_soon") return "bg-amber-500/15 text-amber-800 dark:text-amber-300"
  return "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
}

function checkStatusClass(status: string) {
  if (status === "error") return "border-destructive/40 bg-destructive/5"
  if (status === "warn") return "border-amber-500/40 bg-amber-500/5"
  return "border-emerald-500/30 bg-emerald-500/5"
}

function CheckRow({ check }: { check: PlatformCheckResult }) {
  return (
    <div className={cn("rounded-lg border p-3", checkStatusClass(check.status))}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium text-sm">{check.label}</p>
          <p className="mt-1 text-sm text-muted-foreground">{check.message}</p>
          {check.action && (
            <p className="mt-2 text-xs text-foreground/80">
              <strong>Qué hacer:</strong> {check.action}
            </p>
          )}
        </div>
        <span
          className={cn(
            "shrink-0 rounded-full px-2 py-0.5 text-xs font-medium",
            check.status === "error" && "bg-destructive/15 text-destructive",
            check.status === "warn" && "bg-amber-500/20 text-amber-900 dark:text-amber-200",
            check.status === "ok" && "bg-emerald-500/15 text-emerald-800 dark:text-emerald-200",
          )}
        >
          {check.status === "ok" ? "OK" : check.status === "warn" ? "Atención" : "Error"}
        </span>
      </div>
    </div>
  )
}

export function PlatformDashboardPage() {
  const { logout } = usePlatformAuth()
  const queryClient = useQueryClient()
  const [tenantToDelete, setTenantToDelete] = useState<PlatformTenantRow | null>(null)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["platform-dashboard"],
    queryFn: getPlatformDashboard,
    refetchInterval: 60_000,
  })

  const diagnostics = useQuery({
    queryKey: ["platform-diagnostics"],
    queryFn: getPlatformDiagnostics,
    refetchInterval: 60_000,
  })

  const markPaid = useMutation({
    mutationFn: (organizationId: string) => markTenantPaid(organizationId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["platform-dashboard"] }),
  })

  const removeTenant = useMutation({
    mutationFn: (organizationId: string) => deleteTenant(organizationId),
    onSuccess: () => {
      setTenantToDelete(null)
      queryClient.invalidateQueries({ queryKey: ["platform-dashboard"] })
    },
  })

  if (isLoading) return <LoadingSkeleton rows={6} />

  if (isError || !data) {
    return (
      <div className="min-h-screen bg-muted/30 p-4 sm:p-8">
        <QueryErrorState onRetry={() => refetch()} />
      </div>
    )
  }

  const dueTenants = data.tenants.filter((t) => t.payment_status === "overdue" || t.payment_status === "due_today")
  const diag = diagnostics.data

  return (
    <div className="min-h-screen bg-muted/30">
      <header className="border-b bg-background">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div>
            <p className="text-sm text-muted-foreground">Operación interna</p>
            <h1 className="text-xl font-semibold">Clientes AppMédica</h1>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link to="/">Sitio público</Link>
            </Button>
            <Button variant="ghost" size="sm" onClick={logout}>
              <LogOut className="mr-2 h-4 w-4" />
              Salir
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-6 sm:px-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
            <CardTitle className="flex items-center gap-2 text-base">
              <Activity className="h-5 w-5" />
              Diagnóstico del sistema
              {diag && (
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-xs font-medium",
                    diag.overall_status === "ok" && "bg-emerald-500/15 text-emerald-800",
                    diag.overall_status === "warn" && "bg-amber-500/20 text-amber-900",
                    diag.overall_status === "error" && "bg-destructive/15 text-destructive",
                  )}
                >
                  {diag.overall_status === "ok"
                    ? "Todo OK"
                    : diag.overall_status === "warn"
                      ? "Hay avisos"
                      : "Hay errores"}
                </span>
              )}
            </CardTitle>
            <Button
              size="sm"
              variant="outline"
              disabled={diagnostics.isFetching}
              onClick={() => diagnostics.refetch()}
            >
              <RefreshCw className={cn("mr-1 h-3.5 w-3.5", diagnostics.isFetching && "animate-spin")} />
              Revisar ahora
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Chequeos para detectar fallas de email, base de datos y configuración sin entrar al VPS.
              {diag?.checked_at ? ` Última revisión: ${formatDateTime(diag.checked_at)}.` : ""}
            </p>
            {diagnostics.isLoading && <LoadingSkeleton rows={3} />}
            {diagnostics.isError && (
              <p className="text-sm text-destructive">No se pudo cargar el diagnóstico. Probá “Revisar ahora”.</p>
            )}
            {diag && (
              <>
                <div className="grid gap-2">
                  {diag.checks.map((c) => (
                    <CheckRow key={c.key} check={c} />
                  ))}
                </div>
                {(diag.error_count_window > 0 || diag.recent_errors.length > 0) && (
                  <div className="pt-2">
                    <p className="mb-2 text-sm font-medium">
                      Errores recientes ({diag.error_count_window} en memoria)
                    </p>
                    <div className="max-h-56 space-y-2 overflow-y-auto">
                      {diag.recent_errors.length === 0 ? (
                        <p className="text-sm text-muted-foreground">Sin eventos recientes en este proceso.</p>
                      ) : (
                        diag.recent_errors.map((ev) => (
                          <div key={ev.id} className="rounded-md border bg-background p-2 text-xs">
                            <div className="flex flex-wrap gap-2 text-muted-foreground">
                              <span>{formatDateTime(ev.created_at)}</span>
                              <span className="font-medium text-foreground">{ev.code}</span>
                              <span>{ev.source}</span>
                              {ev.path && <span>{ev.path}</span>}
                            </div>
                            <p className="mt-1 text-sm">{ev.message}</p>
                            {ev.detail && (
                              <p className="mt-1 break-all font-mono text-[11px] text-muted-foreground">
                                {ev.detail}
                              </p>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {dueTenants.length > 0 && (
          <Card className="border-destructive/40 bg-destructive/5">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base text-destructive">
                <AlertTriangle className="h-5 w-5" />
                Cobros pendientes ({dueTenants.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              {dueTenants.map((t) => (
                <p key={t.id}>
                  <strong>{t.name}</strong>
                  {t.owner_email ? ` — ${t.owner_email}` : ""}
                  {t.paid_until ? ` · venció ${formatDate(t.paid_until)}` : ""}
                </p>
              ))}
            </CardContent>
          </Card>
        )}

        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Building2 className="h-4 w-4" />
                Clientes
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold">{data.total_clients}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <AlertTriangle className="h-4 w-4" />
                Deben pagar
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold text-destructive">{data.payments_due}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Users className="h-4 w-4" />
                Vencen esta semana
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold">{data.due_soon}</p>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Consultorios</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b text-muted-foreground">
                  <th className="pb-3 pr-4 font-medium">Consultorio</th>
                  <th className="pb-3 pr-4 font-medium">Dueño</th>
                  <th className="pb-3 pr-4 font-medium">Inicio</th>
                  <th className="pb-3 pr-4 font-medium">Vence</th>
                  <th className="pb-3 pr-4 font-medium">Cuota</th>
                  <th className="pb-3 pr-4 font-medium">Estado</th>
                  <th className="pb-3 pr-4 font-medium">Uso</th>
                  <th className="pb-3 font-medium" />
                </tr>
              </thead>
              <tbody>
                {data.tenants.map((tenant) => (
                  <tr key={tenant.id} className="border-b last:border-0">
                    <td className="py-3 pr-4 font-medium">{tenant.name}</td>
                    <td className="py-3 pr-4">
                      <div>{tenant.owner_name ?? "—"}</div>
                      <div className="text-muted-foreground">{tenant.owner_email ?? ""}</div>
                    </td>
                    <td className="py-3 pr-4">{formatDate(tenant.service_started_at)}</td>
                    <td className="py-3 pr-4">{tenant.paid_until ? formatDate(tenant.paid_until) : "—"}</td>
                    <td className="py-3 pr-4">{formatMoney(Number(tenant.monthly_fee))}</td>
                    <td className="py-3 pr-4">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium",
                          statusClass(tenant.payment_status),
                        )}
                      >
                        {tenant.payment_status === "current" && <CheckCircle2 className="h-3.5 w-3.5" />}
                        {STATUS_LABELS[tenant.payment_status]}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-muted-foreground">
                      {tenant.patients_count} pac. · {tenant.appointments_count} turnos
                    </td>
                    <td className="py-3">
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={markPaid.isPending || removeTenant.isPending}
                          onClick={() => markPaid.mutate(tenant.id)}
                        >
                          Registrar pago
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          disabled={markPaid.isPending || removeTenant.isPending}
                          onClick={() => setTenantToDelete(tenant)}
                        >
                          <Trash2 className="mr-1 h-3.5 w-3.5" />
                          Eliminar
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {data.tenants.length === 0 && (
              <p className="py-8 text-center text-muted-foreground">Todavía no hay consultorios cargados.</p>
            )}
          </CardContent>
        </Card>
      </main>

      <Dialog open={tenantToDelete !== null} onOpenChange={(open) => !open && setTenantToDelete(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>¿Eliminar este cliente?</DialogTitle>
            <p className="text-sm text-muted-foreground">
              Se borrará permanentemente el consultorio <strong>{tenantToDelete?.name}</strong>, sus usuarios,
              pacientes, turnos y todo el historial. Esta acción no se puede deshacer.
            </p>
          </DialogHeader>
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button variant="outline" onClick={() => setTenantToDelete(null)} disabled={removeTenant.isPending}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              disabled={removeTenant.isPending}
              onClick={() => tenantToDelete && removeTenant.mutate(tenantToDelete.id)}
            >
              {removeTenant.isPending ? "Eliminando..." : "Sí, eliminar"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
