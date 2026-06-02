import { apiRequest } from "@/lib/api-client"
import type { TeamMember, UserRole } from "@/types/api"

export type UserDetail = TeamMember & {
  created_at: string
}

export type CreateUserPayload = {
  full_name: string
  email: string
  password: string
  role: Exclude<UserRole, "owner">
}

export type UpdateUserPayload = {
  full_name?: string
  role?: UserRole
  is_active?: boolean
}

export function listTeam() {
  return apiRequest<TeamMember[]>("/users/team")
}

export function listUsers() {
  return apiRequest<UserDetail[]>("/users")
}

export function createUser(data: CreateUserPayload) {
  return apiRequest<UserDetail>("/users", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export function updateUser(id: string, data: UpdateUserPayload) {
  return apiRequest<UserDetail>(`/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

export const ROLE_LABELS: Record<UserRole, string> = {
  owner: "Administrador",
  professional: "Profesional",
  staff: "Administración",
}
