import { LifeBuoy, Mail, MessageCircle } from "lucide-react"
import {
  SUPPORT_EMAIL,
  SUPPORT_WHATSAPP_DISPLAY,
  SUPPORT_WHATSAPP_PHONE,
  SUPPORT_WHATSAPP_PREFILL,
} from "@/lib/constants"
import { buildWhatsAppUrl } from "@/lib/whatsapp"
import { cn } from "@/lib/utils"

const whatsappUrl = buildWhatsAppUrl(SUPPORT_WHATSAPP_PHONE, SUPPORT_WHATSAPP_PREFILL)
const mailtoUrl = `mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent("Ayuda AppMedica")}`

type UrgentHelpSectionProps = {
  className?: string
  compact?: boolean
}

export function UrgentHelpSection({ className, compact = false }: UrgentHelpSectionProps) {
  return (
    <section
      className={cn(
        "rounded-lg border border-primary/20 bg-primary/5",
        compact ? "p-3 space-y-2" : "p-4 space-y-3",
        className,
      )}
      aria-label="Ayuda urgente"
    >
      <div className="flex items-center gap-2">
        <LifeBuoy className="h-4 w-4 text-primary shrink-0" />
        <h2 className={cn("font-medium text-foreground", compact ? "text-xs" : "text-sm")}>
          Ayuda urgente
        </h2>
      </div>
      <p className={cn("text-muted-foreground", compact ? "text-[11px] leading-snug" : "text-xs")}>
        Problemas para entrar, turnos o pagos: escribinos directo.
      </p>
      <ul className={cn("space-y-1.5", compact ? "text-xs" : "text-sm")}>
        <li>
          <a
            href={whatsappUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-foreground hover:text-primary transition-colors"
          >
            <MessageCircle className="h-4 w-4 text-green-600 shrink-0" />
            <span>
              WhatsApp{" "}
              <span className="font-medium tabular-nums">{SUPPORT_WHATSAPP_DISPLAY}</span>
            </span>
          </a>
        </li>
        <li>
          <a
            href={mailtoUrl}
            className="inline-flex items-center gap-2 text-foreground hover:text-primary transition-colors break-all"
          >
            <Mail className="h-4 w-4 text-primary shrink-0" />
            <span className="font-medium">{SUPPORT_EMAIL}</span>
          </a>
        </li>
      </ul>
    </section>
  )
}
