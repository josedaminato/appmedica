import type { Appointment, AppointmentStatus } from "@/types/api"

export const DURATION_PRESETS = [15, 20, 30, 45, 60] as const

const BLOCKING_STATUSES = new Set<AppointmentStatus>([
  "pending",
  "confirmed",
  "attended",
])

export function computeEndFromStart(start: Date, durationMinutes: number): Date {
  return new Date(start.getTime() + durationMinutes * 60_000)
}

export function parseLocalDateTime(date: string, time: string): Date | null {
  if (!date || !time) return null
  const parsed = new Date(`${date}T${time}:00`)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

export function findSchedulingConflict(
  appointments: Appointment[],
  start: Date,
  end: Date,
  excludeAppointmentId?: string,
): Appointment | null {
  for (const appt of appointments) {
    if (excludeAppointmentId && appt.id === excludeAppointmentId) continue
    if (!BLOCKING_STATUSES.has(appt.status)) continue
    const otherStart = new Date(appt.start_at)
    const otherEnd = new Date(appt.end_at)
    if (start < otherEnd && end > otherStart) return appt
  }
  return null
}

export function conflictMessage(conflict: Appointment): string {
  const name = conflict.patient
    ? `${conflict.patient.last_name}, ${conflict.patient.first_name}`
    : "otro paciente"
  const start = new Date(conflict.start_at).toLocaleTimeString("es-AR", {
    hour: "2-digit",
    minute: "2-digit",
  })
  const end = new Date(conflict.end_at).toLocaleTimeString("es-AR", {
    hour: "2-digit",
    minute: "2-digit",
  })
  return `Ese horario se superpone con ${name} (${start}–${end}). Elegí otro horario o duración.`
}
