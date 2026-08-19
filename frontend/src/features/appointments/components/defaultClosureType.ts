import type { Appointment, AppointmentClosureStatus } from "@/types/api"

export function defaultClosureType(
  attentionType: Appointment["attention_type"] | null | undefined,
): AppointmentClosureStatus {
  return attentionType === "health_insurance" ? "insurance_pending" : "paid"
}
