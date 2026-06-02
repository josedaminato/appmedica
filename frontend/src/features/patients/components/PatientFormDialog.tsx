import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useQuery } from "@tanstack/react-query"
import { listHealthInsurances } from "@/features/insurances/api"
import type { Patient } from "@/types/api"
import type { PatientPayload } from "../api"

const schema = z.object({
  first_name: z.string().min(1, "Requerido"),
  last_name: z.string().min(1, "Requerido"),
  dni: z.string().min(7, "DNI inválido"),
  phone: z.string().optional(),
  email: z.string().email("Email inválido").optional().or(z.literal("")),
  birth_date: z.string().optional(),
  health_insurance_id: z.string().optional(),
  affiliate_number: z.string().optional(),
  notes: z.string().optional(),
  is_active: z.boolean(),
})

type FormValues = z.infer<typeof schema>

interface PatientFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  patient?: Patient | null
  onSubmit: (data: PatientPayload) => Promise<unknown>
  loading?: boolean
}

export function PatientFormDialog({
  open,
  onOpenChange,
  patient,
  onSubmit,
  loading,
}: PatientFormDialogProps) {
  const { data: insurances = [] } = useQuery({
    queryKey: ["insurances"],
    queryFn: () => listHealthInsurances(),
    enabled: open,
  })

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      first_name: "",
      last_name: "",
      dni: "",
      phone: "",
      email: "",
      birth_date: "",
      affiliate_number: "",
      notes: "",
      is_active: true,
    },
  })

  useEffect(() => {
    if (patient) {
      reset({
        first_name: patient.first_name,
        last_name: patient.last_name,
        dni: patient.dni,
        phone: patient.phone ?? "",
        email: patient.email ?? "",
        birth_date: patient.birth_date ?? "",
        health_insurance_id: patient.health_insurance_id ?? undefined,
        affiliate_number: patient.affiliate_number ?? "",
        notes: patient.notes ?? "",
        is_active: patient.is_active,
      })
    } else {
      reset({
        first_name: "",
        last_name: "",
        dni: "",
        phone: "",
        email: "",
        birth_date: "",
        affiliate_number: "",
        notes: "",
        is_active: true,
      })
    }
  }, [patient, open, reset])

  const isActive = watch("is_active")

  async function onFormSubmit(values: FormValues) {
    await onSubmit({
      first_name: values.first_name,
      last_name: values.last_name,
      dni: values.dni,
      phone: values.phone || null,
      email: values.email || null,
      birth_date: values.birth_date || null,
      health_insurance_id: values.health_insurance_id || null,
      affiliate_number: values.affiliate_number || null,
      notes: values.notes || null,
      is_active: values.is_active,
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{patient ? "Editar paciente" : "Nuevo paciente"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Nombre</Label>
              <Input {...register("first_name")} />
              {errors.first_name && <p className="text-xs text-destructive">{errors.first_name.message}</p>}
            </div>
            <div className="space-y-2">
              <Label>Apellido</Label>
              <Input {...register("last_name")} />
              {errors.last_name && <p className="text-xs text-destructive">{errors.last_name.message}</p>}
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>DNI</Label>
              <Input {...register("dni")} />
              {errors.dni && <p className="text-xs text-destructive">{errors.dni.message}</p>}
            </div>
            <div className="space-y-2">
              <Label>Teléfono</Label>
              <Input {...register("phone")} />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Email</Label>
              <Input type="email" {...register("email")} />
              {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
            </div>
            <div className="space-y-2">
              <Label>Fecha de nacimiento</Label>
              <Input type="date" {...register("birth_date")} />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Obra social</Label>
            <Select
              value={watch("health_insurance_id") || "none"}
              onValueChange={(v) => setValue("health_insurance_id", v === "none" ? undefined : v)}
            >
              <SelectTrigger><SelectValue placeholder="Sin obra social" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Sin obra social</SelectItem>
                {insurances.map((i) => (
                  <SelectItem key={i.id} value={i.id}>{i.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Nº afiliado</Label>
            <Input {...register("affiliate_number")} />
          </div>
          <div className="space-y-2">
            <Label>Estado</Label>
            <Select
              value={isActive ? "active" : "inactive"}
              onValueChange={(v) => setValue("is_active", v === "active")}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Activo</SelectItem>
                <SelectItem value="inactive">Inactivo</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Observaciones</Label>
            <Textarea {...register("notes")} rows={3} />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Guardando..." : "Guardar"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
