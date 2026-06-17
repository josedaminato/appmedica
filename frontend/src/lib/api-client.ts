import { TOKEN_KEY } from "@/lib/constants"
import { queryClient } from "@/lib/query-client"

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1"

const AUTH_PUBLIC_PATHS = ["/login", "/register", "/forgot-password", "/reset-password"]

export class ApiError extends Error {
  code: string
  status: number

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

type RequestOptions = RequestInit & {
  skipAuth?: boolean
}

function isAuthPublicPath(pathname: string): boolean {
  return AUTH_PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`))
}

function messageForStatus(status: number, fallback: string): string {
  if (status === 401) {
    return "Tu sesión expiró. Volvé a iniciar sesión e intentá de nuevo."
  }
  if (status === 403) {
    return "No tenés permiso para esta acción."
  }
  if (status === 404) {
    return "No encontramos el recurso solicitado."
  }
  if (status === 413) {
    return "El archivo es demasiado grande para el servidor."
  }
  if (status === 429) {
    return "Demasiados intentos. Esperá un momento e intentá de nuevo."
  }
  return fallback
}

function validationHint(details: unknown): string | null {
  if (!Array.isArray(details) || details.length === 0) return null
  const first = details[0] as { loc?: unknown[]; msg?: string }
  const field = Array.isArray(first.loc) ? String(first.loc.at(-1) ?? "") : ""
  const msg = first.msg ?? ""
  if (field && msg) return `${field}: ${msg}`
  return msg || null
}

async function parseError(response: Response): Promise<ApiError> {
  try {
    const body = await response.json()
    const err = body?.error
    let message = err?.message ?? messageForStatus(response.status, "Error en la solicitud")
    const hint = validationHint(err?.details)
    if (hint && err?.code === "VALIDATION_ERROR") {
      message = `${message} (${hint})`
    }
    return new ApiError(response.status, err?.code ?? "ERROR", message)
  } catch {
    return new ApiError(
      response.status,
      "ERROR",
      messageForStatus(response.status, response.statusText || "Error en la solicitud"),
    )
  }
}

function authHeaders(skipAuth?: boolean): Headers {
  const headers = new Headers()
  if (!skipAuth) {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) headers.set("Authorization", `Bearer ${token}`)
  }
  return headers
}

function handleUnauthorized(skipAuth?: boolean): void {
  if (skipAuth || typeof window === "undefined") return
  localStorage.removeItem(TOKEN_KEY)
  queryClient.clear()
  if (!isAuthPublicPath(window.location.pathname)) {
    window.location.href = "/login"
  }
}

async function handleResponse<T>(response: Response, skipAuth?: boolean): Promise<T> {
  if (!response.ok) {
    const err = await parseError(response)
    if (err.status === 401) {
      handleUnauthorized(skipAuth)
    }
    throw err
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export function getErrorMessage(error: unknown, fallback = "Ocurrió un error inesperado"): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error && error.message) return error.message
  return fallback
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const headers = authHeaders(options.skipAuth)
  headers.set("Content-Type", "application/json")

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  })

  return handleResponse<T>(response, options.skipAuth)
}

export async function apiDownload(path: string, filename: string): Promise<void> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: authHeaders(),
  })

  if (!response.ok) {
    const err = await parseError(response)
    if (err.status === 401) {
      handleUnauthorized()
    }
    throw err
  }

  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}
