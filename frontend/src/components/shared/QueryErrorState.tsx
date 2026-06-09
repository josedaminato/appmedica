import { Button } from "@/components/ui/button"

type Props = {
  title?: string
  description?: string
  onRetry?: () => void
}

export function QueryErrorState({
  title = "No pudimos cargar los datos",
  description = "Revisá tu conexión e intentá de nuevo.",
  onRetry,
}: Props) {
  return (
    <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-6 py-10 text-center">
      <h3 className="text-lg font-medium text-foreground">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
      {onRetry && (
        <Button type="button" variant="outline" className="mt-4" onClick={onRetry}>
          Reintentar
        </Button>
      )}
    </div>
  )
}
