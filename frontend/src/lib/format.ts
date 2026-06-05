export function formatMoney(amount: number | string | null | undefined) {
  const n = Number(amount ?? 0)
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    maximumFractionDigits: 0,
  }).format(n)
}

export function formatDate(d: string | Date) {
  const date = typeof d === "string" ? new Date(d) : d
  return date.toLocaleDateString("es-AR", { day: "2-digit", month: "short", year: "numeric" })
}

export function formatTime(d: string) {
  return new Date(d).toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" })
}

export function formatTimeRange(startIso: string, endIso: string) {
  return `${formatTime(startIso)} – ${formatTime(endIso)}`
}

export function appointmentDurationMinutes(startIso: string, endIso: string) {
  const ms = new Date(endIso).getTime() - new Date(startIso).getTime()
  return Math.max(0, Math.round(ms / 60_000))
}

export function toDateParam(d: Date) {
  return d.toISOString().slice(0, 10)
}

export function startOfWeek(d: Date) {
  const copy = new Date(d)
  const day = copy.getDay()
  const diff = day === 0 ? -6 : 1 - day
  copy.setDate(copy.getDate() + diff)
  return copy
}
