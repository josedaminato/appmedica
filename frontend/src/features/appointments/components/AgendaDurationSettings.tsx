import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Clock, DollarSign } from "lucide-react"
import { useAuth } from "@/features/auth/AuthContext"
import {
  getOrganizationSettings,
  updateOrganizationSettings,
  type OrganizationSettings,
} from "@/features/organizations/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { FeedbackBanner } from "@/components/shared/FeedbackBanner"
import { DurationPicker } from "./DurationPicker"
import { ApiError } from "@/lib/api-client"
import { formatMoney } from "@/lib/format"

function parseAmountInput(raw: string): number | null {
  const trimmed = raw.trim()
  if (!trimmed) return null
  const n = Number(trimmed)
  return Number.isFinite(n) && n >= 0 ? n : null
}

function amountFromApi(value: string | number | null | undefined): string {
  if (value == null || value === "") return ""
  return String(Number(value))
}

function saveSuccessMessage(result: OrganizationSettings): string {
  const parts = ["Listo: turnos nuevos y futuros pendientes usan esta configuración."]
  const amounts = result.future_private_amounts_updated ?? 0
  const durations = result.future_durations_updated ?? 0
  if (amounts > 0 && durations > 0) {
    parts.push(
      `Se actualizaron ${amounts} valor${amounts === 1 ? "" : "es"} y ${durations} duración${durations === 1 ? "" : "es"} en la agenda.`,
    )
  } else if (amounts > 0) {
    parts.push(
      `Se actualizó el valor en ${amounts} turno${amounts === 1 ? "" : "s"} futuro${amounts === 1 ? "" : "s"} (particulares).`,
    )
  } else if (durations > 0) {
    parts.push(
      `Se actualizó la duración en ${durations} turno${durations === 1 ? "" : "s"} futuro${durations === 1 ? "" : "s"}.`,
    )
  }
  return parts.join(" ")
}

/** Solo el dueño edita. Duración y valor habitual de sesiones particulares. */
export function AgendaDurationSettings() {
  const { user, loadUser } = useAuth()
  const qc = useQueryClient()
  const [durationMinutes, setDurationMinutes] = useState(30)
  const [sessionAmount, setSessionAmount] = useState("")
  const [savedMessage, setSavedMessage] = useState("")
  const [error, setError] = useState("")

  const { data, isLoading } = useQuery({
    queryKey: ["org-settings"],
    queryFn: getOrganizationSettings,
    enabled: user?.role === "owner",
  })

  useEffect(() => {
    if (data) {
      setDurationMinutes(data.default_appointment_duration_minutes)
      setSessionAmount(amountFromApi(data.default_private_session_amount))
    }
  }, [data])

  const save = useMutation({
    mutationFn: () =>
      updateOrganizationSettings({
        default_appointment_duration_minutes: durationMinutes,
        default_private_session_amount: parseAmountInput(sessionAmount),
      }),
    onSuccess: async (result) => {
      setError("")
      setSavedMessage(saveSuccessMessage(result))
      qc.invalidateQueries({ queryKey: ["org-settings"] })
      qc.invalidateQueries({ queryKey: ["appointments"] })
      await loadUser()
      setTimeout(() => setSavedMessage(""), 6000)
    },
    onError: (err) => {
      setSavedMessage("")
      setError(err instanceof ApiError ? err.message : "No se pudo guardar")
    },
  })

  const storedAmount = amountFromApi(data?.default_private_session_amount)
  const unchanged =
    data != null &&
    data.default_appointment_duration_minutes === durationMinutes &&
    storedAmount === sessionAmount.trim()

  if (user?.role !== "owner") return null

  return (
    <div className="mb-4 rounded-lg border bg-muted/30 p-4 space-y-6">
      <div>
        <h3 className="text-sm font-medium">Configuración del consultorio</h3>
        <p className="text-xs text-muted-foreground mt-1 max-w-2xl">
          Definí <strong>una sola vez</strong> duración y valor de sesión. Si subís el precio por
          inflación, guardá el nuevo monto acá y los <strong>turnos futuros</strong>{" "}
          pendientes que tenían el valor anterior se actualizan solos. Los que tengan un monto
          distinto (caso especial) no se tocan.
        </p>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Cargando…</p>
      ) : (
        <>
          <div className="space-y-3">
            <div className="flex items-start gap-2">
              <Clock className="h-5 w-5 text-primary shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-medium">Duración de cada sesión</h4>
                <p className="text-xs text-muted-foreground mt-1">
                  Por defecto 30 min. Si pasás a 45 min, los turnos futuros con la duración vieja
                  también se ajustan al guardar.
                </p>
              </div>
            </div>
            <DurationPicker
              value={durationMinutes}
              onChange={setDurationMinutes}
              label="Duración estándar"
              hideEndPreview
            />
          </div>

          <div className="space-y-3 border-t pt-4">
            <div className="flex items-start gap-2">
              <DollarSign className="h-5 w-5 text-primary shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-medium">Valor de sesión particular</h4>
                <p className="text-xs text-muted-foreground mt-1">
                  Escribí el monto en pesos que cobrás por sesión <strong>particular</strong> (el
                  que vos uses, sin límites prefijados). Si lo dejás vacío, el valor lo cargás en
                  cada turno.
                </p>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="org-session-amount">Valor de sesión ($)</Label>
              <div className="flex flex-wrap items-center gap-2">
                <Input
                  id="org-session-amount"
                  type="number"
                  min={0}
                  step={1}
                  className="w-40 max-w-full"
                  placeholder="Ej. 35000"
                  value={sessionAmount}
                  onChange={(e) => setSessionAmount(e.target.value)}
                />
                <span className="text-xs text-muted-foreground">pesos argentinos</span>
                {sessionAmount.trim() && (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => setSessionAmount("")}
                  >
                    Borrar valor
                  </Button>
                )}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 border-t pt-4">
            <Button
              type="button"
              size="sm"
              disabled={save.isPending || unchanged}
              onClick={() => save.mutate()}
            >
              {save.isPending ? "Guardando…" : "Guardar configuración"}
            </Button>
            {unchanged && data && (
              <span className="text-xs text-muted-foreground">
                Actual: {data.default_appointment_duration_minutes} min
                {data.default_private_session_amount != null
                  ? ` · ${formatMoney(data.default_private_session_amount)} en particulares`
                  : " · valor particular: lo cargás por turno"}
              </span>
            )}
          </div>
          {savedMessage && <FeedbackBanner message={savedMessage} variant="success" />}
          {error && <FeedbackBanner message={error} variant="error" />}
        </>
      )}
    </div>
  )
}

/** Aviso para profesional/staff: solo lectura. */
export function StandardDurationHint() {
  const { user } = useAuth()
  const mins = user?.organization.default_appointment_duration_minutes ?? 30
  const amount = user?.organization.default_private_session_amount

  if (user?.role === "owner") return null

  return (
    <p className="text-xs text-muted-foreground rounded-md bg-muted/50 px-3 py-2 mb-4">
      Estándar del consultorio: <strong>{mins} minutos</strong> por sesión
      {amount != null && amount !== "" ? (
        <>
          {" "}
          · particular <strong>{formatMoney(amount)}</strong>
        </>
      ) : null}
      . Podés cambiar duración y monto solo para este turno más abajo.
    </p>
  )
}
