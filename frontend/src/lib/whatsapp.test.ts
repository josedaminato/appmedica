import { describe, expect, it } from "vitest"
import {
  buildAppointmentReminderMessage,
  buildWhatsAppUrl,
  normalizeWhatsAppPhone,
} from "./whatsapp"

describe("WSP-01 WhatsApp un clic", () => {
  it("normaliza teléfono argentino con 0 inicial", () => {
    expect(normalizeWhatsAppPhone("0261 555-0000")).toBe("542615550000")
  })

  it("arma URL wa.me con mensaje codificado", () => {
    const url = buildWhatsAppUrl("2615550000", "Hola María")
    expect(url).toBe("https://wa.me/542615550000?text=Hola%20Mar%C3%ADa")
  })

  it("genera recordatorio de turno con nombre y fecha", () => {
    const msg = buildAppointmentReminderMessage(
      "María",
      "2026-09-15T11:00:00.000Z",
      "Consultorio Norte",
    )
    expect(msg).toContain("Hola María")
    expect(msg).toContain("Consultorio Norte")
    expect(msg).toContain("reprogramar")
  })
})
