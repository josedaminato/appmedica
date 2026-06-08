import { useState } from "react"
import { Navigate } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus, UserCog } from "lucide-react"
import { useAuth } from "@/features/auth/AuthContext"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { PageHeader } from "@/components/shared/PageHeader"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { FeedbackBanner } from "@/components/shared/FeedbackBanner"
import { EmptyState } from "@/components/shared/EmptyState"
import { ApiError } from "@/lib/api-client"
import { formatDate } from "@/lib/format"
import * as api from "../api"
import type { CreateUserPayload, UpdateUserPayload, UserDetail } from "../api"
import { UserFormDialog } from "../components/UserFormDialog"

export function TeamPage() {
  const { user } = useAuth()
  const qc = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<UserDetail | null>(null)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")

  if (user && user.role !== "owner") {
    return <Navigate to="/inicio" replace />
  }

  const { data: members = [], isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: api.listUsers,
    enabled: user?.role === "owner",
  })

  const create = useMutation({
    mutationFn: api.createUser,
    onSuccess: () => {
      setDialogOpen(false)
      setSuccess("Miembro agregado")
      setError("")
      qc.invalidateQueries({ queryKey: ["users"] })
      qc.invalidateQueries({ queryKey: ["team"] })
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Error al crear usuario")
    },
  })

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateUserPayload }) =>
      api.updateUser(id, data),
    onSuccess: () => {
      setEditTarget(null)
      setSuccess("Cambios guardados")
      setError("")
      qc.invalidateQueries({ queryKey: ["users"] })
      qc.invalidateQueries({ queryKey: ["team"] })
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Error al actualizar usuario")
    },
  })

  function openCreate() {
    setEditTarget(null)
    setDialogOpen(true)
  }

  function openEdit(member: UserDetail) {
    setEditTarget(member)
    setDialogOpen(true)
  }

  async function handleSubmit(data: CreateUserPayload | UpdateUserPayload) {
    if (editTarget) {
      await update.mutateAsync({ id: editTarget.id, data: data as UpdateUserPayload })
    } else {
      await create.mutateAsync(data as CreateUserPayload)
    }
  }

  return (
    <div>
      <PageHeader
        title="Equipo"
        description="Invitá profesionales y personal administrativo a tu consultorio."
        action={
          <Button size="sm" onClick={openCreate}>
            <Plus className="h-4 w-4 mr-1" />
            Agregar miembro
          </Button>
        }
      />

      {success && <FeedbackBanner variant="success" message={success} />}
      {error && <FeedbackBanner variant="error" message={error} />}

      {isLoading ? (
        <LoadingSkeleton />
      ) : members.length === 0 ? (
        <EmptyState
          title="Sin miembros"
          description="Agregá profesionales o personal de administración."
        />
      ) : (
        <div className="rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50">
              <tr>
                <th className="px-3 py-2.5 text-left font-medium">Nombre</th>
                <th className="px-3 py-2.5 text-left font-medium hidden md:table-cell">Email</th>
                <th className="px-3 py-2.5 text-left font-medium">Rol</th>
                <th className="px-3 py-2.5 text-left font-medium">Estado</th>
                <th className="px-3 py-2.5 text-right font-medium">Acción</th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.id} className="border-b last:border-0 hover:bg-muted/20">
                  <td className="px-3 py-2.5">
                    <p className="font-medium">{m.full_name}</p>
                    <p className="text-xs text-muted-foreground md:hidden">{m.email}</p>
                    <p className="text-xs text-muted-foreground hidden sm:block">
                      Desde {formatDate(m.created_at)}
                    </p>
                  </td>
                  <td className="px-3 py-2.5 hidden md:table-cell text-muted-foreground">
                    {m.email}
                  </td>
                  <td className="px-3 py-2.5">
                    <Badge variant={m.role === "owner" ? "default" : "secondary"}>
                      {api.ROLE_LABELS[m.role]}
                    </Badge>
                  </td>
                  <td className="px-3 py-2.5">
                    <Badge variant={m.is_active ? "success" : "secondary"}>
                      {m.is_active ? "Activo" : "Inactivo"}
                    </Badge>
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    <Button size="sm" variant="ghost" onClick={() => openEdit(m)}>
                      <UserCog className="h-3.5 w-3.5 mr-1" />
                      Editar
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <UserFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        mode={editTarget ? "edit" : "create"}
        member={editTarget}
        currentUserId={user?.id}
        onSubmit={handleSubmit}
        loading={create.isPending || update.isPending}
      />
    </div>
  )
}
