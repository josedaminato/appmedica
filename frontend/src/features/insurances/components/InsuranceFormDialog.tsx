import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import type { HealthInsurance } from "@/types/api"

type Mode = "create" | "edit"

type FormPayload = {
  name: string
  coverage_percent: number | null
  estimated_payment_days: number | null
  notes: string | null
}

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  mode: Mode
  insurance?: HealthInsurance | null
  onSubmit: (data: FormPayload) => Promise<void>
  loading?: boolean
}

export function InsuranceFormDialog({
  open,
  onOpenChange,
  mode,
  insurance,
  onSubmit,
  loading,
}: Props) {
  const [name, setName] = useState("")
  const [coverage, setCoverage] = useState("")
  const [days, setDays] = useState("")
  const [notes, setNotes] = useState("")

  useEffect(() => {
    if (!open) return
    if (mode === "edit" && insurance) {
      setName(insurance.name)
      setCoverage(insurance.coverage_percent != null ? String(insurance.coverage_percent) : "")
      setDays(insurance.estimated_payment_days != null ? String(insurance.estimated_payment_days) : "")
      setNotes(insurance.notes ?? "")
    } else {
      setName("")
      setCoverage("")
      setDays("")
      setNotes("")
    }
  }, [open, mode, insurance])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await onSubmit({
      name: name.trim(),
      coverage_percent: coverage ? Number(coverage) : null,
      estimated_payment_days: days ? Number(days) : null,
      notes: notes.trim() || null,
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{mode === "edit" ? "Editar obra social" : "Nueva obra social"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="insurance-name">Nombre</Label>
            <Input
              id="insurance-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ej. OSDE, Swiss Medical, PAMI"
              required
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="insurance-coverage">% cobertura (opcional)</Label>
              <Input
                id="insurance-coverage"
                type="number"
                min={0}
                max={100}
                value={coverage}
                onChange={(e) => setCoverage(e.target.value)}
                placeholder="80"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="insurance-days">Días de pago (opcional)</Label>
              <Input
                id="insurance-days"
                type="number"
                min={0}
                value={days}
                onChange={(e) => setDays(e.target.value)}
                placeholder="60"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="insurance-notes">Notas (opcional)</Label>
            <Textarea
              id="insurance-notes"
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Contacto de facturación, observaciones..."
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Cargá solo las obras sociales con las que trabajás. Después las vas a usar en pacientes, turnos y reclamos.
          </p>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={loading || !name.trim()}>
              {loading ? "Guardando..." : mode === "edit" ? "Guardar cambios" : "Agregar"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
