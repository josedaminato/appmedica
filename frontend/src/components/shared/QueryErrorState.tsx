import { Button } from "@/components/ui/button"
import { ApiError, getErrorMessage } from "@/lib/api-client"

type Props = {
  title?: string
  description?: string
  error?: unknown
  onRetry?: () => void
}

export function QueryErrorState({
  title = "No pudimos cargar los datos",
  description,
  error,
  onRetry,
}: Props) {
  const message =
    description ??
    (error instanceof ApiError && error.status === 404
      ? "El recurso no existe o fue eliminado."
      : getErrorMessage(error, "Revisá tu conexión e intentá de nuevo."))

  return (
    <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-6 py-10 text-center">
      <h3 className="text-lg font-medium text-foreground">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{message}</p>
      {onRetry && (
        <Button type="button" variant="outline" className="mt-4" onClick={onRetry}>
          Reintentar
        </Button>
      )}
    </div>
  )
}
