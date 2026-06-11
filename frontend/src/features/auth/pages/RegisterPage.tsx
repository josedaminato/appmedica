import { useState } from "react"
import { Link, Navigate, useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { UrgentHelpSection } from "@/components/shared/UrgentHelpSection"
import { BrandLogo } from "@/features/marketing/components/BrandLogo"
import { ApiError } from "@/lib/api-client"
import { useAuth } from "@/features/auth/AuthContext"
import { APP_DASHBOARD_PATH, APP_TAGLINE } from "@/lib/constants"

export function RegisterPage() {
  const { register, isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    organization_name: "",
    full_name: "",
    email: "",
    password: "",
  })
  const [acceptedTerms, setAcceptedTerms] = useState(false)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  if (!isLoading && isAuthenticated) {
    return <Navigate to={APP_DASHBOARD_PATH} replace />
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!acceptedTerms) {
      setError("Tenés que aceptar los términos y la política de privacidad.")
      return
    }
    setError("")
    setLoading(true)
    try {
      await register(form)
      navigate("/inicio")
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al registrarse")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-muted/30 p-4">
      <BrandLogo className="h-11" />
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Crear consultorio</CardTitle>
          <CardDescription>{APP_TAGLINE}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {(["organization_name", "full_name", "email", "password"] as const).map((field) => (
              <div key={field} className="space-y-2">
                <Label htmlFor={field}>
                  {field === "organization_name" && "Nombre del consultorio"}
                  {field === "full_name" && "Tu nombre"}
                  {field === "email" && "Email"}
                  {field === "password" && "Contraseña (mín. 8)"}
                </Label>
                <Input
                  id={field}
                  type={field === "password" ? "password" : field === "email" ? "email" : "text"}
                  value={form[field]}
                  onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                  required
                  minLength={field === "password" ? 8 : undefined}
                />
              </div>
            ))}
            <label className="flex items-start gap-2 text-sm text-muted-foreground cursor-pointer">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 shrink-0 rounded border-input accent-primary"
                checked={acceptedTerms}
                onChange={(e) => setAcceptedTerms(e.target.checked)}
                required
              />
              <span>
                Acepto los{" "}
                <Link to="/terminos" className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
                  términos de uso
                </Link>{" "}
                y la{" "}
                <Link to="/privacidad" className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
                  política de privacidad
                </Link>
                . Entiendo que AppMedica es gestión administrativa, no historia clínica.
              </span>
            </label>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading || !acceptedTerms}>
              {loading ? "Creando..." : "Crear cuenta"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            ¿Ya tenés cuenta? <Link to="/login" className="text-primary hover:underline">Ingresar</Link>
            {" · "}
            <Link to="/" className="hover:text-foreground">Volver al inicio</Link>
          </p>
        </CardContent>
      </Card>
      <UrgentHelpSection className="w-full max-w-md" />
    </div>
  )
}
