import type { Appointment, AppointmentClosureStatus } from "@/types/api"

export function defaultClosureType(
  attentionType: Appointment["attention_type"] | null | undefined,
): AppointmentClosureStatus {
  return attentionType === "health_insurance" ? "insurance_pending" : "paid"
}

/** Monto del input de cierre. Vacío si no hay importe esperado > 0. */
export function closureAmountInput(expectedAmount: Appointment["expected_amount"] | null | undefined): string {
  if (expectedAmount == null || expectedAmount === "") return ""
  const value = Number(expectedAmount)
  return Number.isFinite(value) && value > 0 ? String(value) : ""
}
