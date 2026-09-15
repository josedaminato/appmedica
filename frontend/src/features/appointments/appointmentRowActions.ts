import type { Appointment } from "@/types/api"

export type RowAction = {
  id: string
  label: string
  variant?: "default" | "secondary" | "outline" | "ghost" | "destructive"
  href?: string
  external?: boolean
  primary?: boolean
}

export function buildAppointmentActions(
  a: Appointment,
  needsClose: boolean,
  allowClinical: boolean,
): RowAction[] {
  const actions: RowAction[] = []

  if (a.status === "pending") {
    actions.push({ id: "confirm", label: "Confirmar", variant: "secondary", primary: true })
  }
  if (a.status === "pending" || a.status === "confirmed") {
    if (allowClinical) {
      actions.push({ id: "atender", label: "Atender", primary: a.status === "confirmed" })
    } else {
      actions.push({
        id: "attend",
        label: "Asistió",
        primary: a.status === "confirmed",
      })
    }
    actions.push({ id: "no_show", label: "Ausente", variant: "outline" })
    actions.push({ id: "reschedule", label: "Reprogramar", variant: "ghost" })
    actions.push({ id: "cancel", label: "Cancelar", variant: "ghost" })
  }
  if (a.status === "attended" && allowClinical) {
    actions.push({ id: "atender", label: "Atender", primary: !needsClose })
  }
  if (a.status === "no_show") {
    actions.push({ id: "reschedule", label: "Reprogramar", variant: "ghost", primary: true })
  }
  if (needsClose) {
    actions.push({ id: "close", label: "Registrar cobro", primary: true })
  }
  if (a.closure_status === "pending" || a.closure_status === "partial") {
    actions.push({
      id: "payment",
      label: "Cobrar",
      variant: "outline",
      primary: !needsClose && a.status !== "pending" && a.status !== "confirmed",
    })
  }

  const withPrimary = actions.find((act) => act.primary)
  if (!withPrimary && actions.length > 0) actions[0].primary = true

  return actions
}

export function canOpenClinicalAttention(a: Appointment, allowClinical: boolean): boolean {
  const needsClose = a.status === "attended" && a.closure_status === "none"
  return buildAppointmentActions(a, needsClose, allowClinical).some((act) => act.id === "atender")
}

export function baseAppointment(overrides: Partial<Appointment> = {}): Appointment {
  return {
    id: "a1",
    organization_id: "o1",
    patient_id: "p1",
    professional_id: "u1",
    health_insurance_id: null,
    rescheduled_to_id: null,
    series_id: null,
    start_at: "2026-09-05T15:00:00Z",
    end_at: "2026-09-05T16:00:00Z",
    status: "confirmed",
    modality: "presencial",
    attention_type: "private",
    expected_amount: "10000",
    closure_status: "none",
    notes: null,
    created_at: "2026-09-01T12:00:00Z",
    updated_at: "2026-09-01T12:00:00Z",
    ...overrides,
  }
}
