import { useState } from "react"
import { Link, Navigate, useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { UrgentHelpSection } from "@/components/shared/UrgentHelpSection"
import { BrandLogo } from "@/features/marketing/components/BrandLogo"
import { APP_DASHBOARD_PATH, APP_NAME } from "@/lib/constants"
import { ApiError } from "@/lib/api-client"
import { useAuth } from "@/features/auth/AuthContext"

export function LoginPage() {
  const { login, isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
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
      await login(email, password)
      navigate(APP_DASHBOARD_PATH)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al iniciar sesión")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-muted/30 p-4">
      <BrandLogo className="h-11" />
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-2xl">{APP_NAME}</CardTitle>
          <CardDescription>Ingresá a tu consultorio</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Contraseña</Label>
              <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Ingresando..." : "Ingresar"}
            </Button>
          </form>
          <div className="mt-4 flex flex-col gap-2 text-center text-sm text-muted-foreground">
            <Link to="/forgot-password" className="hover:text-foreground">¿Olvidaste tu contraseña?</Link>
            <Link to="/register" className="hover:text-foreground">Crear cuenta</Link>
            <Link to="/" className="hover:text-foreground">Volver al inicio</Link>
          </div>
        </CardContent>
      </Card>
      <UrgentHelpSection className="w-full max-w-md" />
    </div>
  )
}
