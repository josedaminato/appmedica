import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { UserDetail, CreateUserPayload, UpdateUserPayload } from "../api"
import type { UserRole } from "@/types/api"

type Mode = "create" | "edit"

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  mode: Mode
  member?: UserDetail | null
  currentUserId?: string
  onSubmit: (data: CreateUserPayload | UpdateUserPayload) => Promise<void>
  loading?: boolean
}

export function UserFormDialog({
  open,
  onOpenChange,
  mode,
  member,
  currentUserId,
  onSubmit,
  loading,
}: Props) {
  const [fullName, setFullName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [role, setRole] = useState<Exclude<UserRole, "owner">>("professional")
  const [isActive, setIsActive] = useState(true)

  const isSelf = member?.id === currentUserId
  const isOwnerMember = member?.role === "owner"

  useEffect(() => {
    if (!open) return
    if (mode === "edit" && member) {
      setFullName(member.full_name)
      setEmail(member.email)
      setPassword("")
      setRole(member.role === "owner" ? "professional" : member.role)
      setIsActive(member.is_active)
    } else {
      setFullName("")
      setEmail("")
      setPassword("")
      setRole("professional")
      setIsActive(true)
    }
  }, [open, mode, member])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (mode === "create") {
      await onSubmit({
        full_name: fullName,
        email,
        password,
        role,
      })
      return
    }
    const payload: UpdateUserPayload = {
      full_name: fullName,
      is_active: isActive,
    }
    if (!isOwnerMember && !isSelf) {
      payload.role = role
    }
    await onSubmit(payload)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{mode === "create" ? "Agregar miembro" : "Editar miembro"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label>Nombre completo</Label>
            <Input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
          </div>
          {mode === "create" ? (
            <>
              <div className="space-y-2">
                <Label>Email</Label>
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Contraseña temporal</Label>
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  minLength={8}
                  required
                />
                <p className="text-xs text-muted-foreground">
                  Compartila con la persona para su primer acceso.
                </p>
              </div>
            </>
          ) : (
            <div className="space-y-2">
              <Label>Email</Label>
              <Input type="email" value={email} disabled />
            </div>
          )}
          {(!isOwnerMember || mode === "create") && (
            <div className="space-y-2">
              <Label>Rol</Label>
              <Select
                value={role}
                onValueChange={(v) => setRole(v as typeof role)}
                disabled={mode === "edit" && (isSelf || isOwnerMember)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="professional">Profesional</SelectItem>
                  <SelectItem value="staff">Administración</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
          {mode === "edit" && !isSelf && (
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <p className="text-sm font-medium">Activo</p>
                <p className="text-xs text-muted-foreground">
                  Los usuarios inactivos no pueden iniciar sesión.
                </p>
              </div>
              <Button
                type="button"
                variant={isActive ? "secondary" : "outline"}
                size="sm"
                onClick={() => setIsActive((v) => !v)}
                disabled={isOwnerMember}
              >
                {isActive ? "Activo" : "Inactivo"}
              </Button>
            </div>
          )}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Guardando..." : mode === "create" ? "Agregar" : "Guardar"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
