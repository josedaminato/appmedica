import { useEffect, useMemo, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Banknote, Building2, CheckCircle2, ClipboardList, ExternalLink } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useRoleScope } from "@/hooks/use-role-scope"
import { listTeam } from "@/features/users/api"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { FeedbackBanner } from "@/components/shared/FeedbackBanner"
import { EmptyState } from "@/components/shared/EmptyState"
import { formatDate, formatMoney } from "@/lib/format"
import { cn } from "@/lib/utils"
import { ApiError } from "@/lib/api-client"
import { AddPaymentDialog } from "@/features/appointments/components/AddPaymentDialog"
import * as apptApi from "@/features/appointments/api"
import * as insApi from "@/features/insurances/api"
import { downloadExport } from "@/lib/export-download"
import * as api from "../api"
import type { CollectionRow, CollectionTab } from "../api"

const TABS: { id: CollectionTab; label: string }[] = [
  { id: "pending", label: "Todo pendiente" },
  { id: "private", label: "Particulares" },
  { id: "insurance", label: "Obras sociales" },
  { id: "recent", label: "Cobros recientes" },
]

const METHOD_LABELS: Record<string, string> = {
  cash: "Efectivo",
  transfer: "Transferencia",
  mercadopago: "MercadoPago",
  health_insurance: "Obra social",
}

const VALID_TABS = new Set<CollectionTab>(["pending", "private", "insurance", "recent"])

function tabFromParams(params: URLSearchParams): CollectionTab {
  const raw = params.get("tab")
  if (raw && VALID_TABS.has(raw as CollectionTab)) return raw as CollectionTab
  return "pending"
}

