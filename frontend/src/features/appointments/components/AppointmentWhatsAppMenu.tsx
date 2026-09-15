import { MessageCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  buildAppointmentWhatsAppMessage,
  buildWhatsAppHref,
  type AppointmentWhatsAppKind,
} from "@/lib/whatsapp"
import type { Appointment } from "@/types/api"

const TEMPLATES: { kind: Exclude<AppointmentWhatsAppKind, "availability">; label: string }[] = [
  { kind: "reminder", label: "Recordar turno" },
  { kind: "confirm", label: "Confirmar turno" },
  { kind: "reschedule", label: "Avisar reprogramación" },
  { kind: "cancel", label: "Avisar cancelación" },
]

type Props = {
  appointment: Appointment
  orgName?: string | null
}

export function AppointmentWhatsAppMenu({ appointment, orgName }: Props) {
  const phone = appointment.patient?.phone
  const firstName = appointment.patient?.first_name ?? ""
  const professionalName = appointment.professional?.full_name

  const items = TEMPLATES.map((tpl) => ({
    ...tpl,
    href: buildWhatsAppHref(
      phone,
      buildAppointmentWhatsAppMessage(tpl.kind, {
        patientFirstName: firstName,
        startAtIso: appointment.start_at,
        orgName,
        professionalName,
      }),
    ),
  })).filter((item) => item.href)

  if (items.length === 0) return null

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button size="sm" variant="outline" aria-label="Mensajes de WhatsApp">
          <MessageCircle className="h-3.5 w-3.5" />
          WhatsApp
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        {items.map((item) => (
          <DropdownMenuItem key={item.kind} asChild>
            <a href={item.href!} target="_blank" rel="noopener noreferrer">
              {item.label}
            </a>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
