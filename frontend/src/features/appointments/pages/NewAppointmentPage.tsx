import { useState } from "react"
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
import { useAuth } from "@/features/auth/AuthContext"
import { listPatients } from "@/features/patients/api"
import { listHealthInsurances } from "@/features/insurances/api"
import { listTeam } from "@/features/users/api"
import * as apptApi from "../api"

export function NewAppointmentPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [patientId, setPatientId] = useState("")
  const [professionalId, setProfessionalId] = useState("")
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [time, setTime] = useState("09:00")
  const [duration, setDuration] = useState("30")
  const [modality, setModality] = useState<"presencial" | "online">("presencial")
  const [attentionType, setAttentionType] = useState<"private" | "health_insurance">("private")
  const [amount, setAmount] = useState("")
  const [insuranceId, setInsuranceId] = useState("")

  const { data: patientsData } = useQuery({
    queryKey: ["patients", "picker"],
    queryFn: () => listPatients({ page_size: 100, is_active: true }),
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

  const create = useMutation({
    mutationFn: apptApi.createAppointment,
    onSuccess: (appt) => {
      const d = appt.start_at.slice(0, 10)
      navigate(`/agenda?date=${d}`)
    },
  })

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const start = new Date(`${date}T${time}:00`)
    const end = new Date(start.getTime() + Number(duration) * 60_000)
    if (end <= start) return
    await create.mutateAsync({
      patient_id: patientId,
      professional_id: resolvedProfessionalId || null,
      start_at: start.toISOString(),
      end_at: end.toISOString(),
      modality,
      attention_type: attentionType,
      expected_amount: amount ? Number(amount) : null,
      health_insurance_id: attentionType === "health_insurance" ? insuranceId || null : null,
    })
  }

  return (
    <div className="max-w-lg">
      <PageHeader title="Nuevo turno" description="Agendá en pocos segundos." />
      <Card>
        <CardHeader><CardTitle className="text-base">Datos del turno</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>Paciente</Label>
              <Select value={patientId} onValueChange={setPatientId} required>
                <SelectTrigger><SelectValue placeholder="Seleccionar" /></SelectTrigger>
                <SelectContent>
                  {patientsData?.data.map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.last_name}, {p.first_name} — {p.dni}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Fecha</Label>
                <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
              </div>
              <div className="space-y-2">
                <Label>Hora</Label>
                <Input type="time" value={time} onChange={(e) => setTime(e.target.value)} required />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Duración (min)</Label>
              <Input type="number" value={duration} onChange={(e) => setDuration(e.target.value)} />
            </div>
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
              </div>
            )}
            <div className="space-y-2">
              <Label>Monto esperado ($)</Label>
              <Input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} />
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={create.isPending}>Guardar</Button>
              <Button type="button" variant="outline" asChild><Link to="/agenda">Cancelar</Link></Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
