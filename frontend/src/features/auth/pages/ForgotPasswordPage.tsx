import { useState } from "react"
import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { BrandLogo } from "@/features/marketing/components/BrandLogo"
import { forgotPassword } from "@/features/auth/api"
import { ApiError } from "@/lib/api-client"
import {
  SUPPORT_WHATSAPP_DISPLAY,
  SUPPORT_WHATSAPP_PHONE,
  SUPPORT_WHATSAPP_PREFILL,
} from "@/lib/constants"

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("")
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    setMessage("")
    setLoading(true)
    try {
      const res = await forgotPassword(email)
      setMessage(res.message)
      setSent(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No pudimos enviar las instrucciones. Intentá de nuevo.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-muted/30 p-4">
      <BrandLogo className="h-11" />
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Recuperar contraseña</CardTitle>
          <CardDescription>
            Te enviamos un enlace a tu email para restablecer el acceso a tu consultorio.
          </CardDescription>
        </CardHeader>
        <CardContent>
  {sent ? (
            <div className="space-y-3 text-sm text-muted-foreground" role="status">
              <p>{message}</p>
              <p>
                Revisá la bandeja de entrada y <strong>spam / correo no deseado</strong>. El enlace
                vence en 2 horas.
              </p>
              <p>
                Si no llega en unos minutos, escribinos por WhatsApp{" "}
                <a
                  href={`https://wa.me/${SUPPORT_WHATSAPP_PHONE.replace(/\D/g, "")}?text=${encodeURIComponent(SUPPORT_WHATSAPP_PREFILL)}`}
                  className="text-primary hover:underline"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {SUPPORT_WHATSAPP_DISPLAY}
                </a>
                .
              </p>
              <Button type="button" variant="outline" className="w-full" onClick={() => setSent(false)}>
                Probar con otro email
              </Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email de tu cuenta</Label>
                <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Enviando..." : "Enviar instrucciones"}
              </Button>
            </form>
          )}
          <p className="mt-4 text-center text-sm text-muted-foreground">
            <Link to="/login" className="text-primary hover:underline">
              Volver al login
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
