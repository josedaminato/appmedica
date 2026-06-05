/** Enlace wa.me sin costo de API (el consultorio envía desde su WhatsApp). */

export function normalizeWhatsAppPhone(phone: string): string {
  const digits = phone.replace(/\D/g, "")
  if (digits.startsWith("0")) return "54" + digits.slice(1)
  if (!digits.startsWith("54") && digits.length <= 10) return "54" + digits
  return digits
}

export function buildWhatsAppUrl(phone: string, message: string): string {
  const num = normalizeWhatsAppPhone(phone)
  return `https://wa.me/${num}?text=${encodeURIComponent(message)}`
}

export function buildAppointmentReminderMessage(
  patientFirstName: string,
  startAtIso: string,
  orgName = "el consultorio",
): string {
  const d = new Date(startAtIso)
  const date = d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" })
  const time = d.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" })
  return (
    `Hola ${patientFirstName}, te recordamos tu turno en ${orgName} ` +
    `el ${date} a las ${time}. Si necesitás reprogramar, respondé este mensaje.`
  )
}
