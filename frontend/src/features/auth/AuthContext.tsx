import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react"
import { TOKEN_KEY } from "@/lib/constants"
import type { User } from "@/types/api"
import * as authApi from "./api"

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (data: authApi.RegisterPayload) => Promise<void>
  logout: () => Promise<void>
  setToken: (token: string) => void
  loadUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const loadUser = useCallback(async () => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      setUser(null)
      setIsLoading(false)
      return
    }
    try {
      const me = await authApi.getMe()
      setUser(me)
    } catch {
      localStorage.removeItem(TOKEN_KEY)
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadUser()
  }, [loadUser])

  const setToken = useCallback((token: string) => {
    localStorage.setItem(TOKEN_KEY, token)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login({ email, password })
    setToken(res.access_token)
    setUser(res.user)
  }, [setToken])

  const register = useCallback(async (data: authApi.RegisterPayload) => {
    const res = await authApi.register(data)
    setToken(res.access_token)
    setUser(res.user)
  }, [setToken])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } finally {
      localStorage.removeItem(TOKEN_KEY)
      setUser(null)
    }
  }, [])

  const value = useMemo(
    () => ({
      user,
      isLoading,
      isAuthenticated: !!user,
      login,
      register,
      logout,
      setToken,
      loadUser,
    }),
    [user, isLoading, login, register, logout, setToken, loadUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider")
  return ctx
}
