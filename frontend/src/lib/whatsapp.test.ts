import { describe, expect, it } from "vitest"
import { formatMoney } from "./format"
import {
  FALLBACK_CONSULTORIO_NAME,
  buildAppointmentReminderMessage,
  buildAppointmentWhatsAppMessage,
  buildAvailabilityMessage,
  buildPrivateDebtMessage,
  buildWhatsAppHref,
  buildWhatsAppUrl,
  isWhatsAppPhoneValid,
  normalizeWhatsAppPhone,
  resolveConsultorioName,
} from "./whatsapp"

const SLOT = "2026-09-15T18:30:00.000-03:00"
const ORG = "Consultorio Norte"
const PROF = "Dra. Pérez"

function slotParts(iso: string) {
  const d = new Date(iso)
  return {
    weekday: d.toLocaleDateString("es-AR", { weekday: "long" }),
    date: d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit" }),
    time: d.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit", hour12: false }),
  }
}

describe("WSP-01 WhatsApp un clic", () => {
  it("normaliza teléfono argentino con 0 inicial", () => {
    expect(normalizeWhatsAppPhone("0261 555-0000")).toBe("542615550000")
  })

  it("arma URL wa.me con mensaje codificado", () => {
    const url = buildWhatsAppUrl("2615550000", "Hola María")
    expect(url).toBe("https://wa.me/542615550000?text=Hola%20Mar%C3%ADa")
  })

  it("genera recordatorio de turno con nombre y fecha", () => {
    const msg = buildAppointmentReminderMessage("María", SLOT, ORG, PROF)
    const { weekday, date, time } = slotParts(SLOT)
    expect(msg).toContain("Hola María")
    expect(msg).toContain(ORG)
    expect(msg).toContain("Te recordamos que tenés turno")
    expect(msg.toLowerCase()).toContain(weekday)
    expect(msg).toContain(date)
    expect(msg).toContain(time)
    expect(msg).toContain(PROF)
    expect(msg).not.toContain("DNI")
  })
})

