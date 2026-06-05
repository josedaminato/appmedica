import { useAuth } from "@/features/auth/AuthContext"
import type { UserRole } from "@/types/api"

export function useRoleScope() {
  const { user } = useAuth()
  const role = user?.role as UserRole | undefined

  return {
    user,
    role,
    isOwner: role === "owner",
    isStaff: role === "staff",
    isProfessional: role === "professional",
    /** Profesional solo ve su cartera; owner/staff pueden filtrar. */
    lockedProfessionalId: role === "professional" ? user?.id : undefined,
    canManageTeam: role === "owner",
    canFilterByProfessional: role === "owner" || role === "staff",
  }
}
