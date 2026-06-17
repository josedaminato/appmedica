import { useEffect, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { FileSpreadsheet, Plus, Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { PageHeader } from "@/components/shared/PageHeader"
import { EmptyState } from "@/components/shared/EmptyState"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { QueryErrorState } from "@/components/shared/QueryErrorState"
import { PatientFormDialog } from "../components/PatientFormDialog"
import { PatientImportDialog } from "../components/PatientImportDialog"
import { downloadExport } from "@/lib/export-download"
import * as patientsApi from "../api"
import { ApiError, getErrorMessage } from "@/lib/api-client"

export function PatientsPage() {
  const queryClient = useQueryClient()
  const [q, setQ] = useState("")
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [page, setPage] = useState(1)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [error, setError] = useState("")
  const [exportError, setExportError] = useState("")
  const [searchParams, setSearchParams] = useSearchParams()

  useEffect(() => {
    if (searchParams.get("new") === "1") {
      setDialogOpen(true)
      searchParams.delete("new")
      setSearchParams(searchParams, { replace: true })
    }
  }, [searchParams, setSearchParams])

  const isActive =
    statusFilter === "all" ? undefined : statusFilter === "active"

  const { data, isLoading, isError, error: queryError, refetch } = useQuery({
    queryKey: ["patients", page, search, statusFilter],
    queryFn: () =>
      patientsApi.listPatients({
        page,
        page_size: 20,
        q: search || undefined,
        is_active: isActive,
      }),
  })

  const createMutation = useMutation({
    mutationFn: patientsApi.createPatient,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patients"] })
      setDialogOpen(false)
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Error al crear"),
  })

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    setSearch(q)
    setPage(1)
  }

  return (
    <div>
      <PageHeader
        title="Pacientes"
        description="Gestioná la información administrativa de tus pacientes."
        action={
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={async () => {
                setExportError("")
                try {
                  await downloadExport("patients")
                } catch (err) {
                  setExportError(getErrorMessage(err, "No se pudo exportar la lista de pacientes"))
                }
              }}
            >
              Exportar
            </Button>
            <Button variant="outline" onClick={() => { setError(""); setImportOpen(true) }}>
              <FileSpreadsheet className="h-4 w-4" />
              Importar
            </Button>
            <Button onClick={() => { setError(""); setDialogOpen(true) }}>
              <Plus className="h-4 w-4" />
              Nuevo paciente
            </Button>
          </div>
        }
      />

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
        <form onSubmit={handleSearch} className="flex flex-1 gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-9"
              placeholder="Buscar por nombre, DNI, teléfono..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <Button type="submit" variant="secondary">Buscar</Button>
        </form>
        <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1) }}>
          <SelectTrigger className="w-full sm:w-40">
            <SelectValue placeholder="Estado" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="active">Activos</SelectItem>
            <SelectItem value="inactive">Inactivos</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}
      {exportError && <p className="mb-4 text-sm text-destructive">{exportError}</p>}

      {isLoading ? (
        <LoadingSkeleton />
      ) : isError ? (
        <QueryErrorState error={queryError} onRetry={() => refetch()} />
      ) : !data?.data.length ? (
        <EmptyState
          title="Sin pacientes"
          description="Creá tu primer paciente para empezar."
          action={<Button onClick={() => setDialogOpen(true)}>Nuevo paciente</Button>}
        />
      ) : (
        <>
          <div className="space-y-2 md:hidden">
            {data.data.map((p) => (
              <Link
                key={p.id}
                to={`/patients/${p.id}`}
                className="flex items-center justify-between gap-3 rounded-xl border bg-card p-4 transition-colors hover:bg-muted/30 touch-manipulation"
              >
                <div className="min-w-0">
                  <p className="font-medium truncate">
                    {p.last_name}, {p.first_name}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    DNI {p.dni}
                    {p.phone ? ` · ${p.phone}` : ""}
                  </p>
                </div>
                <Badge variant={p.is_active ? "success" : "secondary"}>
                  {p.is_active ? "Activo" : "Inactivo"}
                </Badge>
              </Link>
            ))}
          </div>
          <div className="hidden md:block rounded-xl border overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium">Paciente</th>
                  <th className="px-4 py-3 text-left font-medium">DNI</th>
                  <th className="px-4 py-3 text-left font-medium">Teléfono</th>
                  <th className="px-4 py-3 text-left font-medium">Estado</th>
                </tr>
              </thead>
              <tbody>
                {data.data.map((p) => (
                  <tr key={p.id} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="px-4 py-3">
                      <Link to={`/patients/${p.id}`} className="font-medium hover:text-primary">
                        {p.last_name}, {p.first_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{p.dni}</td>
                    <td className="px-4 py-3 text-muted-foreground">{p.phone ?? "—"}</td>
                    <td className="px-4 py-3">
                      <Badge variant={p.is_active ? "success" : "secondary"}>
                        {p.is_active ? "Activo" : "Inactivo"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {data && data.meta.total_pages > 1 && (
        <div className="mt-4 flex justify-center gap-2">
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

      <PatientFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSubmit={async (payload) => createMutation.mutateAsync(payload)}
        loading={createMutation.isPending}
      />

      <PatientImportDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        onSuccess={() => queryClient.invalidateQueries({ queryKey: ["patients"] })}
      />
    </div>
  )
}
