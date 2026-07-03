import { describe, expect, it } from "vitest"
import {
  formatDate,
  isoToLocalDateParam,
  toDateParam,
  todayDateParam,
} from "./format"

describe("fechas locales (agenda, America/Argentina/Buenos_Aires)", () => {
  it("toDateParam usa el día local, no UTC", () => {
    const evening = new Date(2026, 5, 25, 22, 0, 0)
    expect(toDateParam(evening)).toBe("2026-06-25")
    expect(evening.toISOString().slice(0, 10)).toBe("2026-06-26")
  })

  it("isoToLocalDateParam recupera el día local desde ISO UTC", () => {
    expect(isoToLocalDateParam("2026-06-26T01:00:00.000Z")).toBe("2026-06-25")
  })

  it("todayDateParam coincide con toDateParam de ahora", () => {
    expect(todayDateParam()).toBe(toDateParam(new Date()))
  })

  it("formatDate de una fecha pura no corre al día anterior", () => {
    // birth_date / service_date llegan como "YYYY-MM-DD"; new Date() los tomaría
    // como medianoche UTC y en Argentina (UTC-3) mostraría el día previo.
    expect(formatDate("2026-06-25")).toContain("25")
    expect(formatDate("2026-06-25")).not.toContain("24")
  })

  it("formatDate de un datetime ISO con zona respeta el día local", () => {
    expect(formatDate("2026-06-25T11:00:00.000Z")).toContain("25")
  })
})
