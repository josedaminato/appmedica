import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Calendar, Copy, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ApiError } from "@/lib/api-client"
import { APP_NAME } from "@/lib/constants"
import { getCalendarFeed, regenerateCalendarFeed } from "../api-calendar"

interface CalendarSyncDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CalendarSyncDialog({ open, onOpenChange }: CalendarSyncDialogProps) {
  const qc = useQueryClient()
  const [copied, setCopied] = useState<"feed" | "webcal" | null>(null)
  const [error, setError] = useState("")

  const { data, isLoading } = useQuery({
    queryKey: ["calendar-feed"],
    queryFn: getCalendarFeed,
    enabled: open,
  })

  const regenerate = useMutation({
    mutationFn: regenerateCalendarFeed,
    onSuccess: () => {
      setError("")
      qc.invalidateQueries({ queryKey: ["calendar-feed"] })
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "No se pudo regenerar el enlace")
    },
  })

  async function copyText(text: string, kind: "feed" | "webcal") {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(kind)
      setTimeout(() => setCopied(null), 2000)
    } catch {
      setError("No se pudo copiar. Seleccioná el texto manualmente.")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Sincronizar con calendario
          </DialogTitle>
          <p className="text-sm text-muted-foreground">
            Suscribite una vez en Google Calendar, Outlook o Apple. Los turnos se actualizan solos
            (cada pocas horas). Solo lectura: los cambios se hacen en {APP_NAME}.
          </p>
        </DialogHeader>

        {isLoading && <p className="text-sm text-muted-foreground">Generando enlace…</p>}

        {data && (
          <div className="space-y-4 text-sm">
            <p className="rounded-md bg-muted px-3 py-2 text-muted-foreground">
              Alcance: <span className="font-medium text-foreground">{data.scope_label}</span>
            </p>

            <div className="space-y-2">
              <Label>Enlace de suscripción (recomendado)</Label>
              <div className="flex gap-2">
                <Input readOnly value={data.feed_url} className="font-mono text-xs" />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={() => copyText(data.feed_url, "feed")}
                  title="Copiar"
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
              {copied === "feed" && (
                <p className="text-xs text-primary">Copiado al portapapeles</p>
              )}
            </div>

            <div className="space-y-2">
              <Label>Enlace webcal (Apple / algunos clientes)</Label>
              <div className="flex gap-2">
                <Input readOnly value={data.webcal_url} className="font-mono text-xs" />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={() => copyText(data.webcal_url, "webcal")}
                  title="Copiar"
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
              {copied === "webcal" && (
                <p className="text-xs text-primary">Copiado al portapapeles</p>
              )}
            </div>

            <div className="rounded-md border p-3 space-y-2 text-muted-foreground">
              <p className="font-medium text-foreground">Google Calendar</p>
              <ol className="list-decimal list-inside space-y-1">
                <li>Configuración → Añadir calendario → Desde URL</li>
                <li>Pegá el enlace de suscripción y guardá</li>
              </ol>
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <Button
              type="button"
              variant="outline"
              className="w-full"
              disabled={regenerate.isPending}
              onClick={() => regenerate.mutate()}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${regenerate.isPending ? "animate-spin" : ""}`} />
              Regenerar enlace (invalida el anterior)
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