export function PaymentsPage() {
  const qc = useQueryClient()
  const { lockedProfessionalId, canFilterByProfessional } = useRoleScope()
  const [searchParams, setSearchParams] = useSearchParams()
  const [tab, setTab] = useState<CollectionTab>(() => tabFromParams(searchParams))
  const [professionalId, setProfessionalId] = useState<string>(
    () => lockedProfessionalId ?? searchParams.get("professional_id") ?? "all",
  )
  const [collectTarget, setCollectTarget] = useState<CollectionRow | null>(null)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")

  useEffect(() => {
    setTab(tabFromParams(searchParams))
    if (lockedProfessionalId) {
      setProfessionalId(lockedProfessionalId)
    } else {
      setProfessionalId(searchParams.get("professional_id") ?? "all")
    }
  }, [searchParams, lockedProfessionalId])

  const effectiveProfessionalId = useMemo(
    () => lockedProfessionalId ?? (professionalId === "all" ? undefined : professionalId),
    [lockedProfessionalId, professionalId],
  )

  const { data: team = [] } = useQuery({
    queryKey: ["team"],
    queryFn: listTeam,
    enabled: canFilterByProfessional,
  })

  function selectTab(next: CollectionTab) {
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

  function syncProfessionalId(next: string) {
    setProfessionalId(next)
    if (lockedProfessionalId) return
    setSearchParams(
      (prev) => {
        const params = new URLSearchParams(prev)
        if (next && next !== "all") params.set("professional_id", next)
        else params.delete("professional_id")
        return params
      },
      { replace: true },
    )
  }

  const { data: summary, isLoading: loadingSummary } = useQuery({
    queryKey: ["payments-summary", effectiveProfessionalId],
    queryFn: () => api.getCollectionsSummary(effectiveProfessionalId),
    refetchInterval: 60_000,
  })

  const { data: rows = [], isLoading: loadingRows } = useQuery({
    queryKey: ["payments-items", tab, effectiveProfessionalId],
    queryFn: () => api.listCollectionItems(tab, effectiveProfessionalId),
  })

  const collect = useMutation({
    mutationFn: ({ appointmentId, amount, method }: { appointmentId: string; amount: number; method: string }) =>
      apptApi.addPaymentToAppointment(appointmentId, { amount, method }),
    onSuccess: () => {
      setCollectTarget(null)
      setSuccess("Cobro registrado")
      setError("")
      invalidateAll(qc)
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Error al cobrar")
    },
  })

  const markCollected = useMutation({
    mutationFn: (claimId: string) => insApi.updateInsuranceClaim(claimId, { status: "collected" }),
    onSuccess: () => {
      setSuccess("Reclamo marcado como cobrado")
      setError("")
      invalidateAll(qc)
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Error al actualizar reclamo")
    },
  })

  return (
    <div>
      <PageHeader
        title="Cobros"
        description="Estado económico del consultorio: deuda, cobros y obras sociales."
        action={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => downloadExport("debt")}>
              Exportar deuda
            </Button>
            <Button variant="outline" size="sm" onClick={() => downloadExport("payments")}>
              Exportar cobros
            </Button>
          </div>
        }
      />

      {loadingSummary ? (
        <LoadingSkeleton rows={2} />
      ) : summary && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5 mb-6">
          <SummaryCard
            label="Deuda particulares"
            value={formatMoney(summary.private_debt_total)}
            icon={Banknote}
            highlight={Number(summary.private_debt_total) > 0}
          />
          <SummaryCard
            label="Deuda obras sociales"
            value={formatMoney(summary.insurance_debt_total)}
            icon={Building2}
            highlight={Number(summary.insurance_debt_total) > 0}
          />
          <SummaryCard
            label="Cobrado hoy"
            value={formatMoney(summary.payments_today_total)}
            sub={`${summary.payments_today_count} pago(s)`}
            icon={CheckCircle2}
          />
          <SummaryCard
            label="Reclamos OS"
            value={String(summary.pending_insurance_claims)}
            sub="pendientes"
            icon={Building2}
            highlight={summary.pending_insurance_claims > 0}
          />
          <SummaryCard
            label="Sin cerrar"
            value={String(summary.unclosed_attended)}
            sub="turnos asistidos"
            icon={ClipboardList}
            highlight={summary.unclosed_attended > 0}
            href="/agenda?status=attended&closure=none"
          />
        </div>
      )}

      {success && <FeedbackBanner variant="success" message={success} />}
      {error && <FeedbackBanner variant="error" message={error} />}

      {canFilterByProfessional && (
        <div className="mb-4">
          <Select value={professionalId} onValueChange={syncProfessionalId}>
            <SelectTrigger className="w-52">
              <SelectValue placeholder="Profesional" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los profesionales</SelectItem>
              {team.map((m) => (
                <SelectItem key={m.id} value={m.id}>
                  {m.full_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      <div className="flex gap-1 mb-4 border-b overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => selectTab(t.id)}
            className={cn(
              "px-4 py-2.5 text-sm font-medium border-b-2 -mb-px whitespace-nowrap transition-colors",
              tab === t.id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loadingRows ? (
        <LoadingSkeleton />
      ) : rows.length === 0 ? (
        <EmptyState
          title="Nada pendiente acá"
          description={
            tab === "recent"
              ? "Los cobros registrados aparecerán en esta lista."
              : "Cuando haya deuda de particulares u obras sociales, la verás acá."
          }
        />
      ) : (
        <div className="rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50">
              <tr>
                <th className="px-3 py-2.5 text-left font-medium">Paciente</th>
                <th className="px-3 py-2.5 text-left font-medium hidden md:table-cell">Origen</th>
                <th className="px-3 py-2.5 text-left font-medium">Fecha</th>
                <th className="px-3 py-2.5 text-left font-medium">Estado</th>
                <th className="px-3 py-2.5 text-right font-medium">Total</th>
                <th className="px-3 py-2.5 text-right font-medium">Pendiente</th>
                <th className="px-3 py-2.5 text-right font-medium">Acción</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.kind}-${row.row_id}`} className="border-b last:border-0 hover:bg-muted/20">
                  <td className="px-3 py-2.5">
                    <Link to={`/patients/${row.patient_id}`} className="font-medium hover:text-primary">
                      {row.patient_name}
                    </Link>
                    {row.professional_name && (
                      <p className="text-xs text-muted-foreground">{row.professional_name}</p>
                    )}
                  </td>
                  <td className="px-3 py-2.5 hidden md:table-cell text-muted-foreground text-xs">
                    {row.kind === "insurance"
                      ? row.health_insurance_name ?? "Obra social"
                      : row.kind === "payment"
                        ? METHOD_LABELS[row.payment_method ?? ""] ?? "Particular"
                        : "Turno particular"}
                  </td>
                  <td className="px-3 py-2.5 text-muted-foreground whitespace-nowrap">
                    {formatDate(row.service_date)}
                    {row.days_pending > 0 && row.balance_pending !== "0" && (
                      <span className="block text-xs text-amber-600 dark:text-amber-400">
                        {row.days_pending} d
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2.5">
                    <StatusBadge row={row} />
                  </td>
                  <td className="px-3 py-2.5 text-right tabular-nums">{formatMoney(row.total_amount)}</td>
                  <td className="px-3 py-2.5 text-right tabular-nums font-medium">
                    {Number(row.balance_pending) > 0 ? formatMoney(row.balance_pending) : "—"}
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="flex justify-end gap-1">
                      {row.can_collect && row.appointment_id && (
                        <Button
                          size="sm"
                          onClick={() => setCollectTarget(row)}
                        >
                          Cobrar
                        </Button>
                      )}
                      {row.can_mark_insurance && (
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={markCollected.isPending}
                          onClick={() => markCollected.mutate(row.row_id)}
                        >
                          Cobrado OS
                        </Button>
                      )}
                      {row.appointment_id && (
                        <Button size="sm" variant="ghost" asChild>
                          <Link to="/agenda" title="Ver agenda">
                            <ExternalLink className="h-3.5 w-3.5" />
                          </Link>
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <AddPaymentDialog
        open={!!collectTarget}
        onOpenChange={(o) => !o && setCollectTarget(null)}
        patientName={collectTarget?.patient_name}
        onSubmit={async (amount, method) => {
          if (collectTarget?.appointment_id) {
            await collect.mutateAsync({
              appointmentId: collectTarget.appointment_id,
              amount,
              method,
            })
          }
        }}
        loading={collect.isPending}
      />
    </div>
  )
}

function SummaryCard({
  label,
  value,
  sub,
  icon: Icon,
  highlight,
  href,
}: {
  label: string
  value: string
  sub?: string
  icon: React.ComponentType<{ className?: string }>
  highlight?: boolean
  href?: string
}) {
  const inner = (
    <Card className={highlight ? "border-amber-500/40 bg-amber-500/5" : ""}>
      <CardContent className="pt-4 pb-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-xl font-semibold tabular-nums mt-0.5">{value}</p>
            {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
          </div>
          <Icon className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
        </div>
      </CardContent>
    </Card>
  )
  return href ? <Link to={href}>{inner}</Link> : inner
}

function StatusBadge({ row }: { row: CollectionRow }) {
  if (row.kind === "insurance") {
    const variant =
      row.status_code === "invoiced"
        ? "secondary"
        : row.status_code === "pending"
          ? "warning"
          : "success"
    return <Badge variant={variant}>{row.status_label}</Badge>
  }
  if (row.kind === "payment") {
    return <Badge variant="success">{row.status_label}</Badge>
  }
  const variant = row.status_code === "partial" ? "warning" : "destructive"
  return <Badge variant={variant}>{row.status_label}</Badge>
}

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["payments-summary"] })
  qc.invalidateQueries({ queryKey: ["payments-items"] })
  qc.invalidateQueries({ queryKey: ["dashboard"] })
  qc.invalidateQueries({ queryKey: ["appointments"] })
  qc.invalidateQueries({ queryKey: ["insurance-claims"] })
  qc.invalidateQueries({ queryKey: ["insurance-ranking"] })
  qc.invalidateQueries({ queryKey: ["patient-admin"] })
}
