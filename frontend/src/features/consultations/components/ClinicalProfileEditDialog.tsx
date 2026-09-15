import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import type { PatientClinicalProfile } from "@/types/api"
import type { PatientClinicalUpdatePayload } from "../api"

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  profile: PatientClinicalProfile | null
  onSubmit: (data: PatientClinicalUpdatePayload) => Promise<void>
  loading?: boolean
}

type FormValues = {
  medical_history: string
  allergies: string
  current_medications: string
  clinical_notes: string
}

export function ClinicalProfileEditDialog({
  open,
  onOpenChange,
  profile,
  onSubmit,
  loading,
}: Props) {
  const { register, handleSubmit, reset } = useForm<FormValues>({
    defaultValues: {
      medical_history: "",
      allergies: "",
      current_medications: "",
      clinical_notes: "",
    },
  })

  useEffect(() => {
    if (profile && open) {
      reset({
        medical_history: profile.medical_history ?? "",
        allergies: profile.allergies ?? "",
        current_medications: profile.current_medications ?? "",
        clinical_notes: profile.clinical_notes ?? "",
      })
    }
  }, [profile, open, reset])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Editar información clínica</DialogTitle>
        </DialogHeader>
        <form
          onSubmit={handleSubmit(async (values) => {
            await onSubmit({
              medical_history: values.medical_history || null,
              allergies: values.allergies || null,
              current_medications: values.current_medications || null,
              clinical_notes: values.clinical_notes || null,
            })
            onOpenChange(false)
          })}
          className="space-y-4"
        >
          <ClinicalField label="Antecedentes" id="medical_history" register={register("medical_history")} />
          <ClinicalField label="Alergias" id="allergies" register={register("allergies")} />
          <ClinicalField label="Medicación habitual" id="current_medications" register={register("current_medications")} />
          <ClinicalField label="Observaciones clínicas" id="clinical_notes" register={register("clinical_notes")} />
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Guardando..." : "Guardar"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function ClinicalField({
  label,
  id,
  register,
}: {
  label: string
  id: string
  register: ReturnType<ReturnType<typeof useForm<FormValues>>["register"]>
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Textarea id={id} rows={2} {...register} />
    </div>
  )
}
