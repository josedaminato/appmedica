import { apiRequest } from "@/lib/api-client"
import type { AuthResponse, MessageResponse, User } from "@/types/api"

export interface RegisterPayload {
  organization_name: string
  full_name: string
  email: string
  password: string
}

export interface LoginPayload {
  email: string
  password: string
}

export function register(data: RegisterPayload) {
  return apiRequest<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
    skipAuth: true,
  })
}

export function login(data: LoginPayload) {
  return apiRequest<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
    skipAuth: true,
  })
}

export function logout() {
  return apiRequest<MessageResponse>("/auth/logout", { method: "POST" })
}

export function forgotPassword(email: string) {
  return apiRequest<MessageResponse>("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
    skipAuth: true,
  })
}

export function resetPassword(token: string, new_password: string) {
  return apiRequest<{ access_token: string }>("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, new_password }),
    skipAuth: true,
  })
}

export function getMe() {
  return apiRequest<User>("/auth/me")
}
