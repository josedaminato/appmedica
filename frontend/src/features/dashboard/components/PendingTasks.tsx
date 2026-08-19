import { Link } from "react-router-dom"
import { CheckCircle2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { formatMoney } from "@/lib/format"
import type { DashboardAlerts, DashboardSummary } from "@/types/api"

type Props = {
  summary: DashboardSummary
  alerts?: DashboardAlerts
}

function plural(n: number, one: string, many: string) {
  return n === 1 ? one : many
}

export function PendingTasks({ summary, alerts }: Props) {
  const oldClaimsTotal = alerts?.old_insurance_claims.total_count ?? 0
  const oldDays = alerts?.old_insurance_claims.threshold_days ?? 45

  const items = [
    summary.unclosed_attended > 0 && {
      id: "unclosed",
      text:
        summary.unclosed_attended === 1
          ? "Tenés 1 turno que asistió y todavía no está cerrado."
          : `Tenés ${summary.unclosed_attended} turnos que asistieron y todavía no están cerrados.`,
      href: "/agenda/resolver?kind=unclosed",
      cta: "Ver turnos",
    },
    summary.overdue_unresolved > 0 && {
      id: "overdue",
      text: `Tenés ${summary.overdue_unresolved} ${plural(summary.overdue_unresolved, "turno", "turnos")} que ya pasaron y no se resolvieron.`,
      href: "/agenda/resolver?kind=overdue",
      cta: "Ver agenda",
    },
    summary.upcoming_unconfirmed > 0 && {
      id: "unconfirmed",
      text: `Tenés ${summary.upcoming_unconfirmed} ${plural(summary.upcoming_unconfirmed, "turno próximo", "turnos próximos")} sin confirmar.`,
      href: "/agenda",
      cta: "Ver agenda",
    },
    summary.patients_with_debt > 0 && {
      id: "payments",
      text: `Hay ${summary.patients_with_debt} ${plural(summary.patients_with_debt, "paciente", "pacientes")} con pagos pendientes. ${formatMoney(summary.private_debt_total)} pendientes.`,
      href: "/payments?tab=pending",
      cta: "Ver pendientes",
    },
    oldClaimsTotal > 0 && {
      id: "old-claims",
      text: `Tenés ${oldClaimsTotal} ${plural(oldClaimsTotal, "reclamo", "reclamos")} con ${oldDays} días o más.`,
      href: `/insurances?tab=claims&min_days=${oldDays}`,
      cta: "Ver reclamos",
    },
  ].filter(Boolean) as { id: string; text: string; href: string; cta: string }[]

  if (items.length === 0) {
    if (!alerts) return null
    return (
      <Card className="mb-8 border-emerald-500/30 bg-emerald-500/5">
        <CardContent className="flex items-start gap-3 pt-6">
          <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-700 dark:text-emerald-400 mt-0.5" />
          <div>
            <p className="font-medium">Todo al día</p>
            <p className="text-sm text-muted-foreground">Hoy no tenés pendientes administrativos.</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="mb-8">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        Para resolver hoy
      </h2>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Pendientes administrativos</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex flex-col gap-2 border-b pb-3 last:border-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
            >
              <p className="text-sm">{item.text}</p>
              <Button asChild size="sm" variant="outline" className="shrink-0 self-start sm:self-auto">
                <Link to={item.href}>{item.cta}</Link>
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
