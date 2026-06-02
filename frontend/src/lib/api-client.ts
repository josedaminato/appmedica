import { TOKEN_KEY } from "@/lib/constants"

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1"

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

function messageForStatus(status: number, fallback: string): string {
  if (status === 401) {
    return "Tu sesión expiró. Volvé a iniciar sesión e intentá de nuevo."
  }
  if (status === 403) {
    return "No tenés permiso para esta acción."
  }
  if (status === 413) {
    return "El archivo es demasiado grande para el servidor."
  }
  return fallback
}

async function parseError(response: Response): Promise<ApiError> {
  try {
    const body = await response.json()
    const err = body?.error
    const message = err?.message ?? messageForStatus(response.status, "Error en la solicitud")
    return new ApiError(response.status, err?.code ?? "ERROR", message)
  } catch {
    return new ApiError(
      response.status,
      "ERROR",
      messageForStatus(response.status, response.statusText),
    )
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set("Content-Type", "application/json")

  if (!options.skipAuth) {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) headers.set("Authorization", `Bearer ${token}`)
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const err = await parseError(response)
    if (err.status === 401 && !options.skipAuth) {
      localStorage.removeItem(TOKEN_KEY)
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login"
      }
    }
    throw err
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export async function apiUpload<T>(
  path: string,
  formData: FormData,
): Promise<T> {
  const headers = new Headers()
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) headers.set("Authorization", `Bearer ${token}`)

  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers,
    body: formData,
  })

  if (!response.ok) {
    const err = await parseError(response)
    if (err.status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login"
      }
    }
    throw err
  }

  return response.json() as Promise<T>
}
