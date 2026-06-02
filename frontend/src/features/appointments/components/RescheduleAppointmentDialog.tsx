import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import type { Appointment } from "@/types/api"

export interface ReschedulePayload {
  start_at: string
  end_at: string
  professional_id?: string | null
  notes?: string | null
}

interface RescheduleAppointmentDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  appointment: Appointment | null
  onSubmit: (data: ReschedulePayload) => Promise<void>
  loading?: boolean
}

export function RescheduleAppointmentDialog({
  open,
  onOpenChange,
  appointment,
  onSubmit,
  loading,
}: RescheduleAppointmentDialogProps) {
  const [date, setDate] = useState("")
  const [time, setTime] = useState("")
  const [duration, setDuration] = useState("30")
  const [error, setError] = useState("")

  function reset() {
    if (!appointment) return
    const start = new Date(appointment.start_at)
    const end = new Date(appointment.end_at)
    const mins = Math.round((end.getTime() - start.getTime()) / 60_000) || 30
    const y = start.getFullYear()
    const mo = String(start.getMonth() + 1).padStart(2, "0")
    const d = String(start.getDate()).padStart(2, "0")
    const h = String(start.getHours()).padStart(2, "0")
    const mi = String(start.getMinutes()).padStart(2, "0")
    setDate(`${y}-${mo}-${d}`)
    setTime(`${h}:${mi}`)
    setDuration(String(mins))
    setError("")
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    const start = new Date(`${date}T${time}:00`)
    const end = new Date(start.getTime() + Number(duration) * 60_000)
    if (Number.isNaN(start.getTime()) || !date || !time) {
      setError("Ingresá fecha y hora válidas")
      return
    }
    if (end <= start) {
      setError("La duración debe ser mayor a cero")
      return
    }
    await onSubmit({
      start_at: start.toISOString(),
      end_at: end.toISOString(),
      professional_id: appointment?.professional_id ?? null,
      notes: appointment?.notes,
    })
  }

  const patientName = appointment?.patient
    ? `${appointment.patient.last_name}, ${appointment.patient.first_name}`
    : null

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
          <DialogTitle>Reprogramar turno</DialogTitle>
        </DialogHeader>
        {patientName && (
          <p className="text-sm text-muted-foreground -mt-2">{patientName}</p>
        )}
        <p className="text-xs text-muted-foreground">
          El turno actual quedará como reprogramado y se creará uno nuevo en la fecha elegida.
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>Nueva fecha</Label>
              <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label>Hora</Label>
              <Input type="time" value={time} onChange={(e) => setTime(e.target.value)} required />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Duración (min)</Label>
            <Input
              type="number"
              min={5}
              step={5}
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              required
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Reprogramando..." : "Reprogramar"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
