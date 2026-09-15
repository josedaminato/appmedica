import { describe, expect, it } from "vitest"
import { baseAppointment, buildAppointmentActions, canOpenClinicalAttention } from "./appointmentRowActions"

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
    expect(actions.some((a) => a.id === "close" && a.label === "Registrar cobro")).toBe(true)
    expect(actions.find((a) => a.primary)?.id).toBe("close")
  })

  it("no incluye cierre automático al atender — cobro es acción separada", () => {
    const actions = buildAppointmentActions(baseAppointment(), false, true)
    expect(actions.some((a) => a.id === "close")).toBe(false)
  })

  it("Atender está disponible en pending/confirmed/attended y no en ausente o cancelado", () => {
    expect(canOpenClinicalAttention(baseAppointment({ status: "pending" }), true)).toBe(true)
    expect(canOpenClinicalAttention(baseAppointment({ status: "confirmed" }), true)).toBe(true)
    expect(canOpenClinicalAttention(baseAppointment({ status: "attended" }), true)).toBe(true)
    expect(canOpenClinicalAttention(baseAppointment({ status: "no_show" }), true)).toBe(false)
    expect(canOpenClinicalAttention(baseAppointment({ status: "cancelled" }), true)).toBe(false)
    expect(canOpenClinicalAttention(baseAppointment({ status: "confirmed" }), false)).toBe(false)
  })
})
