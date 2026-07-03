import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react"
import { PLATFORM_TOKEN_KEY, PLATFORM_USERNAME_KEY } from "@/lib/constants"
import * as platformApi from "./api"

interface PlatformAuthContextValue {
  username: string | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const PlatformAuthContext = createContext<PlatformAuthContextValue | null>(null)

export function PlatformAuthProvider({ children }: { children: React.ReactNode }) {
  const [username, setUsername] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem(PLATFORM_TOKEN_KEY)
    if (!token) {
      setIsLoading(false)
      return
    }
    platformApi
      .getPlatformDashboard()
      .then(() => setUsername(localStorage.getItem(PLATFORM_USERNAME_KEY)))
      .catch(() => {
        localStorage.removeItem(PLATFORM_TOKEN_KEY)
        localStorage.removeItem(PLATFORM_USERNAME_KEY)
        setUsername(null)
      })
      .finally(() => setIsLoading(false))
  }, [])

  const login = useCallback(async (user: string, password: string) => {
    const res = await platformApi.platformLogin(user, password)
    localStorage.setItem(PLATFORM_TOKEN_KEY, res.access_token)
    localStorage.setItem(PLATFORM_USERNAME_KEY, res.username)
    setUsername(res.username)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(PLATFORM_TOKEN_KEY)
    localStorage.removeItem(PLATFORM_USERNAME_KEY)
    setUsername(null)
  }, [])

  const value = useMemo(
    () => ({
      username,
      isLoading,
      isAuthenticated: !!username,
      login,
      logout,
    }),
    [username, isLoading, login, logout],
  )

  return <PlatformAuthContext.Provider value={value}>{children}</PlatformAuthContext.Provider>
}

export function usePlatformAuth() {
  const ctx = useContext(PlatformAuthContext)
  if (!ctx) throw new Error("usePlatformAuth debe usarse dentro de PlatformAuthProvider")
  return ctx
}
