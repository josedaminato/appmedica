import { useMemo } from "react"
import { AlertTriangle } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  computeEndFromStart,
  conflictMessage,
  findSchedulingConflict,
  parseLocalDateTime,
} from "@/lib/appointment-schedule"
import { formatTime } from "@/lib/format"
import type { Appointment } from "@/types/api"
import { DurationPicker } from "./DurationPicker"

interface AppointmentScheduleFieldsProps {
  date: string
  time: string
  durationMinutes: number
  onDateChange: (date: string) => void
  onTimeChange: (time: string) => void
  onDurationChange: (minutes: number) => void
  dayAppointments?: Appointment[]
  excludeAppointmentId?: string
}

export function AppointmentScheduleFields({
  date,
  time,
  durationMinutes,
  onDateChange,
  onTimeChange,
  onDurationChange,
  dayAppointments = [],
  excludeAppointmentId,
}: AppointmentScheduleFieldsProps) {
  const { endPreview, conflict } = useMemo(() => {
    const start = parseLocalDateTime(date, time)
    if (!start) return { endPreview: null as string | null, conflict: null as Appointment | null }
    const end = computeEndFromStart(start, durationMinutes)
    const hit = findSchedulingConflict(dayAppointments, start, end, excludeAppointmentId)
    return { endPreview: formatTime(end.toISOString()), conflict: hit }
  }, [date, time, durationMinutes, dayAppointments, excludeAppointmentId])

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
          <Label>Fecha</Label>
          <Input type="date" value={date} onChange={(e) => onDateChange(e.target.value)} required />
        </div>
        <div className="space-y-2">
          <Label>Hora de inicio</Label>
          <Input type="time" value={time} onChange={(e) => onTimeChange(e.target.value)} required />
        </div>
      </div>

      <DurationPicker
        value={durationMinutes}
        onChange={onDurationChange}
        endPreview={endPreview ?? undefined}
      />

      {conflict && (
        <div
          className="flex gap-2 rounded-md border border-amber-500/50 bg-amber-500/10 px-3 py-2 text-sm text-amber-950 dark:text-amber-100"
          role="alert"
        >
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          <span>{conflictMessage(conflict)}</span>
        </div>
      )}
    </div>
  )
}

export function useScheduleValidation(
  date: string,
  time: string,
  durationMinutes: number,
  dayAppointments: Appointment[],
  excludeAppointmentId?: string,
) {
  return useMemo(() => {
    const start = parseLocalDateTime(date, time)
    if (!start) return { valid: false, start: null as Date | null, end: null as Date | null, conflict: null as Appointment | null }
    const end = computeEndFromStart(start, durationMinutes)
    if (end <= start) return { valid: false, start, end, conflict: null }
    const conflict = findSchedulingConflict(dayAppointments, start, end, excludeAppointmentId)
    return { valid: !conflict, start, end, conflict }
  }, [date, time, durationMinutes, dayAppointments, excludeAppointmentId])
}
