import type { Consultation, ConsultationListItem } from "@/types/api"

export type ClinicalTimelineEntry = {
  primary: ConsultationListItem
  amendments: ConsultationListItem[]
}

export function consultationKind(item: {
  appointment_id: string | null
  amends_id: string | null
}): "visit" | "note" | "amendment" {
  if (item.amends_id) return "amendment"
  if (item.appointment_id) return "visit"
  return "note"
}

export function consultationPath(item: {
  id: string
  appointment_id: string | null
  amends_id?: string | null
}): string {
  if (item.amends_id || !item.appointment_id) {
    return `/consultations/${item.id}`
  }
  return `/agenda/${item.appointment_id}/atencion`
}

export function timelineSortKey(item: Pick<ConsultationListItem, "occurred_at" | "created_at">): string {
  return item.occurred_at || item.created_at
}

export function groupClinicalTimeline(items: ConsultationListItem[]): ClinicalTimelineEntry[] {
  const amendmentsByOriginal = new Map<string, ConsultationListItem[]>()
  const primaries: ConsultationListItem[] = []
  for (const item of items) {
    if (item.amends_id) {
      const bucket = amendmentsByOriginal.get(item.amends_id) ?? []
      bucket.push(item)
      amendmentsByOriginal.set(item.amends_id, bucket)
    } else {
      primaries.push(item)
    }
  }

  const byDesc = (a: ConsultationListItem, b: ConsultationListItem) => {
    const cmp = timelineSortKey(b).localeCompare(timelineSortKey(a))
    if (cmp !== 0) return cmp
    return b.created_at.localeCompare(a.created_at)
  }
  primaries.sort(byDesc)
  for (const bucket of amendmentsByOriginal.values()) bucket.sort(byDesc)

  const primaryIds = new Set(primaries.map((item) => item.id))
  const entries: ClinicalTimelineEntry[] = primaries.map((primary) => ({
    primary,
    amendments: amendmentsByOriginal.get(primary.id) ?? [],
  }))
  for (const [originalId, bucket] of amendmentsByOriginal) {
    if (primaryIds.has(originalId)) continue
    for (const amendment of bucket) {
      entries.push({ primary: amendment, amendments: [] })
    }
  }
  entries.sort((a, b) => byDesc(a.primary, b.primary))
  return entries
}

export function canEditConsultation(
  consultation: Consultation | null | undefined,
  currentUser?: { id: string; role: string } | null,
): boolean {
  if (!consultation || consultation.status !== "draft") return false
  if (!currentUser || currentUser.role === "staff") return false
  if (currentUser.role === "owner") return true
  return consultation.professional_id === currentUser.id
}

/** Owner/professional pueden crear la primera nota aunque GET /clinical sea 403. */
export function canCreateStandaloneClinicalNote({
  role,
}: {
  role?: string | null
  clinicalForbidden?: boolean
}): boolean {
  return role === "owner" || role === "professional"
}
