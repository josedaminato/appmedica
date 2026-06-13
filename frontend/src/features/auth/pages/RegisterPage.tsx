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
import { APP_DASHBOARD_PATH, APP_NAME, APP_TAGLINE } from "@/lib/constants"

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

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!acceptedTerms) {
      setError("Tenés que aceptar los términos y la política de privacidad.")
      return
    }
    const fd = new FormData(e.currentTarget)
    const payload = {
      organization_name: String(fd.get("organization_name") ?? form.organization_name).trim(),
      full_name: String(fd.get("full_name") ?? form.full_name).trim(),
      email: String(fd.get("email") ?? form.email).trim(),
      password: String(fd.get("password") ?? form.password),
    }
    setError("")
    setLoading(true)
    try {
      await register(payload)
      navigate("/inicio")
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else if (err instanceof Error && err.message) {
        setError(`No se pudo conectar con el servidor. Revisá tu internet e intentá de nuevo. (${err.message})`)
      } else {
        setError("Error al registrarse. Si el email ya lo usaste, probá ingresar.")
      }
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
                  name={field}
                  type={field === "password" ? "password" : field === "email" ? "email" : "text"}
                  autoComplete={
                    field === "email"
                      ? "email"
                      : field === "password"
                        ? "new-password"
                        : field === "full_name"
                          ? "name"
                          : "organization"
                  }
                  value={form[field]}
                  onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                  required
                  minLength={field === "password" ? 8 : field === "organization_name" || field === "full_name" ? 2 : undefined}
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
                . Entiendo que {APP_NAME} es gestión administrativa, no historia clínica.
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
