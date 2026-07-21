export function formatMoney(amount: number | string | null | undefined) {
  const n = Number(amount ?? 0)
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    maximumFractionDigits: 0,
  }).format(n)
}

const DATE_ONLY_RE = /^\d{4}-\d{2}-\d{2}$/

/**
 * Convierte una entrada a Date interpretando las fechas puras "YYYY-MM-DD"
 * (cumpleaños, service_date) como día local. Si se pasaran a `new Date()`
 * directo se tomarían como medianoche UTC y en Argentina mostrarían el día
 * anterior. Los datetime ISO con zona (start_at, created_at) se respetan.
 */
function toLocalDate(d: string | Date): Date {
  if (typeof d !== "string") return d
  if (DATE_ONLY_RE.test(d)) {
    const [y, m, day] = d.split("-").map(Number)
    return new Date(y, m - 1, day)
  }
  return new Date(d)
}

export function formatDate(d: string | Date) {
  const date = toLocalDate(d)
  return date.toLocaleDateString("es-AR", { day: "2-digit", month: "short", year: "numeric" })
}

export function formatDateTime(d: string | Date) {
  const date = toLocalDate(d)
  return date.toLocaleString("es-AR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
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

function pad2(n: number) {
  return String(n).padStart(2, "0")
}

/** YYYY-MM-DD en hora local (para inputs type="date" y query ?date=). */
export function toDateParam(d: Date) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}

export function todayDateParam() {
  return toDateParam(new Date())
}

/** Día local de un instante ISO (evita usar slice UTC sobre start_at). */
export function isoToLocalDateParam(iso: string) {
  return toDateParam(new Date(iso))
}

export function startOfWeek(d: Date) {
  const copy = new Date(d)
  const day = copy.getDay()
  const diff = day === 0 ? -6 : 1 - day
  copy.setDate(copy.getDate() + diff)
  return copy
}
