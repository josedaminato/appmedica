import { Navigate } from "react-router-dom"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { useAuth } from "@/features/auth/AuthContext"
import { LandingPage } from "./LandingPage"

/** Pública en `/`: landing para visitantes, panel para usuarios logueados. */
export function HomePage() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center p-8">
        <LoadingSkeleton rows={3} />
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/inicio" replace />
  }

  return <LandingPage />
}