describe("WhatsApp contextual", () => {
  it("usa el nombre real del consultorio y fallback si falta", () => {
    expect(resolveConsultorioName("Consultorio Integral Mendoza")).toBe(
      "Consultorio Integral Mendoza",
    )
    expect(resolveConsultorioName("  ")).toBe(FALLBACK_CONSULTORIO_NAME)
    expect(resolveConsultorioName(null)).toBe(FALLBACK_CONSULTORIO_NAME)
    expect(resolveConsultorioName(undefined)).toBe(FALLBACK_CONSULTORIO_NAME)
  })

  it("recordatorio incluye paciente, consultorio, profesional, fecha y hora", () => {
    const msg = buildAppointmentWhatsAppMessage("reminder", {
      patientFirstName: "María",
      startAtIso: SLOT,
      orgName: ORG,
      professionalName: PROF,
    })
    expect(msg).toContain("Hola María, te escribimos desde Consultorio Norte.")
    expect(msg).toContain("Te recordamos que tenés turno")
    expect(msg).toContain(`con ${PROF}`)
    expect(msg).toContain("hs")
  })

  it("confirmación pide confirmar el turno sin cambiar estados", () => {
    const msg = buildAppointmentWhatsAppMessage("confirm", {
      patientFirstName: "María",
      startAtIso: SLOT,
      orgName: ORG,
      professionalName: PROF,
    })
    expect(msg).toContain("Queríamos confirmar tu turno")
    expect(msg).toContain(PROF)
    expect(msg).not.toMatch(/DNI|diagnóstico|historia/i)
  })

  it("reprogramación informa el nuevo día y horario", () => {
    const msg = buildAppointmentWhatsAppMessage("reschedule", {
      patientFirstName: "María",
      startAtIso: SLOT,
      orgName: ORG,
      professionalName: PROF,
    })
    const { date, time } = slotParts(SLOT)
    expect(msg).toContain("Tu turno fue reprogramado")
    expect(msg).toContain(date)
    expect(msg).toContain(time)
  })

  it("cancelación avisa y ofrece coordinar otro horario", () => {
    const msg = buildAppointmentWhatsAppMessage("cancel", {
      patientFirstName: "María",
      startAtIso: SLOT,
      orgName: ORG,
    })
    expect(msg).toContain("fue cancelado")
    expect(msg).toContain("coordinar un nuevo horario")
    expect(msg).not.toContain("con ")
  })

  it("disponibilidad queda lista para lista de espera", () => {
    const msg = buildAvailabilityMessage({
      patientFirstName: "María",
      startAtIso: SLOT,
      orgName: ORG,
      professionalName: PROF,
    })
    expect(msg).toContain("Se liberó un turno")
    expect(msg).toContain("Si te interesa, respondé a este mensaje")
  })

  it("omite el profesional si no hay nombre", () => {
    const msg = buildAppointmentWhatsAppMessage("reminder", {
      patientFirstName: "María",
      startAtIso: SLOT,
      orgName: ORG,
    })
    expect(msg).not.toContain(" con ")
  })

  it("antepone mañana si el turno es el día siguiente", () => {
    const now = new Date()
    const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 15, 30, 0)
    const msg = buildAppointmentWhatsAppMessage("reminder", {
      patientFirstName: "María",
      startAtIso: tomorrow.toISOString(),
      orgName: ORG,
    })
    expect(msg).toContain("mañana")
  })

  it("deuda particular puede incluir monto formateado y no incluye DNI", () => {
    const withAmount = buildPrivateDebtMessage("María", ORG, 15000)
    expect(withAmount).toContain("Hola María, te escribimos desde Consultorio Norte.")
    expect(withAmount).toContain("pendiente el pago")
    expect(withAmount).toContain(formatMoney(15000))
    expect(withAmount).not.toContain("DNI")
    expect(withAmount).not.toMatch(/diagnóstico|tratamiento|historia clínica/i)

    const withoutAmount = buildPrivateDebtMessage("María", ORG)
    expect(withoutAmount).not.toContain("El saldo es de")
  })

  it("deuda no muestra saldo si el monto es 0 o inválido", () => {
    expect(buildPrivateDebtMessage("María", ORG, 0)).not.toContain("El saldo es de")
    expect(buildPrivateDebtMessage("María", ORG, "abc")).not.toContain("El saldo es de")
  })

  it("acepta teléfonos válidos y rechaza inválidos", () => {
    expect(isWhatsAppPhoneValid("2615550000")).toBe(true)
    expect(isWhatsAppPhoneValid("+54 9 11 5555-1234")).toBe(true)
    expect(isWhatsAppPhoneValid("0261 555-0000")).toBe(true)
    expect(isWhatsAppPhoneValid("")).toBe(false)
    expect(isWhatsAppPhoneValid("   ")).toBe(false)
    expect(isWhatsAppPhoneValid(null)).toBe(false)
    expect(isWhatsAppPhoneValid("123")).toBe(false)
    expect(isWhatsAppPhoneValid("abc")).toBe(false)
  })

  it("no arma href si el teléfono es inválido", () => {
    expect(buildWhatsAppHref("", "Hola")).toBeNull()
    expect(buildWhatsAppHref("123", "Hola")).toBeNull()
    const href = buildWhatsAppHref("2615550000", "Hola María")
    expect(href).toBe("https://wa.me/542615550000?text=Hola%20Mar%C3%ADa")
  })

  it("codifica caracteres especiales en la URL", () => {
    const msg = buildAppointmentWhatsAppMessage("reminder", {
      patientFirstName: "María",
      startAtIso: SLOT,
      orgName: "Consultorio Ñandú",
    })
    const url = buildWhatsAppUrl("2615550000", msg)
    expect(url.startsWith("https://wa.me/542615550000?text=")).toBe(true)
    expect(url).toContain(encodeURIComponent("María"))
    expect(url).toContain(encodeURIComponent("Ñandú"))
    expect(decodeURIComponent(url.split("text=")[1])).toBe(msg)
  })
})
