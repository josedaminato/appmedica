import { useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { TOKEN_KEY } from "@/lib/constants"
import { resetPassword } from "@/features/auth/api"

export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = params.get("token") ?? ""
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!token) {
      setError("Token inválido")
      return
    }
    setLoading(true)
    try {
      const res = await resetPassword(token, password)
      localStorage.setItem(TOKEN_KEY, res.access_token)
      navigate("/")
    } catch {
      setError("No se pudo restablecer la contraseña")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Nueva contraseña</CardTitle>
          <CardDescription>Ingresá tu nueva contraseña</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="password">Contraseña</Label>
              <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Guardando..." : "Guardar contraseña"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm">
            <Link to="/login" className="text-primary hover:underline">Volver al login</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
