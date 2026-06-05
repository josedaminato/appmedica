import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import {
  AlertCircle,
  Calendar,
  CreditCard,
  Shield,
  UserX,
  ClipboardList,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { AppointmentStatusBadge, AttentionTypeBadge } from "@/components/shared/StatusBadge"
import { formatMoney, formatTime } from "@/lib/format"
import { Badge } from "@/components/ui/badge"
import { getDashboardAlerts, getDashboardSummary } from "./api"

export function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboardSummary,
    refetchInterval: 60_000,
  })

  const { data: alerts } = useQuery({
    queryKey: ["dashboard-alerts"],
    queryFn: () => getDashboardAlerts(45),
    refetchInterval: 60_000,
  })

  if (isLoading) return <LoadingSkeleton rows={4} />

  const d = data!

  return (
    <div>
      <PageHeader
        title="Inicio"
        description="Estado administrativo y económico de tu consultorio."
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 mb-6">
        <MetricCard
          title="Turnos hoy"
          value={String(d.appointments_today)}
          icon={Calendar}
          href="/agenda"
        />
        <MetricCard
          title="Sin cerrar administrativamente"
          value={String(d.unclosed_attended)}
          icon={ClipboardList}
          highlight={d.unclosed_attended > 0}
          href="/agenda?status=attended&closure=none"
          subtitle="Asistieron pero falta el cierre"
        />
        <MetricCard
          title="Turnos vencidos sin resolver"
          value={String(d.overdue_unresolved)}
          icon={AlertCircle}
          highlight={d.overdue_unresolved > 0}
          href="/agenda?status=pending"
        />
        <MetricCard
          title="Deuda particulares"
          value={formatMoney(d.private_debt_total)}
          icon={CreditCard}
          highlight={Number(d.private_debt_total) > 0}
          href="/payments?tab=private"
        />
        <MetricCard
          title="Deuda obras sociales"
          value={formatMoney(d.insurance_debt_total)}
          icon={Shield}
          highlight={Number(d.insurance_debt_total) > 0}
          href="/insurances?tab=claims"
        />
        <MetricCard
          title="Pacientes con deuda"
          value={String(d.patients_with_debt)}
          icon={AlertCircle}
          highlight={d.patients_with_debt > 0}
          href="/payments?tab=pending"
        />
        <MetricCard
          title="Prestaciones OS pendientes"
          value={String(d.pending_insurance_claims)}
          icon={Shield}
          href="/insurances?tab=claims"
        />
        <MetricCard
          title="Ausencias (30 días)"
          value={String(d.no_shows_last_30_days)}
          icon={UserX}
        />
      </div>

      <div className="mb-6">
        <h2 className="text-sm font-semibold text-foreground mb-2">Alertas operativas</h2>
        {!alerts ? (
          <div className="rounded-xl border bg-muted/20 p-4 text-sm text-muted-foreground">
            Cargando alertas…
          </div>
        ) : (
          <div className="grid gap-3 lg:grid-cols-2">
            <AlertCard
              title="Turnos sin cerrar"
              value={alerts.unclosed_attended.count}
              highlight={alerts.unclosed_attended.count > 0}
              href="/agenda?status=attended&closure=none"
              subtitle="Asistieron pero falta cierre"
            />
            <AlertCard
              title="Cobros parciales pendientes"
              value={alerts.partial_payments_pending.count}
              highlight={alerts.partial_payments_pending.count > 0}
              href="/payments?tab=private"
              subtitle={`${formatMoney(alerts.partial_payments_pending.pending_total)} pendientes`}
            />
            <AlertCard
              title="Reclamos OS viejos"
              value={alerts.old_insurance_claims.items.length}
              highlight={alerts.old_insurance_claims.items.length > 0}
              href="/insurances?tab=claims"
              subtitle={`> ${alerts.old_insurance_claims.threshold_days} días`}
            />
            <AlertCard
              title="Pacientes con deuda alta"
              value={alerts.top_debt_patients.items.length}
              highlight={alerts.top_debt_patients.items.length > 0}
              href="/payments?tab=pending"
              subtitle="Top de deuda acumulada"
            />
          </div>
        )}
      </div>

      {alerts && (
        <div className="grid gap-4 lg:grid-cols-2 mb-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Reclamos OS viejos</CardTitle>
              <Link to="/insurances" className="text-sm text-primary hover:underline">
                Ver reclamos
              </Link>
            </CardHeader>
            <CardContent>
              {alerts.old_insurance_claims.items.length === 0 ? (
                <p className="text-sm text-muted-foreground">No hay reclamos viejos.</p>
              ) : (
                <ul className="space-y-2">
                  {alerts.old_insurance_claims.items.slice(0, 4).map((it) => (
                    <li key={it.health_insurance_id} className="flex items-center justify-between text-sm border-b last:border-0 pb-2 last:pb-0">
                      <div className="min-w-0">
                        <p className="font-medium truncate">{it.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {it.claims_count} reclamos · {formatMoney(it.debt_total)} · prom {it.avg_days_pending} d
                        </p>
                      </div>
                      <Badge variant="warning">Viejos</Badge>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Pacientes con deuda alta</CardTitle>
              <Link to="/payments?tab=pending" className="text-sm text-primary hover:underline">
                Ver cobros
              </Link>
            </CardHeader>
            <CardContent>
              {alerts.top_debt_patients.items.length === 0 ? (
                <p className="text-sm text-muted-foreground">No hay deuda registrada.</p>
              ) : (
                <ul className="space-y-2">
                  {alerts.top_debt_patients.items.slice(0, 5).map((p) => (
                    <li key={p.patient_id} className="flex items-center justify-between text-sm border-b last:border-0 pb-2 last:pb-0">
                      <div className="min-w-0">
                        <Link to={`/patients/${p.patient_id}`} className="font-medium hover:text-primary truncate block">
                          {p.patient_name}
                        </Link>
                        <p className="text-xs text-muted-foreground">
                          Part {formatMoney(p.private_debt)} · OS {formatMoney(p.insurance_debt)}
                        </p>
                      </div>
                      <span className="font-semibold tabular-nums">{formatMoney(p.total_debt)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Próximos turnos</CardTitle>
          <Link to="/agenda" className="text-sm text-primary hover:underline">Ver agenda</Link>
        </CardHeader>
        <CardContent>
          {d.upcoming_appointments.length === 0 ? (
            <p className="text-sm text-muted-foreground">No hay turnos próximos</p>
          ) : (
            <ul className="space-y-2">
              {d.upcoming_appointments.map((a) => (
                <li key={a.id} className="flex items-center justify-between text-sm border-b last:border-0 pb-2 last:pb-0">
                  <div>
                    <span className="font-medium">{formatTime(a.start_at)}</span>
                    {" — "}
                    <Link to={`/patients/${a.patient_id}`} className="hover:text-primary">
                      {a.patient?.last_name}, {a.patient?.first_name}
                    </Link>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <AttentionTypeBadge
                      attentionType={a.attention_type}
                      healthInsuranceName={a.health_insurance?.name}
                    />
                    <AppointmentStatusBadge status={a.status} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function AlertCard({
  title,
  value,
  subtitle,
  href,
  highlight,
}: {
  title: string
  value: number
  subtitle?: string
  href: string
  highlight?: boolean
}) {
  const content = (
    <Card className={highlight ? "border-amber-500/40 bg-amber-500/5" : ""}>
      <CardContent className="pt-4 pb-3">
        <p className="text-xs text-muted-foreground">{title}</p>
        <p className="text-xl font-semibold tabular-nums mt-0.5">{value}</p>
        {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
      </CardContent>
    </Card>
  )
  return <Link to={href}>{content}</Link>
}

function MetricCard({
  title,
  value,
  icon: Icon,
  href,
  highlight,
  subtitle,
}: {
  title: string
  value: string
  icon: React.ComponentType<{ className?: string }>
  href?: string
  highlight?: boolean
  subtitle?: string
}) {
  const content = (
    <Card className={highlight ? "border-amber-500/50 bg-amber-500/5" : ""}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
      </CardContent>
    </Card>
  )
  return href ? <Link to={href}>{content}</Link> : content
}
