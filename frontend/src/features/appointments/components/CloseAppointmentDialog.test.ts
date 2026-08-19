import { describe, expect, it } from "vitest"
import { defaultClosureType } from "./defaultClosureType"

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
