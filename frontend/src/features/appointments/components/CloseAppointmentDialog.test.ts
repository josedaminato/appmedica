import { describe, expect, it } from "vitest"
import { closureAmountInput, defaultClosureType } from "./defaultClosureType"

describe("defaultClosureType", () => {
  it("turno particular abre en cobrado", () => {
    expect(defaultClosureType("private")).toBe("paid")
  })

  it("turno OS abre en pendiente OS", () => {
    expect(defaultClosureType("health_insurance")).toBe("insurance_pending")
  })

  it("sin tipo o valor inesperado sigue en cobrado", () => {
    expect(defaultClosureType(undefined)).toBe("paid")
    expect(defaultClosureType(null)).toBe("paid")
  })
})

describe("closureAmountInput", () => {
  it("precarga un monto esperado mayor a cero", () => {
    expect(closureAmountInput("15000.00")).toBe("15000")
    expect(closureAmountInput("2500")).toBe("2500")
  })

  it("deja vacío si no hay importe usable", () => {
    expect(closureAmountInput(null)).toBe("")
    expect(closureAmountInput(undefined)).toBe("")
    expect(closureAmountInput("")).toBe("")
    expect(closureAmountInput("0")).toBe("")
  })
})
