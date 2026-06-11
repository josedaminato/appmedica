import { useQuery } from "@tanstack/react-query"
import { Trophy } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { formatMoney } from "@/lib/format"
import * as api from "../api"

function ratingVariant(
  label: string,
): "success" | "warning" | "secondary" | "destructive" {
  if (label === "Muy buena") return "success"
  if (label === "Aceptable") return "secondary"
  if (label === "Lenta") return "warning"
  if (label === "Problemática") return "destructive"
  return "secondary"
}

export function InsuranceRankingPanel() {
  const { data, isLoading } = useQuery({
    queryKey: ["insurance-ranking"],
    queryFn: api.getInsuranceRanking,
  })

  if (isLoading) return <LoadingSkeleton rows={4} />

  const items = data?.items.filter((i) => i.claims_total > 0) ?? []

  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
        <p className="font-medium text-foreground mb-1">¿Te conviene cada prepaga?</p>
        <p>
          Ranking según <strong>tu</strong> consultorio: demora entre la atención y el cobro,
          rechazos y deuda pendiente. Marcá los reclamos como cobrados para mejorar el dato.
        </p>
        {data && (
          <p className="text-xs mt-2">
            Mínimo {data.min_sample} pagos registrados para estadísticas fiables.
          </p>
        )}
      </div>

      {items.length === 0 ? (
        <div className="rounded-xl border border-dashed py-10 text-center text-sm text-muted-foreground">
          Aún no hay datos para rankear. Cerrá turnos con obra social y marcá cuándo cobraste.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <Card
              key={item.health_insurance_id}
              className={item.rank === 1 && item.sample_sufficient ? "border-primary/40" : ""}
            >
              <CardHeader className="pb-2 flex flex-row items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  {item.rank <= 3 && item.sample_sufficient && (
                    <Trophy
                      className={`h-4 w-4 shrink-0 ${
                        item.rank === 1
                          ? "text-amber-500"
                          : item.rank === 2
                            ? "text-muted-foreground"
                            : "text-amber-700/70"
                      }`}
                    />
                  )}
                  <CardTitle className="text-base truncate">
                    #{item.rank} {item.name}
                  </CardTitle>
                </div>
                <Badge variant={ratingVariant(item.rating_label)}>{item.rating_label}</Badge>
              </CardHeader>
              <CardContent className="text-sm space-y-2">
                {item.sample_sufficient ? (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <Stat
                      label="Días al cobro (prom.)"
                      value={
                        item.avg_days_to_collect != null
                          ? `${item.avg_days_to_collect}`
                          : "—"
                      }
                    />
                    <Stat
                      label="Pagos en ≤ 45 d"
                      value={
                        item.pct_collected_within_45_days != null
                          ? `${item.pct_collected_within_45_days}%`
                          : "—"
                      }
                    />
                    <Stat
                      label="Rechazos"
                      value={
                        item.rejection_rate_pct != null ? `${item.rejection_rate_pct}%` : "—"
                      }
                    />
                    <Stat label="Score" value={item.score != null ? `${item.score}` : "—"} />
                  </div>
                ) : (
                  <p className="text-muted-foreground text-xs">
                    {item.claims_collected} cobro(s) registrado(s) — necesitás al menos{" "}
                    {data?.min_sample ?? 3} para ver demoras confiables.
                  </p>
                )}
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground pt-1 border-t">
                  <span>{item.claims_total} prestaciones</span>
                  <span>{item.claims_open} pendientes</span>
                  <span>Deuda: {formatMoney(item.open_debt_total)}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-semibold text-lg tabular-nums">{value}</p>
    </div>
  )
}
