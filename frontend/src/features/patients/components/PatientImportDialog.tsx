import { useCallback, useMemo, useRef, useState } from "react"
import { ChevronDown, Download, FileSpreadsheet, Upload } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { ApiError } from "@/lib/api-client"
import { readSpreadsheetFile, type ParsedSpreadsheet } from "@/lib/spreadsheet-parser"
import { useAuth } from "@/features/auth/AuthContext"
import {
  analyzePatientImport,
  commitPatientImport,
  type PatientImportMapping,
  type PatientImportPreview,
} from "../import-api"
import { downloadPatientImportTemplate } from "../import-template"

const UNMAPPED = "__none__"

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

type Step = "pick" | "confirm" | "done"

export function PatientImportDialog({ open, onOpenChange, onSuccess }: Props) {
  const { isAuthenticated } = useAuth()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [step, setStep] = useState<Step>("pick")
  const [sheet, setSheet] = useState<ParsedSpreadsheet | null>(null)
  const [fileName, setFileName] = useState("")
  const [mapping, setMapping] = useState<PatientImportMapping>({})
  const [preview, setPreview] = useState<PatientImportPreview | null>(null)
  const [showMapping, setShowMapping] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [dragOver, setDragOver] = useState(false)
  const [result, setResult] = useState<{ created: number; skipped: number; failed: number } | null>(
    null,
  )

  const importableRows = useMemo(() => {
    if (!preview) return []
    return preview.rows.filter((r) => r.status === "valid" && r.data).map((r) => r.data!)
  }, [preview])

  const mappingOk = useMemo(() => {
    if (!preview) return false
    const m = preview.suggested_mapping
    const hasDni = Boolean(m.dni)
    const hasName =
      Boolean(m.full_name) || (Boolean(m.first_name) && Boolean(m.last_name))
    return hasDni && hasName
  }, [preview])

  function reset() {
    setStep("pick")
    setSheet(null)
    setFileName("")
    setMapping({})
    setPreview(null)
    setShowMapping(false)
    setError("")
    setResult(null)
    setLoading(false)
    setDragOver(false)
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  function handleClose(next: boolean) {
    if (!next) reset()
    onOpenChange(next)
  }

  const runAnalyze = useCallback(
    async (data: ParsedSpreadsheet, map?: PatientImportMapping) => {
      if (!isAuthenticated) {
        setError("Iniciá sesión para importar pacientes.")
        return
      }
      setLoading(true)
      setError("")
      try {
        const res = await analyzePatientImport(data, map)
        setPreview(res)
        setMapping(res.suggested_mapping)
        if (!res.suggested_mapping.dni) {
          setShowMapping(true)
        }
        setStep("confirm")
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "No se pudo validar la planilla")
      } finally {
        setLoading(false)
      }
    },
    [isAuthenticated],
  )

  async function processFile(file: File) {
    setError("")
    setFileName(file.name)
    try {
      const parsed = await readSpreadsheetFile(file)
      setSheet(parsed)
      await runAnalyze(parsed)
    } catch (err) {
      setSheet(null)
      setPreview(null)
      setStep("pick")
      setError(err instanceof Error ? err.message : "No se pudo leer el archivo")
    }
  }

  function onFileInputChange(file: File | undefined) {
    if (file) void processFile(file)
  }

  async function handleMappingApply() {
    if (!sheet) return
    await runAnalyze(sheet, mapping)
  }

  async function handleImport() {
    if (!importableRows.length) {
      setError("No hay filas listas para importar. Revisá el mapeo o corregí el Excel.")
      return
    }
    setLoading(true)
    setError("")
    try {
      const res = await commitPatientImport(importableRows, "skip")
      setResult({ created: res.created, skipped: res.skipped, failed: res.failed })
      setStep("done")
      onSuccess()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al importar")
    } finally {
      setLoading(false)
    }
  }

  const targetFields = preview?.target_fields ?? []
  const columns = preview?.columns ?? sheet?.columns ?? []

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5 text-primary" />
            Importar pacientes
          </DialogTitle>
          <p className="text-sm text-muted-foreground">
            Elegí tu Excel. Lo leemos en tu computadora; solo enviamos los datos al confirmar.
          </p>
        </DialogHeader>

        {step === "pick" && (
          <div className="space-y-4">
            <div className="rounded-lg border bg-muted/30 px-3 py-2.5 text-xs text-muted-foreground space-y-1">
              <p className="font-medium text-foreground">Para evitar problemas al abrir el archivo</p>
              <ul className="list-disc pl-4 space-y-0.5">
                <li>Cerrá el archivo en Excel antes de subirlo</li>
                <li>Preferí .xlsx (Archivo → Guardar como)</li>
                <li>Si está en OneDrive, esperá que termine de sincronizar</li>
              </ul>
            </div>

            <div
              role="button"
              tabIndex={0}
              onDragOver={(e) => {
                e.preventDefault()
                setDragOver(true)
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault()
                setDragOver(false)
                const file = e.dataTransfer.files?.[0]
                if (file) onFileInputChange(file)
              }}
              className={`flex flex-col items-center gap-3 rounded-xl border-2 border-dashed p-8 transition-colors ${
                dragOver ? "border-primary bg-primary/5" : "border-border"
              }`}
            >
              <Upload className="h-8 w-8 text-muted-foreground" />
              <Button
                type="button"
                disabled={loading}
                onClick={() => fileInputRef.current?.click()}
              >
                Elegir archivo Excel o CSV
              </Button>
              <p className="text-xs text-muted-foreground text-center">
                O arrastrá el archivo aquí · hasta 2000 filas
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xlsm,.xls,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv"
                className="hidden"
                onChange={(e) => {
                  onFileInputChange(e.target.files?.[0])
                  e.target.value = ""
                }}
              />
            </div>

            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={downloadPatientImportTemplate}
            >
              <Download className="h-4 w-4" />
              Descargar plantilla de ejemplo
            </Button>
          </div>
        )}

        {step === "confirm" && preview && (
          <div className="space-y-4">
            <p className="text-sm">
              <span className="font-medium">{fileName}</span>
              <span className="text-muted-foreground"> · {preview.summary.total} filas</span>
            </p>

            <div className="flex flex-wrap gap-2">
              <Badge variant="success">{preview.summary.valid} listos</Badge>
              {preview.summary.duplicate > 0 && (
                <Badge variant="secondary">{preview.summary.duplicate} ya existen</Badge>
              )}
              {preview.summary.error > 0 && (
                <Badge variant="destructive">{preview.summary.error} con error</Badge>
              )}
            </div>

            {!mappingOk && (
              <p className="text-sm text-amber-700 dark:text-amber-400">
                Falta mapear al menos <strong>DNI</strong> y <strong>nombre</strong> (o nombre
                completo). Abrí “Ajustar columnas” abajo.
              </p>
            )}

            <p className="text-sm text-muted-foreground">
              Se importarán <strong className="text-foreground">{importableRows.length}</strong>{" "}
              pacientes nuevos.
            </p>

            <button
              type="button"
              className="flex w-full items-center justify-between text-sm font-medium text-muted-foreground hover:text-foreground"
              onClick={() => setShowMapping((v) => !v)}
            >
              Ajustar columnas (opcional)
              <ChevronDown
                className={`h-4 w-4 transition-transform ${showMapping ? "rotate-180" : ""}`}
              />
            </button>

            {showMapping && (
              <div className="space-y-3 rounded-lg border p-3">
                <div className="grid gap-2 max-h-48 overflow-y-auto">
                  {targetFields.map((field) => (
                    <div key={field.key} className="grid grid-cols-2 gap-2 items-center">
                      <Label className="text-xs">{field.label}</Label>
                      <Select
                        value={
                          (mapping[field.key as keyof PatientImportMapping] as string) ?? UNMAPPED
                        }
                        onValueChange={(v) =>
                          setMapping((m) => ({
                            ...m,
                            [field.key]: v === UNMAPPED ? null : v,
                          }))
                        }
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value={UNMAPPED}>—</SelectItem>
                          {columns.map((col) => (
                            <SelectItem key={col} value={col}>
                              {col}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  ))}
                </div>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="w-full"
                  disabled={loading}
                  onClick={handleMappingApply}
                >
                  Aplicar mapeo
                </Button>
              </div>
            )}
          </div>
        )}

        {step === "done" && result && (
          <div className="rounded-lg border bg-muted/30 p-4 space-y-1 text-sm">
            <p className="font-medium text-lg">{result.created} pacientes importados</p>
            {result.skipped > 0 && (
              <p className="text-muted-foreground">{result.skipped} omitidos (ya estaban cargados)</p>
            )}
            {result.failed > 0 && (
              <p className="text-destructive">{result.failed} no se pudieron guardar</p>
            )}
          </div>
        )}

        {error && (
          <p className="text-sm text-destructive rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2">
            {error}
          </p>
        )}

        {loading && step === "pick" && (
          <p className="text-sm text-center text-muted-foreground">Leyendo planilla…</p>
        )}

        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end pt-2">
          {step === "pick" && (
            <Button variant="outline" onClick={() => handleClose(false)}>
              Cancelar
            </Button>
          )}
          {step === "confirm" && (
            <>
              <Button
                variant="outline"
                disabled={loading}
                onClick={() => {
                  setStep("pick")
                  setPreview(null)
                  setSheet(null)
                }}
              >
                Otro archivo
              </Button>
              <Button
                onClick={handleImport}
                disabled={loading || !importableRows.length || !mappingOk}
              >
                {loading ? "Importando…" : `Importar ${importableRows.length} pacientes`}
              </Button>
            </>
          )}
          {step === "done" && <Button onClick={() => handleClose(false)}>Listo</Button>}
        </div>
      </DialogContent>
    </Dialog>
  )
}
