import { Navigate, Outlet } from "react-router-dom"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { usePlatformAuth } from "./PlatformAuthContext"

export function PlatformProtectedRoute() {
  const { isAuthenticated, isLoading } = usePlatformAuth()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center p-8">
        <LoadingSkeleton rows={3} />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/interno" replace />
  }

  return <Outlet />
}
