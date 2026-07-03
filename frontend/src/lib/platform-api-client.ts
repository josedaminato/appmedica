import { PLATFORM_TOKEN_KEY, PLATFORM_USERNAME_KEY } from "@/lib/constants"
import { ApiError } from "@/lib/api-client"

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1"

type RequestOptions = RequestInit & {
  skipAuth?: boolean
}

function authHeaders(skipAuth?: boolean): Headers {
  const headers = new Headers()
  if (!skipAuth) {
    const token = localStorage.getItem(PLATFORM_TOKEN_KEY)
    if (token) headers.set("Authorization", `Bearer ${token}`)
  }
  return headers
}

function handleUnauthorized(skipAuth?: boolean): void {
  if (skipAuth || typeof window === "undefined") return
  localStorage.removeItem(PLATFORM_TOKEN_KEY)
  localStorage.removeItem(PLATFORM_USERNAME_KEY)
  if (!window.location.pathname.startsWith("/interno")) return
  if (window.location.pathname !== "/interno") {
    window.location.href = "/interno"
  }
}

async function handleResponse<T>(response: Response, skipAuth?: boolean): Promise<T> {
  if (!response.ok) {
    let err: ApiError
    try {
      const body = await response.json()
      const message = body?.error?.message ?? "Error en la solicitud"
      err = new ApiError(response.status, body?.error?.code ?? "ERROR", message)
    } catch {
      err = new ApiError(response.status, "ERROR", response.statusText || "Error en la solicitud")
    }
    if (err.status === 401) handleUnauthorized(skipAuth)
    throw err
  }
  return response.json() as Promise<T>
}

export async function platformApiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = authHeaders(options.skipAuth)
  headers.set("Content-Type", "application/json")
  const response = await fetch(`${API_URL}${path}`, { ...options, headers })
  return handleResponse<T>(response, options.skipAuth)
}
