import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { BrandLogo } from "@/features/marketing/components/BrandLogo"

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-muted/30 p-4 text-center">
      <BrandLogo className="h-11" />
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">Página no encontrada</h1>
        <p className="max-w-md text-sm text-muted-foreground">
          La dirección que ingresaste no existe. Volvé al inicio o ingresá a tu consultorio.
        </p>
      </div>
      <div className="flex flex-wrap justify-center gap-3">
        <Button asChild variant="outline">
          <Link to="/">Ir al inicio</Link>
        </Button>
        <Button asChild>
          <Link to="/login">Ingresar</Link>
        </Button>
      </div>
    </div>
  )
}
