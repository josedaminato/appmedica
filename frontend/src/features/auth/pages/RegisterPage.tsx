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
import { APP_DASHBOARD_PATH } from "@/lib/constants"

export function RegisterPage() {
  const { register, isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    organization_name: "",
    full_name: "",
    email: "",
    password: "",
  })
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  if (!isLoading && isAuthenticated) {
    return <Navigate to={APP_DASHBOARD_PATH} replace />
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
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
          <CardDescription>Empezá a organizar tu práctica en minutos</CardDescription>
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
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Creando..." : "Crear cuenta"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            ¿Ya tenés cuenta? <Link to="/login" className="text-primary hover:underline">Ingresar</Link>
            {" · "}
            <Link to="/" className="hover:text-foreground">Volver al inicio</Link>
            {" · "}
            <Link to="/privacidad" className="hover:text-foreground">Privacidad</Link>
          </p>
        </CardContent>
      </Card>
      <UrgentHelpSection className="w-full max-w-md" />
    </div>
  )
}
