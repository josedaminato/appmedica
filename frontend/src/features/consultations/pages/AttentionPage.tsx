import { useEffect, useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { QueryErrorState } from "@/components/shared/QueryErrorState"
import { FeedbackBanner } from "@/components/shared/FeedbackBanner"
import { CloseAppointmentDialog } from "@/features/appointments/components/CloseAppointmentDialog"
import * as apptApi from "@/features/appointments/api"
import { listHealthInsurances } from "@/features/insurances/api"
import { getPatient } from "@/features/patients/api"
import { useRoleScope } from "@/hooks/use-role-scope"
import { ApiError } from "@/lib/api-client"
import { formatDate, formatDateTime, formatMoney, formatTime } from "@/lib/format"
import type { Appointment } from "@/types/api"
import { ClinicalProfileEditDialog } from "../components/ClinicalProfileEditDialog"
import { ConsultationReadOnlyView } from "../components/ConsultationReadOnlyView"
import { canEditConsultation, consultationPath, timelineSortKey } from "../consultationPresentation"
import * as consultationApi from "../api"

function patientAge(birthDate: string | null | undefined): string | null {
  if (!birthDate) return null
  const birth = new Date(birthDate.includes("T") ? birthDate : `${birthDate}T12:00:00`)
  const today = new Date()
  let age = today.getFullYear() - birth.getFullYear()
  const m = today.getMonth() - birth.getMonth()
  if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age -= 1
  return age >= 0 ? `${age} años` : null
}

export function AttentionPage() {
  const { appointmentId, consultationId } = useParams<{
    appointmentId?: string
    consultationId?: string
  }>()
  const isAgendaFlow = Boolean(appointmentId)
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { isStaff, user } = useRoleScope()

  const [reason, setReason] = useState("")
  const [evolution, setEvolution] = useState("")
  const [diagnosis, setDiagnosis] = useState("")
  const [indications, setIndications] = useState("")
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [finalizeOpen, setFinalizeOpen] = useState(false)
  const [amendOpen, setAmendOpen] = useState(false)
  const [amendReason, setAmendReason] = useState("")
  const [clinicalEditOpen, setClinicalEditOpen] = useState(false)
  const [closeOpen, setCloseOpen] = useState(false)
  const [appointment, setAppointment] = useState<Appointment | null>(null)

  useEffect(() => {
    if (isStaff) navigate(isAgendaFlow ? "/agenda" : "/patients", { replace: true })
  }, [isStaff, navigate, isAgendaFlow])

  const consultationQuery = useQuery({
    queryKey: ["consultation", appointmentId ?? consultationId],
    queryFn: () =>
      isAgendaFlow
        ? consultationApi.getOrCreateConsultation(appointmentId!)
        : consultationApi.getConsultation(consultationId!),
    enabled: Boolean(appointmentId || consultationId) && !isStaff,
    retry: false,
  })

  const patientQuery = useQuery({
    queryKey: ["patient", consultationQuery.data?.patient_id],
    queryFn: () => getPatient(consultationQuery.data!.patient_id),
    enabled: !!consultationQuery.data?.patient_id,
  })

  const clinicalQuery = useQuery({
    queryKey: ["patient-clinical", consultationQuery.data?.patient_id],
    queryFn: () => consultationApi.getPatientClinical(consultationQuery.data!.patient_id),
    enabled: !!consultationQuery.data?.patient_id,
    retry: false,
  })

  const historyQuery = useQuery({
    queryKey: ["patient-consultations", consultationQuery.data?.patient_id],
    queryFn: () => consultationApi.listPatientConsultations(consultationQuery.data!.patient_id),
    enabled: !!consultationQuery.data?.patient_id,
    retry: false,
  })

  const { data: insurances = [] } = useQuery({
    queryKey: ["insurances"],
    queryFn: () => listHealthInsurances(),
  })

  useEffect(() => {
    const c = consultationQuery.data
    if (!c) return
    setReason(c.reason ?? "")
    setEvolution(c.evolution ?? "")
    setDiagnosis(c.diagnosis ?? "")
    setIndications(c.indications ?? "")
  }, [consultationQuery.data?.id, consultationQuery.data?.updated_at])

  useEffect(() => {
    const loadedId = appointmentId ?? consultationQuery.data?.appointment_id
    if (!loadedId) {
      setAppointment(null)
      return
    }
    apptApi.getAppointment(loadedId).then(setAppointment).catch(() => setAppointment(null))
  }, [appointmentId, consultationQuery.data?.appointment_id])

  const saveDraft = useMutation({
    mutationFn: () =>
      consultationApi.updateConsultation(consultationQuery.data!.id, {
        reason: reason || null,
        evolution: evolution || null,
        diagnosis: diagnosis || null,
        indications: indications || null,
      }),
    onSuccess: (data) => {
      setError("")
      setSuccess("Borrador guardado")
      qc.setQueryData(["consultation", appointmentId ?? consultationId], data)
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Error al guardar"),
  })

  const finalize = useMutation({
    mutationFn: async () => {
      await consultationApi.updateConsultation(consultationQuery.data!.id, {
        reason,
        evolution,
        diagnosis: diagnosis || null,
        indications: indications || null,
      })
      return consultationApi.finalizeConsultation(consultationQuery.data!.id)
    },
    onSuccess: (data) => {
      setFinalizeOpen(false)
      setError("")
      setSuccess("Consulta finalizada")
      qc.setQueryData(["consultation", appointmentId ?? consultationId], data)
      qc.invalidateQueries({ queryKey: ["patient-consultations"] })
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Error al finalizar"),
  })

  const updateClinical = useMutation({
    mutationFn: (payload: Parameters<typeof consultationApi.updatePatientClinical>[1]) =>
      consultationApi.updatePatientClinical(consultationQuery.data!.patient_id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["patient-clinical", consultationQuery.data?.patient_id] })
    },
  })

  const closeMutation = useMutation({
    mutationFn: (data: apptApi.ClosePayload) => apptApi.closeAppointment(appointmentId!, data),
    onSuccess: () => {
      setCloseOpen(false)
      setSuccess("Cobro registrado")
      qc.invalidateQueries({ queryKey: ["appointments"] })
      qc.invalidateQueries({ queryKey: ["dashboard"] })
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Error al registrar cobro"),
  })

  const createAmendment = useMutation({
    mutationFn: () =>
      consultationApi.createConsultationAmendment(consultationQuery.data!.id, amendReason),
    onMutate: () => setError(""),
    onSuccess: (created) => {
      setAmendOpen(false)
      setAmendReason("")
      qc.invalidateQueries({ queryKey: ["patient-consultations"] })
      navigate(`/consultations/${created.id}`)
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Error al registrar la corrección"),
  })

  if (consultationQuery.isLoading) return <LoadingSkeleton rows={6} />
  if (consultationQuery.isError) {
    return (
      <QueryErrorState
        error={consultationQuery.error}
        onRetry={() => consultationQuery.refetch()}
      />
    )
  }

  const consultation = consultationQuery.data!
  const patient = patientQuery.data
  const isFinalized = consultation.status === "finalized"
  const canEdit = canEditConsultation(consultation, user)
  const previous = (historyQuery.data ?? []).filter((c) => c.id !== consultation.id).slice(0, 5)
  const patientLabel = patient
    ? `${patient.last_name}, ${patient.first_name}`
    : "Paciente"
  const age = patientAge(patient?.birth_date)
  const backTo = isAgendaFlow
    ? "/agenda"
    : patient
      ? `/patients/${patient.id}#historia-clinica`
      : "/patients"
  const backLabel = isAgendaFlow ? "Volver a turnos" : "Volver al paciente"

  return (
    <div className="max-w-3xl mx-auto">
      <Button variant="ghost" size="sm" className="mb-4 -ml-2" asChild>
        <Link to={backTo}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          {backLabel}
        </Link>
      </Button>

      <header className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-primary mb-1">Atención</p>
        <h1 className="text-2xl font-semibold">{patientLabel}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          DNI {patient?.dni ?? "—"}
          {age ? ` · ${age}` : ""}
        </p>
        {appointment && (
          <p className="text-sm text-muted-foreground mt-1">
            {formatDate(appointment.start_at)} {formatTime(appointment.start_at)}
            {appointment.professional?.full_name ? ` · ${appointment.professional.full_name}` : ""}
            {" · "}
            {appointment.modality === "online" ? "Online" : "Presencial"}
          </p>
        )}
        {patient && (
          <Button variant="link" className="px-0 h-auto mt-1" asChild>
            <Link to={`/patients/${patient.id}`}>Ver paciente</Link>
          </Button>
        )}
      </header>

      {error && <FeedbackBanner variant="error" message={error} />}
      {success && <FeedbackBanner variant="success" message={success} />}

      <Card className="mb-6">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Información clínica previa</CardTitle>
          {canEdit && (
            <Button variant="outline" size="sm" onClick={() => setClinicalEditOpen(true)}>
              Editar información clínica
            </Button>
          )}
        </CardHeader>
        <CardContent className="grid gap-3 text-sm sm:grid-cols-2">
          <ClinicalInfo label="Antecedentes" value={clinicalQuery.data?.medical_history} />
          <ClinicalInfo label="Alergias" value={clinicalQuery.data?.allergies} />
          <ClinicalInfo label="Medicación habitual" value={clinicalQuery.data?.current_medications} />
          <ClinicalInfo label="Observaciones clínicas" value={clinicalQuery.data?.clinical_notes} className="sm:col-span-2" />
          {clinicalQuery.data?.clinical_updated_at && (
            <p className="text-xs text-muted-foreground sm:col-span-2">
              Última actualización
              {clinicalQuery.data.clinical_updated_by_name
                ? ` · ${clinicalQuery.data.clinical_updated_by_name}`
                : ""}
              {" · "}
              {formatDateTime(clinicalQuery.data.clinical_updated_at)}
            </p>
          )}
        </CardContent>
      </Card>

      {previous.length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">Últimas consultas</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {previous.map((item) => (
              <div key={item.id} className="flex justify-between items-start gap-3 border-b pb-3 last:border-0 last:pb-0">
                <div>
                  <p className="text-sm font-medium">
                    {formatDate(timelineSortKey(item))}
                  </p>
                  <p className="text-sm">{item.reason || "Consulta"}</p>
                  {item.diagnosis && (
                    <p className="text-xs text-muted-foreground">{item.diagnosis}</p>
                  )}
                </div>
                <Button variant="ghost" size="sm" asChild>
                  <Link to={consultationPath(item)}>Ver consulta</Link>
                </Button>
              </div>
            ))}
            {patient && (
              <Button variant="link" className="px-0" asChild>
                <Link to={`/patients/${patient.id}#historia-clinica`}>Ver historia clínica completa</Link>
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {canEdit ? (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">Consulta actual</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <FormField label="Motivo de consulta" id="reason" value={reason} onChange={setReason} required />
            <FormField label="Evolución / observaciones" id="evolution" value={evolution} onChange={setEvolution} rows={5} required />
            <FormField label="Diagnóstico" id="diagnosis" value={diagnosis} onChange={setDiagnosis} />
            <FormField label="Indicaciones / tratamiento" id="indications" value={indications} onChange={setIndications} rows={3} />
            <div className="flex flex-wrap gap-2 pt-2">
              <Button variant="outline" onClick={() => saveDraft.mutate()} disabled={saveDraft.isPending}>
                Guardar borrador
              </Button>
              <Button onClick={() => setFinalizeOpen(true)}>Finalizar consulta</Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          <ConsultationReadOnlyView
            consultation={consultation}
            patientName={patientLabel}
            appointmentStartAt={appointment?.start_at}
            professionalName={consultation.professional_name}
          />
          {isFinalized && (
            <Card className="mt-6">
              <CardHeader>
                <CardTitle className="text-base">Consulta finalizada</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Esta consulta no se edita. Para dejar constancia de un cambio hay que registrar una corrección.
                </p>
                <Button onClick={() => setAmendOpen(true)}>Registrar corrección</Button>
                {isAgendaFlow && appointment && appointment.closure_status === "none" && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Cobro</p>
                    {appointment.expected_amount && (
                      <p className="text-lg font-semibold mb-3">{formatMoney(appointment.expected_amount)}</p>
                    )}
                    <div className="flex flex-wrap gap-2">
                      <Button onClick={() => setCloseOpen(true)}>Registrar cobro</Button>
                      <Button variant="outline" onClick={() => setCloseOpen(true)}>
                        Dejar pendiente
                      </Button>
                    </div>
                  </div>
                )}
                {isAgendaFlow && appointment && appointment.closure_status !== "none" && (
                  <p className="text-sm text-muted-foreground">
                    Este turno ya tiene un cierre administrativo registrado.
                  </p>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}

      <ClinicalProfileEditDialog
        open={clinicalEditOpen}
        onOpenChange={setClinicalEditOpen}
        profile={clinicalQuery.data ?? null}
        onSubmit={async (data) => {
          await updateClinical.mutateAsync(data)
        }}
        loading={updateClinical.isPending}
      />

      <Dialog open={amendOpen} onOpenChange={setAmendOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Registrar corrección</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Se crea una nueva entrada en borrador. La consulta original no se modifica.
          </p>
          <div className="space-y-2">
            <Label htmlFor="amend-reason">
              Motivo de la corrección<span className="text-destructive ml-0.5">*</span>
            </Label>
            <Textarea
              id="amend-reason"
              rows={3}
              value={amendReason}
              onChange={(e) => setAmendReason(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setAmendOpen(false)}>Cancelar</Button>
            <Button
              onClick={() => createAmendment.mutate()}
              disabled={createAmendment.isPending || !amendReason.trim()}
            >
              Crear corrección
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={finalizeOpen} onOpenChange={setFinalizeOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>¿Finalizar consulta?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            La consulta quedará registrada en la Historia Clínica del paciente.
            {isAgendaFlow ? " Podrás registrar el cobro por separado." : ""}
          </p>
          <div className="flex gap-2 justify-end pt-2">
            <Button variant="outline" onClick={() => setFinalizeOpen(false)}>Cancelar</Button>
            <Button onClick={() => finalize.mutate()} disabled={finalize.isPending}>
              Finalizar consulta
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <CloseAppointmentDialog
        open={closeOpen}
        onOpenChange={setCloseOpen}
        appointment={appointment}
        insurances={insurances}
        onSubmit={async (data) => {
          await closeMutation.mutateAsync(data)
        }}
        loading={closeMutation.isPending}
      />
    </div>
  )
}

function ClinicalInfo({
  label,
  value,
  className,
}: {
  label: string
  value?: string | null
  className?: string
}) {
  return (
    <div className={className}>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium mt-0.5">{value?.trim() || "Sin información registrada"}</p>
    </div>
  )
}

function FormField({
  label,
  id,
  value,
  onChange,
  rows = 3,
  required,
}: {
  label: string
  id: string
  value: string
  onChange: (v: string) => void
  rows?: number
  required?: boolean
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>
        {label}
        {required && <span className="text-destructive ml-0.5">*</span>}
      </Label>
      <Textarea id={id} rows={rows} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  )
}
