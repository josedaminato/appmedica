/** Enlace wa.me sin costo de API (el consultorio envía desde su WhatsApp). */

import { formatMoney } from "./format"

export const FALLBACK_CONSULTORIO_NAME = "el consultorio"

export function normalizeWhatsAppPhone(phone: string): string {
  const digits = phone.replace(/\D/g, "")
  if (digits.startsWith("0")) return "54" + digits.slice(1)
  if (!digits.startsWith("54") && digits.length <= 10) return "54" + digits
  return digits
}

export function isWhatsAppPhoneValid(phone: string | null | undefined): boolean {
  if (!phone?.trim()) return false
  const num = normalizeWhatsAppPhone(phone)
  return /^\d{10,15}$/.test(num)
}

export function buildWhatsAppUrl(phone: string, message: string): string {
  const num = normalizeWhatsAppPhone(phone)
  return `https://wa.me/${num}?text=${encodeURIComponent(message)}`
}

export function buildWhatsAppHref(
  phone: string | null | undefined,
  message: string,
): string | null {
  if (!isWhatsAppPhoneValid(phone) || !phone) return null
  return buildWhatsAppUrl(phone, message)
}

export function resolveConsultorioName(orgName?: string | null): string {
  const trimmed = orgName?.trim()
  return trimmed ? trimmed : FALLBACK_CONSULTORIO_NAME
}

export type AppointmentWhatsAppKind =
  | "reminder"
  | "confirm"
  | "reschedule"
  | "cancel"
  | "availability"

export type AppointmentWhatsAppContext = {
  patientFirstName: string
  startAtIso: string
  orgName?: string | null
  professionalName?: string | null
}

function greeting(patientFirstName: string, orgName?: string | null): string {
  const org = resolveConsultorioName(orgName)
  const name = patientFirstName.trim()
  if (!name) return `Hola, te escribimos desde ${org}.`
  return `Hola ${name}, te escribimos desde ${org}.`
}

function professionalPhrase(professionalName?: string | null): string {
  const name = professionalName?.trim()
  return name ? ` con ${name}` : ""
}

function relativeDayLabel(d: Date): "hoy" | "mañana" | null {
  const today = new Date()
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  const target = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const diffDays = Math.round((target.getTime() - start.getTime()) / 86_400_000)
  if (diffDays === 0) return "hoy"
  if (diffDays === 1) return "mañana"
  return null
}

function describeSlot(startAtIso: string): { core: string; relative: "hoy" | "mañana" | null } {
  const d = new Date(startAtIso)
  const weekday = d.toLocaleDateString("es-AR", { weekday: "long" })
  const date = d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit" })
  const time = d.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit", hour12: false })
  return {
    core: `${weekday} ${date} a las ${time} hs`,
    relative: relativeDayLabel(d),
  }
}

/** "mañana martes 19/08 a las 15:30 hs" o "el martes 19/08 a las 15:30 hs" */
export function formatWhatsAppSlot(startAtIso: string, prep: "el" | "del" | "para el"): string {
  const { core, relative } = describeSlot(startAtIso)
  if (relative) {
    if (prep === "el") return `${relative} ${core}`
    if (prep === "del") return `de ${relative} ${core}`
    return `para ${relative} ${core}`
  }
  return `${prep} ${core}`
}

export function buildAppointmentWhatsAppMessage(
  kind: AppointmentWhatsAppKind,
  ctx: AppointmentWhatsAppContext,
): string {
  const hello = greeting(ctx.patientFirstName, ctx.orgName)
  const withProf = professionalPhrase(ctx.professionalName)

  switch (kind) {
    case "reminder":
      return (
        `${hello} Te recordamos que tenés turno ${formatWhatsAppSlot(ctx.startAtIso, "el")}` +
        `${withProf}.`
      )
    case "confirm":
      return (
        `${hello} Queríamos confirmar tu turno ${formatWhatsAppSlot(ctx.startAtIso, "del")}` +
        `${withProf}.`
      )
    case "reschedule":
      return (
        `${hello} Tu turno fue reprogramado ${formatWhatsAppSlot(ctx.startAtIso, "para el")}` +
        `${withProf}.`
      )
    case "cancel":
      return (
        `${hello} Te avisamos que tu turno ${formatWhatsAppSlot(ctx.startAtIso, "del")}` +
        `${withProf} fue cancelado. Si querés coordinar un nuevo horario, escribinos.`
      )
    case "availability":
      return (
        `${hello} Se liberó un turno ${formatWhatsAppSlot(ctx.startAtIso, "para el")}` +
        `${withProf}. Si te interesa, respondé a este mensaje.`
      )
  }
}

/** Conservada para compatibilidad; el recordatorio contextual es `buildAppointmentWhatsAppMessage("reminder", ...)`. */
export function buildAppointmentReminderMessage(
  patientFirstName: string,
  startAtIso: string,
  orgName = FALLBACK_CONSULTORIO_NAME,
  professionalName?: string | null,
): string {
  return buildAppointmentWhatsAppMessage("reminder", {
    patientFirstName,
    startAtIso,
    orgName,
    professionalName,
  })
}

export function buildPrivateDebtMessage(
  patientFirstName: string,
  orgName?: string | null,
  amount?: number | string | null,
): string {
  const hello = greeting(patientFirstName, orgName)
  const numeric = amount == null || amount === "" ? NaN : Number(amount)
  const amountPhrase =
    Number.isFinite(numeric) && numeric > 0
      ? ` El saldo es de ${formatMoney(numeric)}.`
      : ""
  return (
    `${hello} Queríamos avisarte que quedó pendiente el pago correspondiente a tu última atención.` +
    `${amountPhrase} Si querés, podés escribirnos por este medio.`
  )
}

export function buildAvailabilityMessage(ctx: AppointmentWhatsAppContext): string {
  return buildAppointmentWhatsAppMessage("availability", ctx)
}
