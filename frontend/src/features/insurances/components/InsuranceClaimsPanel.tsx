import { useState } from "react"
import { Link } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect } from "react"
import { CheckCircle2, FileCheck, XCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ClaimStatusBadge } from "./ClaimStatusBadge"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { QueryErrorState } from "@/components/shared/QueryErrorState"
import { FeedbackBanner } from "@/components/shared/FeedbackBanner"
import { formatDate, formatMoney } from "@/lib/format"
import { downloadExport } from "@/lib/export-download"
import { ApiError, getErrorMessage } from "@/lib/api-client"
import type { InsuranceClaimStatus } from "@/types/api"
import * as api from "../api"

type Props = {
  insurances: { id: string; name: string }[]
}

export function InsuranceClaimsPanel({ insurances }: Props) {
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<string>("open")
  const [insuranceFilter, setInsuranceFilter] = useState<string>("all")
  const [success, setSuccess] = useState("")
  const [error, setError] = useState("")
  const [exportError, setExportError] = useState("")

  const openOnly = statusFilter === "open"
  const status =
    statusFilter !== "all" && statusFilter !== "open"
      ? (statusFilter as InsuranceClaimStatus)
      : undefined

  const { data, isLoading, isError, error: queryError, refetch } = useQuery({
    queryKey: ["insurance-claims", page, statusFilter, insuranceFilter],
    queryFn: () =>
      api.listInsuranceClaims({
        page,
        page_size: 20,
        status,
        open_only: openOnly,
        health_insurance_id: insuranceFilter === "all" ? undefined : insuranceFilter,
      }),
  })

  useEffect(() => {
    if (!success) return
    const t = setTimeout(() => setSuccess(""), 4000)
    return () => clearTimeout(t)
  }, [success])

  const update = useMutation({
    mutationFn: ({ id, status: st }: { id: string; status: InsuranceClaimStatus }) =>
      api.updateInsuranceClaim(id, { status: st }),
    onSuccess: () => {
      setError("")
      setSuccess("Reclamo actualizado")
      qc.invalidateQueries({ queryKey: ["insurance-claims"] })
      qc.invalidateQueries({ queryKey: ["insurance-ranking"] })
      qc.invalidateQueries({ queryKey: ["dashboard"] })
      qc.invalidateQueries({ queryKey: ["patient-admin"] })
    },
    onError: (err) => {
      setSuccess("")
      setError(err instanceof ApiError ? err.message : "Error al actualizar")
    },
  })

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Marcá cuándo facturaste y cuándo cobró la obra social. Así calculamos demoras y el ranking.
      </p>

      {success && <FeedbackBanner variant="success" message={success} />}
      {error && <FeedbackBanner variant="error" message={error} />}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1) }}>
          <SelectTrigger className="w-full sm:w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="open">Pendientes de cobro</SelectItem>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="pending">Pendiente</SelectItem>
            <SelectItem value="invoiced">Facturado</SelectItem>
            <SelectItem value="collected">Cobrado</SelectItem>
            <SelectItem value="rejected">Rechazado</SelectItem>
          </SelectContent>
        </Select>
        <Select value={insuranceFilter} onValueChange={(v) => { setInsuranceFilter(v); setPage(1) }}>
          <SelectTrigger className="w-full sm:w-52">
            <SelectValue placeholder="Obra social" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas las obras sociales</SelectItem>
            {insurances.map((i) => (
              <SelectItem key={i.id} value={i.id}>{i.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={async () => {
            setExportError("")
            try {
              await downloadExport("claims")
            } catch (err) {
              setExportError(getErrorMessage(err, "No se pudo exportar los reclamos"))
            }
          }}
        >
          Exportar Excel
        </Button>
      </div>

      {exportError && <FeedbackBanner variant="error" message={exportError} />}

      {isLoading ? (
        <LoadingSkeleton />
      ) : isError ? (
        <QueryErrorState error={queryError} onRetry={() => refetch()} />
      ) : !data?.data.length ? (
        <div className="rounded-xl border border-dashed py-10 text-center text-sm text-muted-foreground">
          No hay reclamos con estos filtros.
          <br />
          Se crean al cerrar un turno como obra social en la agenda.
        </div>
      ) : (
        <div className="rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Paciente</th>
                <th className="px-3 py-2 text-left font-medium hidden md:table-cell">OS</th>
                <th className="px-3 py-2 text-left font-medium">Atención</th>
                <th className="px-3 py-2 text-left font-medium">Monto</th>
                <th className="px-3 py-2 text-left font-medium">Estado</th>
                <th className="px-3 py-2 text-left font-medium hidden sm:table-cell">Demora</th>
                <th className="px-3 py-2 text-right font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {data.data.map((claim) => (
                <tr key={claim.id} className="border-b last:border-0 hover:bg-muted/20">
                  <td className="px-3 py-2">
                    <Link to={`/patients/${claim.patient_id}`} className="font-medium hover:text-primary">
                      {claim.patient_name ?? "Paciente"}
                    </Link>
                  </td>
                  <td className="px-3 py-2 hidden md:table-cell text-muted-foreground">
                    {claim.health_insurance_name}
                  </td>
                  <td className="px-3 py-2 text-muted-foreground whitespace-nowrap">
                    {formatDate(claim.service_date)}
                  </td>
                  <td className="px-3 py-2 tabular-nums">{formatMoney(claim.expected_amount)}</td>
                  <td className="px-3 py-2">
                    <ClaimStatusBadge status={claim.status} />
                  </td>
                  <td className="px-3 py-2 hidden sm:table-cell text-xs text-muted-foreground">
                    {claim.status === "collected" && claim.days_to_collect != null
                      ? `${claim.days_to_collect} d al cobro`
                      : `${claim.days_since_service ?? 0} d abierto`}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex justify-end gap-1 flex-wrap">
                      {claim.status === "pending" && (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={update.isPending}
                          onClick={() => update.mutate({ id: claim.id, status: "invoiced" })}
                          title="Marcar facturado"
                        >
                          <FileCheck className="h-3.5 w-3.5" />
                        </Button>
                      )}
                      {(claim.status === "pending" || claim.status === "invoiced") && (
                        <>
                          <Button
                            size="sm"
                            disabled={update.isPending}
                            onClick={() => update.mutate({ id: claim.id, status: "collected" })}
                            title="Marcar cobrado"
                          >
                            <CheckCircle2 className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-destructive"
                            disabled={update.isPending}
                            onClick={() => update.mutate({ id: claim.id, status: "rejected" })}
                            title="Marcar rechazado"
                          >
                            <XCircle className="h-3.5 w-3.5" />
                          </Button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data && data.meta.total_pages > 1 && (
        <div className="flex justify-center gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Anterior
          </Button>
          <span className="flex items-center text-sm text-muted-foreground">
            Página {page} de {data.meta.total_pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= data.meta.total_pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Siguiente
          </Button>
        </div>
      )}
    </div>
  )
}
