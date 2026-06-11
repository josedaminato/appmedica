import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Calendar, Download, TrendingUp, UserX, Wallet } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { EmptyState } from "@/components/shared/EmptyState"
import { FeedbackBanner } from "@/components/shared/FeedbackBanner"
import { formatMoney } from "@/lib/format"
import * as api from "../api"

function currentMonthValue() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`
}

function parseMonthValue(value: string): { year: number; month: number } {
  const [y, m] = value.split("-").map(Number)
  return { year: y, month: m }
}

export function ReportsPage() {
  const [monthValue, setMonthValue] = useState(currentMonthValue)
  const [exportError, setExportError] = useState("")
  const { year, month } = parseMonthValue(monthValue)

  const { data, isLoading, isError } = useQuery({
    queryKey: ["monthly-report", year, month],
    queryFn: () => api.getMonthlyReport(year, month),
    enabled: Boolean(year && month),
  })

  async function handleExport(format: "xlsx" | "csv") {
    setExportError("")
    try {
      await api.downloadMonthlyReport(year, month, format)
    } catch {
      setExportError("No se pudo exportar el reporte")
    }
  }

  return (
    <div>
      <PageHeader
        title="Reportes"
        description="Resumen mensual del consultorio para control y contabilidad."
        action={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => handleExport("xlsx")}>
              <Download className="h-4 w-4 mr-1" />
              Excel
            </Button>
            <Button variant="outline" size="sm" onClick={() => handleExport("csv")}>
              <Download className="h-4 w-4 mr-1" />
              CSV
            </Button>
          </div>
        }
      />

      <div className="mb-6 flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="report-month" className="text-sm font-medium text-muted-foreground block mb-1.5">
            Mes
          </label>
          <Input
            id="report-month"
            type="month"
            className="w-44"
            value={monthValue}
            onChange={(e) => setMonthValue(e.target.value)}
          />
        </div>
      </div>

      {exportError && <FeedbackBanner variant="error" message={exportError} />}

      {isLoading ? (
        <LoadingSkeleton rows={3} />
      ) : isError ? (
        <EmptyState
          title="No se pudo cargar el reporte"
          description="Revisá tu conexión e intentá de nuevo en unos segundos."
        />
      ) : data ? (
        <>
          <p className="text-sm text-muted-foreground mb-4">{data.period_label}</p>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 mb-6">
            <ReportCard
              title="Turnos"
              icon={Calendar}
              lines={[
                { label: "Total", value: String(data.appointments_total) },
                { label: "Asistieron", value: String(data.appointments_attended) },
                { label: "Ausencias", value: String(data.appointments_no_show) },
                { label: "Cancelados", value: String(data.appointments_cancelled) },
              ]}
            />
            <ReportCard
              title="Pagos particulares"
              icon={Wallet}
              lines={[
                { label: "Total cobrado", value: formatMoney(data.private_collected_total) },
                { label: "Pagos registrados", value: String(data.private_payments_count) },
              ]}
            />
            <ReportCard
              title="Obras sociales"
              icon={TrendingUp}
              lines={[
                { label: "Cobrado OS", value: formatMoney(data.insurance_collected_total) },
                { label: "Reclamos cobrados", value: String(data.insurance_collected_count) },
                { label: "Prestaciones del mes", value: String(data.insurance_services_count) },
              ]}
            />
          </div>

          <Card className="border-primary/20 bg-primary/5">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                Total cobrado en el mes
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold tabular-nums">{formatMoney(data.total_collected)}</p>
              <p className="text-xs text-muted-foreground mt-1">
                Particulares + obras sociales cobradas en {data.period_label.toLowerCase()}
              </p>
            </CardContent>
          </Card>

          {data.appointments_no_show > 0 && (
            <Card className="mt-4 border-amber-500/30">
              <CardContent className="pt-4 flex items-center gap-3 text-sm">
                <UserX className="h-4 w-4 text-amber-600 shrink-0" />
                <span>
                  {data.appointments_no_show} ausencia{data.appointments_no_show === 1 ? "" : "s"} en el mes
                </span>
              </CardContent>
            </Card>
          )}
        </>
      ) : null}
    </div>
  )
}

function ReportCard({
  title,
  icon: Icon,
  lines,
}: {
  title: string
  icon: React.ComponentType<{ className?: string }>
  lines: { label: string; value: string }[]
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent className="space-y-1.5">
        {lines.map((line) => (
          <div key={line.label} className="flex justify-between text-sm gap-4">
            <span className="text-muted-foreground">{line.label}</span>
            <span className="font-medium tabular-nums text-right">{line.value}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
