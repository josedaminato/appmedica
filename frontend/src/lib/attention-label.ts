import type { Appointment, AttentionType } from "@/types/api"

/** Etiqueta de tipo de atención / cobro para agenda y listados. */
export function attentionLabel(
  attentionType: AttentionType,
  healthInsuranceName?: string | null,
): string {
  if (attentionType === "health_insurance") {
    return healthInsuranceName ? `OS · ${healthInsuranceName}` : "Obra social"
  }
  return "Particular"
}

export function attentionLabelForAppointment(appointment: Appointment): string {
  return attentionLabel(appointment.attention_type, appointment.health_insurance?.name)
}
