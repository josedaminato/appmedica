export type UserRole = "owner" | "professional" | "staff"
export type AppointmentStatus = "pending" | "confirmed" | "attended" | "no_show" | "cancelled" | "rescheduled"
export type AppointmentModality = "presencial" | "online"
export type AttentionType = "private" | "health_insurance"
export type AppointmentClosureStatus = "none" | "paid" | "pending" | "partial" | "insurance_pending"
export type PaymentMethod = "cash" | "transfer" | "mercadopago" | "health_insurance"
export type PaymentStatus = "pending" | "partial" | "paid"
export type InsuranceClaimStatus = "pending" | "invoiced" | "collected" | "rejected"

export interface OrganizationBrief {
  id: string
  name: string
  slug: string
  default_appointment_duration_minutes?: number
  default_private_session_amount?: string | null
}

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  organization: OrganizationBrief
  created_at: string
}

export interface TeamMember {
  id: string
  full_name: string
  email: string
  role: UserRole
  is_active: boolean
}

export interface AuthResponse {
  user: User
  access_token: string
  token_type: string
}

export interface PaginationMeta {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface PaginatedResponse<T> {
  data: T[]
  meta: PaginationMeta
}

export interface Patient {
  id: string
  organization_id: string
  first_name: string
  last_name: string
  dni: string | null
  phone: string | null
  email: string | null
  birth_date: string | null
  health_insurance_id: string | null
  affiliate_number: string | null
  notes: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface PatientBrief {
  id: string
  first_name: string
  last_name: string
  dni: string | null
  phone?: string | null
}

export interface HealthInsuranceBrief {
  id: string
  name: string
}

export interface Appointment {
  id: string
  organization_id: string
  patient_id: string
  professional_id: string | null
  health_insurance_id: string | null
  rescheduled_to_id: string | null
  series_id: string | null
  start_at: string
  end_at: string
  status: AppointmentStatus
  modality: AppointmentModality
  attention_type: AttentionType
  expected_amount: string | null
  closure_status: AppointmentClosureStatus
  notes: string | null
  created_at: string
  updated_at: string
  patient?: PatientBrief
  professional?: { id: string; full_name: string }
  health_insurance?: HealthInsuranceBrief | null
}

export interface HealthInsurance {
  id: string
  organization_id: string
  name: string
  coverage_percent: number | null
  estimated_payment_days: number | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface DashboardSummary {
  appointments_today: number
  unclosed_attended: number
  overdue_unresolved: number
  private_debt_total: string
  insurance_debt_total: string
  patients_with_debt: number
  pending_insurance_claims: number
  no_shows_last_30_days: number
  upcoming_appointments: Appointment[]
}

export interface DashboardAlerts {
  unclosed_attended: { count: number }
  overdue_unresolved: { count: number }
  partial_payments_pending: { count: number; pending_total: string }
  old_insurance_claims: {
    threshold_days: number
    items: {
      health_insurance_id: string
      name: string
      claims_count: number
      debt_total: string
      avg_days_pending: number
    }[]
  }
  top_debt_patients: {
    items: {
      patient_id: string
      patient_name: string
      total_debt: string
      private_debt: string
      insurance_debt: string
    }[]
  }
}

export interface TimelineEvent {
  id: string
  event_type: string
  title: string
  subtitle: string | null
  amount: string | null
  status: string | null
  occurred_at: string
}

export interface PatientAdminSummary {
  patient_id: string
  private_debt: string
  insurance_debt: string
  total_debt: string
  no_show_count: number
  no_shows_last_30_days: number
  upcoming_appointments: Appointment[]
  recent_appointments: Appointment[]
  recent_payments: Payment[]
  pending_claims: InsuranceClaim[]
  timeline: TimelineEvent[]
}

export interface Payment {
  id: string
  patient_id: string
  appointment_id: string | null
  amount: string
  method: PaymentMethod
  status: PaymentStatus
  paid_at: string | null
  notes: string | null
  created_at: string
}

export interface InsuranceClaim {
  id: string
  organization_id?: string
  patient_id: string
  appointment_id: string | null
  health_insurance_id: string
  expected_amount: string
  service_date: string
  status: InsuranceClaimStatus
  invoiced_at: string | null
  collected_at: string | null
  notes: string | null
  created_at: string
  patient_name?: string
  health_insurance_name?: string
  days_since_service?: number
  days_to_collect?: number | null
  days_service_to_invoice?: number | null
}

export interface InsuranceRankingItem {
  health_insurance_id: string
  name: string
  claims_total: number
  claims_collected: number
  claims_open: number
  claims_rejected: number
  open_debt_total: string
  avg_days_to_collect: number | null
  median_days_to_collect: number | null
  pct_collected_within_45_days: number | null
  rejection_rate_pct: number | null
  score: number | null
  rank: number
  rating_label: string
  sample_sufficient: boolean
}

export interface InsuranceRankingResponse {
  items: InsuranceRankingItem[]
  min_sample: number
  period_note: string
}

export interface MessageResponse {
  message: string
}
