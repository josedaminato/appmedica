import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { Appointment, AppointmentClosureStatus, HealthInsurance } from "@/types/api"
import { InsuranceCatalogHint } from "@/features/insurances/components/InsuranceCatalogHint"
import type { ClosePayload } from "../api"

interface CloseAppointmentDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  appointment: Appointment | null
  insurances: HealthInsurance[]
  onSubmit: (data: ClosePayload) => Promise<void>
  loading?: boolean
}

export function CloseAppointmentDialog({
  open,
  onOpenChange,
  appointment,
  insurances,
  onSubmit,
  loading,
}: CloseAppointmentDialogProps) {
  const [closureType, setClosureType] = useState<AppointmentClosureStatus>("paid")
  const [amount, setAmount] = useState("")
  const [paidAmount, setPaidAmount] = useState("")
  const [method, setMethod] = useState("cash")
  const [insuranceId, setInsuranceId] = useState("")

  function reset() {
    const def = appointment?.expected_amount ?? ""
    setAmount(def ? String(def) : "")
    setPaidAmount("")
    setClosureType("paid")
    setMethod("cash")
    setInsuranceId(appointment?.health_insurance_id ?? "")
  }

  const [error, setError] = useState("")

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    const total = Number(amount)
    if (!total || total <= 0) {
      setError("Ingresá un monto válido")
      return
    }
    if (closureType === "insurance_pending" && !insuranceId) {
      setError("Seleccioná una obra social")
      return
    }
    if (closureType === "partial") {
      const paid = Number(paidAmount)
      if (!paid || paid <= 0 || paid >= total) {
        setError("El monto cobrado ahora debe ser menor al total")
        return
      }
    }
    const payload: ClosePayload = {
      closure_type: closureType,
      amount: total,
      method,
    }
    if (closureType === "partial") payload.paid_amount = Number(paidAmount)
    if (closureType === "insurance_pending") payload.health_insurance_id = insuranceId
    await onSubmit(payload)
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (v) reset()
        onOpenChange(v)
      }}
    >
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Cerrar turno</DialogTitle>
        </DialogHeader>
        {appointment?.patient && (
          <p className="text-sm text-muted-foreground -mt-2">
            {appointment.patient.last_name}, {appointment.patient.first_name}
          </p>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label>Resultado</Label>
            <Select value={closureType} onValueChange={(v) => setClosureType(v as AppointmentClosureStatus)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="paid">Cobrado</SelectItem>
                <SelectItem value="pending">Pendiente de cobro</SelectItem>
                <SelectItem value="partial">Cobro parcial</SelectItem>
                <SelectItem value="insurance_pending">Obra social pendiente</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Monto ($)</Label>
            <Input type="number" min={0} value={amount} onChange={(e) => setAmount(e.target.value)} required />
          </div>
          {closureType !== "insurance_pending" && (
            <div className="space-y-2">
              <Label>Método</Label>
              <Select value={method} onValueChange={setMethod}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="cash">Efectivo</SelectItem>
                  <SelectItem value="transfer">Transferencia</SelectItem>
                  <SelectItem value="mercadopago">MercadoPago</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
          {closureType === "partial" && (
            <div className="space-y-2">
              <Label>Cobrado ahora ($)</Label>
              <Input type="number" min={0} value={paidAmount} onChange={(e) => setPaidAmount(e.target.value)} required />
            </div>
          )}
          {closureType === "insurance_pending" && (
            <div className="space-y-2">
              <Label>Obra social</Label>
              <Select value={insuranceId} onValueChange={setInsuranceId}>
                <SelectTrigger><SelectValue placeholder="Seleccionar" /></SelectTrigger>
                <SelectContent>
                  {insurances.map((i) => (
                    <SelectItem key={i.id} value={i.id}>{i.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {insurances.length === 0 && <InsuranceCatalogHint />}
            </div>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Guardando..." : "Cerrar turno"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
