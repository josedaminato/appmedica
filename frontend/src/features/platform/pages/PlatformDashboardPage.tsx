import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AlertTriangle, Building2, CheckCircle2, LogOut, Trash2, Users } from "lucide-react"
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
import { formatDate, formatMoney } from "@/lib/format"
import { cn } from "@/lib/utils"
import { deleteTenant, getPlatformDashboard, markTenantPaid, type PlatformTenantRow } from "../api"
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

export function PlatformDashboardPage() {
  const { logout } = usePlatformAuth()
  const queryClient = useQueryClient()
  const [tenantToDelete, setTenantToDelete] = useState<PlatformTenantRow | null>(null)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["platform-dashboard"],
    queryFn: getPlatformDashboard,
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
              Se borrará permanentemente el consultorio{" "}
              <strong>{tenantToDelete?.name}</strong>, sus usuarios, pacientes, turnos y todo el historial. Esta acción
              no se puede deshacer.
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
