import { useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { BarChart3, ClipboardList, Layers, Pencil, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { PageHeader } from "@/components/shared/PageHeader"
import { EmptyState } from "@/components/shared/EmptyState"
import { FeedbackBanner } from "@/components/shared/FeedbackBanner"
import { formatMoney } from "@/lib/format"
import { getDashboardSummary } from "@/features/dashboard/api"
import { cn } from "@/lib/utils"
import { ApiError } from "@/lib/api-client"
import type { HealthInsurance } from "@/types/api"
import { InsuranceClaimsPanel } from "../components/InsuranceClaimsPanel"
import { InsuranceFormDialog } from "../components/InsuranceFormDialog"
import { InsuranceRankingPanel } from "../components/InsuranceRankingPanel"
import * as api from "../api"

type Tab = "catalog" | "claims" | "ranking"

const VALID_TABS = new Set<Tab>(["catalog", "claims", "ranking"])

function tabFromParams(params: URLSearchParams): Tab {
  const raw = params.get("tab")
  if (raw && VALID_TABS.has(raw as Tab)) return raw as Tab
  return "catalog"
}

const TABS: { id: Tab; label: string; icon: typeof ClipboardList }[] = [
  { id: "catalog", label: "Mis obras sociales", icon: Layers },
  { id: "claims", label: "Reclamos", icon: ClipboardList },
  { id: "ranking", label: "Ranking", icon: BarChart3 },
]

export function InsurancesPage() {
  const qc = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [tab, setTab] = useState<Tab>(() => tabFromParams(searchParams))
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogMode, setDialogMode] = useState<"create" | "edit">("create")
  const [editTarget, setEditTarget] = useState<HealthInsurance | null>(null)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")

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

  function openCreate() {
    setDialogMode("create")
    setEditTarget(null)
    setDialogOpen(true)
  }

  function openEdit(insurance: HealthInsurance) {
    setDialogMode("edit")
    setEditTarget(insurance)
    setDialogOpen(true)
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
      setDialogOpen(false)
      setSuccess("Obra social agregada.")
      setError("")
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "No se pudo agregar la obra social")
      setSuccess("")
    },
  })

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof api.updateHealthInsurance>[1] }) =>
      api.updateHealthInsurance(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["insurances"] })
      qc.invalidateQueries({ queryKey: ["insurance-ranking"] })
      qc.invalidateQueries({ queryKey: ["insurance-claims"] })
      setDialogOpen(false)
      setEditTarget(null)
      setSuccess("Obra social actualizada.")
      setError("")
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar la obra social")
      setSuccess("")
    },
  })

  const formLoading = create.isPending || update.isPending

  return (
    <div>
      <PageHeader
        title="Obras sociales"
        description="Cargá las obras con las que trabajás, seguí reclamos y compará tiempos de cobro."
        action={
          <Button size="sm" onClick={openCreate}>
            <Plus className="mr-1 h-4 w-4" />
            Agregar obra social
          </Button>
        }
      />

      {error && <FeedbackBanner message={error} variant="error" />}
      {success && <FeedbackBanner message={success} variant="success" />}

      {!isLoading && insurances.length === 0 && (
        <Card className="mb-4 border-primary/20 bg-primary/5">
          <CardContent className="flex flex-col gap-3 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-medium">Empezá por acá</p>
              <p className="text-sm text-muted-foreground">
                Agregá OSDE, Swiss, PAMI u otras obras sociales que atiendas. Después las vas a elegir en pacientes y
                turnos.
              </p>
            </div>
            <Button size="sm" onClick={openCreate}>
              <Plus className="mr-1 h-4 w-4" />
              Agregar la primera
            </Button>
          </CardContent>
        </Card>
      )}

      {dashboard && Number(dashboard.insurance_debt_total) > 0 && (
        <Card className="mb-4 border-amber-500/30 bg-amber-500/5">
          <CardContent className="flex flex-col gap-2 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm">
              <span className="font-medium">Deuda OS:</span> {formatMoney(dashboard.insurance_debt_total)} ·{" "}
              {dashboard.pending_insurance_claims} reclamos pendientes
            </p>
            <Button size="sm" variant="outline" onClick={() => selectTab("claims")}>
              Ver reclamos
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="mb-6 flex gap-1 border-b">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => selectTab(id)}
            className={cn(
              "flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium -mb-px transition-colors",
              tab === id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
            {id === "catalog" && insurances.length > 0 && (
              <span className="rounded-full bg-muted px-1.5 py-0.5 text-xs">{insurances.length}</span>
            )}
          </button>
        ))}
      </div>

      {tab === "catalog" && (
        <>
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Cargando...</p>
          ) : insurances.length === 0 ? (
            <EmptyState
              title="Sin obras sociales cargadas"
              description="Agregá las obras sociales con las que trabajás para asignarlas a pacientes, turnos y reclamos."
              action={
                <Button onClick={openCreate}>
                  <Plus className="mr-1 h-4 w-4" />
                  Agregar obra social
                </Button>
              }
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {insurances.map((i) => (
                <Card key={i.id}>
                  <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
                    <CardTitle className="text-base">{i.name}</CardTitle>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 shrink-0"
                      onClick={() => openEdit(i)}
                      aria-label={`Editar ${i.name}`}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground">
                    {i.coverage_percent != null && <p>Cobertura: {i.coverage_percent}%</p>}
                    {i.estimated_payment_days != null && (
                      <p>Pago estimado (referencia): {i.estimated_payment_days} días</p>
                    )}
                    {i.notes && <p className="mt-2 line-clamp-2">{i.notes}</p>}
                    {i.coverage_percent == null && i.estimated_payment_days == null && !i.notes && (
                      <p>Sin datos extra — podés editarla cuando quieras.</p>
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

      <InsuranceFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        mode={dialogMode}
        insurance={editTarget}
        loading={formLoading}
        onSubmit={async (data) => {
          if (dialogMode === "edit" && editTarget) {
            await update.mutateAsync({ id: editTarget.id, data })
          } else {
            await create.mutateAsync(data)
          }
        }}
      />
    </div>
  )
}
