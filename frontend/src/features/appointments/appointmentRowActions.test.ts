import { describe, expect, it } from "vitest"
import { baseAppointment, buildAppointmentActions } from "./appointmentRowActions"

describe("buildAppointmentActions", () => {
  it("muestra Atender para turno confirmado cuando hay acceso clínico", () => {
    const actions = buildAppointmentActions(baseAppointment(), false, true)
    expect(actions.some((a) => a.id === "atender" && a.label === "Atender")).toBe(true)
    expect(actions.some((a) => a.id === "attend")).toBe(false)
  })

  it("staff ve Asistió en lugar de Atender", () => {
    const actions = buildAppointmentActions(baseAppointment(), false, false)
    expect(actions.some((a) => a.id === "attend")).toBe(true)
    expect(actions.some((a) => a.id === "atender")).toBe(false)
  })

  it("turno attended con acceso clínico permite continuar atención", () => {
    const actions = buildAppointmentActions(
      baseAppointment({ status: "attended" }),
      true,
      true,
    )
    expect(actions.some((a) => a.id === "atender")).toBe(true)
    expect(actions.some((a) => a.id === "close")).toBe(true)
  })

  it("no incluye cierre automático al atender — close es acción separada", () => {
    const actions = buildAppointmentActions(baseAppointment(), false, true)
    expect(actions.some((a) => a.id === "close")).toBe(false)
  })
})
