import { useEffect, useMemo, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useMutation, useQuery } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { PageHeader } from "@/components/shared/PageHeader"
import { FeedbackBanner } from "@/components/shared/FeedbackBanner"
import { useAuth } from "@/features/auth/AuthContext"
import { listPatients } from "@/features/patients/api"
import { listHealthInsurances } from "@/features/insurances/api"
import { InsuranceCatalogHint } from "@/features/insurances/components/InsuranceCatalogHint"
import { listTeam } from "@/features/users/api"
import { ApiError } from "@/lib/api-client"
import { conflictMessage } from "@/lib/appointment-schedule"
import { formatMoney } from "@/lib/format"
import { StandardDurationHint } from "../components/AgendaDurationSettings"
import {
  AppointmentScheduleFields,
  useScheduleValidation,
} from "../components/AppointmentScheduleFields"
import * as apptApi from "../api"

export function NewAppointmentPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const defaultDuration =
    user?.organization.default_appointment_duration_minutes ?? 30
  const defaultSessionAmount = user?.organization.default_private_session_amount

  const [patientId, setPatientId] = useState("")
  const [professionalId, setProfessionalId] = useState("")
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [time, setTime] = useState("09:00")
  const [durationMinutes, setDurationMinutes] = useState(defaultDuration)

  useEffect(() => {
    setDurationMinutes(defaultDuration)
  }, [defaultDuration])

  const [modality, setModality] = useState<"presencial" | "online">("presencial")
  const [attentionType, setAttentionType] = useState<"private" | "health_insurance">("private")
  const [amount, setAmount] = useState("")

  useEffect(() => {
    if (attentionType === "private" && defaultSessionAmount != null && defaultSessionAmount !== "") {
      setAmount(String(Number(defaultSessionAmount)))
    } else if (attentionType === "health_insurance") {
      setAmount("")
    }
  }, [attentionType, defaultSessionAmount])
  const [insuranceId, setInsuranceId] = useState("")
  const [formError, setFormError] = useState("")

  const [patientQ, setPatientQ] = useState("")

  const { data: patientsData } = useQuery({
    queryKey: ["patients", "picker", patientQ],
    queryFn: () =>
      listPatients({
        page_size: 50,
        is_active: true,
        q: patientQ.trim() || undefined,
      }),
  })
  const { data: insurances = [] } = useQuery({
    queryKey: ["insurances"],
    queryFn: () => listHealthInsurances(),
  })
  const { data: team = [] } = useQuery({ queryKey: ["team"], queryFn: listTeam })

  const professionals = team.filter(
    (m) => m.role === "owner" || m.role === "professional",
  )
  const resolvedProfessionalId =
    professionalId || (user?.role === "professional" ? user.id : professionals[0]?.id ?? "")

  const { data: dayAppointments = [] } = useQuery({
    queryKey: ["appointments", date, "day", resolvedProfessionalId],
    queryFn: () =>
      apptApi.listAppointments({
        date,
        view: "day",
        professional_id: resolvedProfessionalId || undefined,
      }),
    enabled: !!resolvedProfessionalId && !!date,
  })

  const schedule = useScheduleValidation(
    date,
    time,
    durationMinutes,
    dayAppointments,
  )

  const create = useMutation({
    mutationFn: apptApi.createAppointment,
    onSuccess: (appt) => {
      const d = appt.start_at.slice(0, 10)
      navigate(`/agenda?date=${d}`)
    },
    onError: (err) => {
      setFormError(err instanceof ApiError ? err.message : "No se pudo crear el turno")
    },
  })

  const submitDisabled = useMemo(
    () =>
      !patientId ||
      !schedule.valid ||
      !schedule.start ||
      !schedule.end ||
      create.isPending ||
      (attentionType === "health_insurance" && !insuranceId),
    [patientId, schedule, create.isPending, attentionType, insuranceId],
  )

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setFormError("")
    if (!schedule.valid || !schedule.start || !schedule.end) {
      if (schedule.conflict) setFormError(conflictMessage(schedule.conflict))
      return
    }
    await create.mutateAsync({
      patient_id: patientId,
      professional_id: resolvedProfessionalId || null,
      start_at: schedule.start.toISOString(),
      end_at: schedule.end.toISOString(),
      modality,
      attention_type: attentionType,
      expected_amount: amount ? Number(amount) : null,
      health_insurance_id: attentionType === "health_insurance" ? insuranceId || null : null,
    })
  }

  return (
    <div className="max-w-lg">
      <PageHeader
        title="Nuevo turno"
        description={`Horario y duración (por defecto ${defaultDuration} min según tu consultorio). Podés cambiar la duración solo para este turno.`}
      />
      <StandardDurationHint />
      {user?.role === "owner" && (
        <p className="text-xs text-muted-foreground -mt-2 mb-4">
          Para cambiar la duración o el valor de sesión de <strong>todos</strong> los turnos nuevos,
          usá la configuración en{" "}
          <Link to="/agenda" className="text-primary hover:underline">
            Agenda
          </Link>
          .
        </p>
      )}
      <Card>
        <CardHeader><CardTitle className="text-base">Datos del turno</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>Paciente</Label>
              <Input
                placeholder="Buscar por nombre o DNI..."
                value={patientQ}
                onChange={(e) => setPatientQ(e.target.value)}
              />
              {patientsData?.data.length ? (
                <Select value={patientId} onValueChange={setPatientId} required>
                  <SelectTrigger><SelectValue placeholder="Seleccionar paciente" /></SelectTrigger>
                  <SelectContent>
                    {patientsData.data.map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.last_name}, {p.first_name} — {p.dni}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {patientQ.trim() ? "No hay pacientes con esa búsqueda." : "Buscá un paciente o cargá uno en Pacientes."}
                </p>
              )}
            </div>
            {professionals.length > 1 && (
              <div className="space-y-2">
                <Label>Profesional</Label>
                <Select
                  value={resolvedProfessionalId}
                  onValueChange={setProfessionalId}
                  required
                >
                  <SelectTrigger><SelectValue placeholder="Seleccionar" /></SelectTrigger>
                  <SelectContent>
                    {professionals.map((m) => (
                      <SelectItem key={m.id} value={m.id}>{m.full_name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <AppointmentScheduleFields
              date={date}
              time={time}
              durationMinutes={durationMinutes}
              onDateChange={setDate}
              onTimeChange={setTime}
              onDurationChange={setDurationMinutes}
              dayAppointments={dayAppointments}
            />

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Modalidad</Label>
                <Select value={modality} onValueChange={(v) => setModality(v as typeof modality)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="presencial">Presencial</SelectItem>
                    <SelectItem value="online">Online</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Tipo</Label>
                <Select value={attentionType} onValueChange={(v) => setAttentionType(v as typeof attentionType)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="private">Particular</SelectItem>
                    <SelectItem value="health_insurance">Obra social</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            {attentionType === "health_insurance" && (
              <div className="space-y-2">
                <Label>Obra social</Label>
                <Select value={insuranceId} onValueChange={setInsuranceId}>
                  <SelectTrigger><SelectValue placeholder="Seleccionar" /></SelectTrigger>
                  <SelectContent>
                    {insurances.map((i) => (
                      <SelectItem key={i.id} value={i.id}>{i.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {insurances.length === 0 && <InsuranceCatalogHint />}
              </div>
            )}
            {attentionType === "private" && (
              <div className="space-y-2">
                <Label>Valor de la sesión ($)</Label>
                <Input
                  type="number"
                  min={0}
                  step={1}
                  className="w-40 max-w-full"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder={
                    defaultSessionAmount
                      ? `Estándar: ${formatMoney(defaultSessionAmount)}`
                      : "Monto en pesos"
                  }
                />
                <p className="text-xs text-muted-foreground">
                  {defaultSessionAmount
                    ? "Trae el valor del consultorio; podés cambiarlo solo para este turno."
                    : "Escribí el monto que cobrás por esta sesión."}
                </p>
              </div>
            )}

            {formError && <FeedbackBanner message={formError} variant="error" />}

            <div className="flex gap-2">
              <Button type="submit" disabled={submitDisabled}>
                {create.isPending ? "Guardando..." : "Guardar turno"}
              </Button>
              <Button type="button" variant="outline" asChild>
                <Link to="/agenda">Cancelar</Link>
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
