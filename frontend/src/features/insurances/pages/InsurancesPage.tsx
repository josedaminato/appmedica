import { useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { BarChart3, ClipboardList, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { PageHeader } from "@/components/shared/PageHeader"
import { formatMoney } from "@/lib/format"
import { getDashboardSummary } from "@/features/dashboard/api"
import { cn } from "@/lib/utils"
import { InsuranceClaimsPanel } from "../components/InsuranceClaimsPanel"
import { InsuranceRankingPanel } from "../components/InsuranceRankingPanel"
import * as api from "../api"

type Tab = "catalog" | "claims" | "ranking"

const VALID_TABS = new Set<Tab>(["catalog", "claims", "ranking"])

function tabFromParams(params: URLSearchParams): Tab {
  const raw = params.get("tab")
  if (raw && VALID_TABS.has(raw as Tab)) return raw as Tab
  return "claims"
}

const TABS: { id: Tab; label: string; icon: typeof ClipboardList }[] = [
  { id: "catalog", label: "Catálogo", icon: ClipboardList },
  { id: "claims", label: "Reclamos", icon: ClipboardList },
  { id: "ranking", label: "Ranking", icon: BarChart3 },
]

export function InsurancesPage() {
  const qc = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [tab, setTab] = useState<Tab>(() => tabFromParams(searchParams))
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [coverage, setCoverage] = useState("")
  const [days, setDays] = useState("")

  useEffect(() => {
    setTab(tabFromParams(searchParams))
  }, [searchParams])

  function selectTab(next: Tab) {
    setTab(next)
    setSearchParams(
      (prev) => {
        const params = new URLSearchParams(prev)
        params.set("tab", next)
        return params
      },
      { replace: true },
    )
  }

  const { data: insurances = [], isLoading } = useQuery({
    queryKey: ["insurances"],
    queryFn: () => api.listHealthInsurances(),
  })

  const { data: dashboard } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboardSummary,
  })

  const create = useMutation({
    mutationFn: api.createHealthInsurance,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["insurances"] })
      qc.invalidateQueries({ queryKey: ["insurance-ranking"] })
      setOpen(false)
      setName("")
    },
  })

  return (
    <div>
      <PageHeader
        title="Obras sociales"
        description="Reclamos, tiempos de cobro y ranking según tu experiencia."
        action={
          tab === "catalog" ? (
            <Button size="sm" onClick={() => setOpen(true)}>
              <Plus className="h-4 w-4 mr-1" />
              Nueva obra social
            </Button>
          ) : undefined
        }
      />

      {dashboard && Number(dashboard.insurance_debt_total) > 0 && (
        <Card className="mb-4 border-amber-500/30 bg-amber-500/5">
          <CardContent className="pt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <p className="text-sm">
              <span className="font-medium">Deuda OS:</span>{" "}
              {formatMoney(dashboard.insurance_debt_total)} ·{" "}
              {dashboard.pending_insurance_claims} reclamos pendientes
            </p>
            <Button size="sm" variant="outline" onClick={() => selectTab("claims")}>
              Ver reclamos
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="flex gap-1 mb-6 border-b">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => selectTab(id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors",
              tab === id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "catalog" && (
        <>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Cargando...</p>
          ) : insurances.length === 0 ? (
            <p className="text-sm text-muted-foreground">No hay obras sociales cargadas.</p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {insurances.map((i) => (
                <Card key={i.id}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">{i.name}</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground">
                    {i.coverage_percent != null && <p>Cobertura: {i.coverage_percent}%</p>}
                    {i.estimated_payment_days != null && (
                      <p>Pago estimado (referencia): {i.estimated_payment_days} días</p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {tab === "claims" && (
        <InsuranceClaimsPanel insurances={insurances.map((i) => ({ id: i.id, name: i.name }))} />
      )}

      {tab === "ranking" && <InsuranceRankingPanel />}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nueva obra social</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              create.mutate({
                name,
                coverage_percent: coverage ? Number(coverage) : null,
                estimated_payment_days: days ? Number(days) : null,
              })
            }}
            className="space-y-4"
          >
            <div className="space-y-2">
              <Label>Nombre</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label>% cobertura</Label>
              <Input type="number" value={coverage} onChange={(e) => setCoverage(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Días estimados de pago (referencia)</Label>
              <Input type="number" value={days} onChange={(e) => setDays(e.target.value)} />
            </div>
            <Button type="submit" disabled={create.isPending}>
              Guardar
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
