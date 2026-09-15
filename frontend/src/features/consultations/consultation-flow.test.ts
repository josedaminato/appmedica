import { describe, expect, it } from "vitest"
import type { Consultation, ConsultationListItem } from "@/types/api"
import {
  canCreateStandaloneClinicalNote,
  canEditConsultation,
  consultationKind,
  consultationPath,
  groupClinicalTimeline,
} from "./consultationPresentation"

const baseConsultation: Consultation = {
  id: "c1",
  organization_id: "o1",
  appointment_id: "a1",
  patient_id: "p1",
  professional_id: "u1",
  professional_name: "Dr. Juan Pérez",
  professional_name_snapshot: "Dr. Juan Pérez",
  professional_license_snapshot: null,
  amends_id: null,
  amend_reason: null,
  occurred_at: "2026-09-01T12:00:00Z",
  reason: "Dolor",
  evolution: "Evolución",
  diagnosis: null,
  indications: null,
  status: "finalized",
  created_at: "2026-09-01T12:00:00Z",
  updated_at: "2026-09-01T12:00:00Z",
  created_by: "u1",
  updated_by: "u1",
}

describe("consultation flow helpers", () => {
  it("consulta finalizada no permite edición normal", () => {
    expect(canEditConsultation(baseConsultation, { id: "u1", role: "professional" })).toBe(false)
  })

  it("borrador propio permite edición", () => {
    const draft: Consultation = { ...baseConsultation, status: "draft", reason: "", evolution: "" }
    expect(canEditConsultation(draft, { id: "u1", role: "professional" })).toBe(true)
  })

  it("professional no edita draft ajeno", () => {
    const draft: Consultation = { ...baseConsultation, status: "draft", professional_id: "u2" }
    expect(canEditConsultation(draft, { id: "u1", role: "professional" })).toBe(false)
  })

  it("owner puede editar draft ajeno", () => {
    const draft: Consultation = { ...baseConsultation, status: "draft", professional_id: "u2" }
    expect(canEditConsultation(draft, { id: "owner", role: "owner" })).toBe(true)
  })
})

describe("canCreateStandaloneClinicalNote", () => {
  it("professional ve Nueva nota clínica aunque GET /clinical sea 403", () => {
    expect(canCreateStandaloneClinicalNote({
      role: "professional",
      clinicalForbidden: true,
    })).toBe(true)
  })

  it("professional con perfil clínico accesible sigue pudiendo crear nota", () => {
    expect(canCreateStandaloneClinicalNote({
      role: "professional",
      clinicalForbidden: false,
    })).toBe(true)
  })

  it("staff no ve Nueva nota clínica", () => {
    expect(canCreateStandaloneClinicalNote({
      role: "staff",
      clinicalForbidden: false,
    })).toBe(false)
  })

  it("owner mantiene la acción de nueva nota", () => {
    expect(canCreateStandaloneClinicalNote({
      role: "owner",
      clinicalForbidden: false,
    })).toBe(true)
  })
})

describe("consultationPath", () => {
  it("no genera /agenda/null para notas sin turno", () => {
    expect(consultationPath({ id: "c9", appointment_id: null, amends_id: null })).toBe(
      "/consultations/c9",
    )
  })

  it("correcciones usan la ruta por id aunque tengan turno", () => {
    expect(consultationPath({ id: "c2", appointment_id: "a1", amends_id: "c1" })).toBe(
      "/consultations/c2",
    )
  })

  it("consulta primaria con turno sigue yendo a agenda", () => {
    expect(consultationPath({ id: "c1", appointment_id: "a1", amends_id: null })).toBe(
      "/agenda/a1/atencion",
    )
  })
})

describe("timeline grouping", () => {
  it("agrupa correcciones bajo la consulta original y distingue tipos", () => {
    const visit: ConsultationListItem = {
      id: "c1",
      appointment_id: "a1",
      professional_id: "u1",
      professional_name: "Dr A",
      appointment_start_at: "2026-09-15T10:00:00Z",
      amends_id: null,
      amend_reason: null,
      occurred_at: "2026-09-15T10:00:00Z",
      reason: "Dolor",
      evolution: "Mejora",
      diagnosis: "Lumbalgia",
      status: "finalized",
      created_at: "2026-09-15T10:00:00Z",
      updated_at: "2026-09-15T10:00:00Z",
    }
    const note: ConsultationListItem = {
      ...visit,
      id: "c3",
      appointment_id: null,
      appointment_start_at: null,
      occurred_at: "2026-09-01T10:00:00Z",
      created_at: "2026-09-01T10:00:00Z",
      reason: "Llamada",
    }
    const amendment: ConsultationListItem = {
      ...visit,
      id: "c2",
      amends_id: "c1",
      amend_reason: "Error de tipeo",
      occurred_at: "2026-09-16T10:00:00Z",
      created_at: "2026-09-16T10:00:00Z",
    }
    const grouped = groupClinicalTimeline([note, amendment, visit])
    expect(grouped.map((entry) => entry.primary.id)).toEqual(["c1", "c3"])
    expect(grouped[0].amendments.map((item) => item.id)).toEqual(["c2"])
    expect(consultationKind(visit)).toBe("visit")
    expect(consultationKind(note)).toBe("note")
    expect(consultationKind(amendment)).toBe("amendment")
  })
})
