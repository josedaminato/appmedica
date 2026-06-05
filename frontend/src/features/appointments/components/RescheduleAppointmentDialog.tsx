import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ApiError } from "@/lib/api-client"
import { conflictMessage } from "@/lib/appointment-schedule"
import { appointmentDurationMinutes } from "@/lib/format"
import type { Appointment } from "@/types/api"
import * as apptApi from "../api"
import {
  AppointmentScheduleFields,
  useScheduleValidation,
} from "./AppointmentScheduleFields"

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
  const [durationMinutes, setDurationMinutes] = useState(30)
  const [error, setError] = useState("")

  const professionalId = appointment?.professional_id ?? ""

  const { data: dayAppointments = [] } = useQuery({
    queryKey: ["appointments", date, "day", professionalId, "reschedule"],
    queryFn: () =>
      apptApi.listAppointments({
        date,
        view: "day",
        professional_id: professionalId || undefined,
      }),
    enabled: open && !!date && !!professionalId,
  })

  const schedule = useScheduleValidation(date, time, durationMinutes, dayAppointments)

  function reset() {
    if (!appointment) return
    const mins =
      appointmentDurationMinutes(appointment.start_at, appointment.end_at) || 30
    const start = new Date(appointment.start_at)
    const y = start.getFullYear()
    const mo = String(start.getMonth() + 1).padStart(2, "0")
    const d = String(start.getDate()).padStart(2, "0")
    const h = String(start.getHours()).padStart(2, "0")
    const mi = String(start.getMinutes()).padStart(2, "0")
    setDate(`${y}-${mo}-${d}`)
    setTime(`${h}:${mi}`)
    setDurationMinutes(mins)
    setError("")
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    if (!schedule.valid || !schedule.start || !schedule.end) {
      if (schedule.conflict) setError(conflictMessage(schedule.conflict))
      else setError("Completá fecha, hora y duración")
      return
    }
    try {
      await onSubmit({
        start_at: schedule.start.toISOString(),
        end_at: schedule.end.toISOString(),
        professional_id: appointment?.professional_id ?? null,
        notes: appointment?.notes,
      })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo reprogramar")
    }
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
          <AppointmentScheduleFields
            date={date}
            time={time}
            durationMinutes={durationMinutes}
            onDateChange={setDate}
            onTimeChange={setTime}
            onDurationChange={setDurationMinutes}
            dayAppointments={dayAppointments}
          />
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button
            type="submit"
            className="w-full"
            disabled={loading || !schedule.valid}
          >
            {loading ? "Reprogramando..." : "Reprogramar"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
