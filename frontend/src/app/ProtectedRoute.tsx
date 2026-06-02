import { Navigate, Outlet } from "react-router-dom"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { useAuth } from "@/features/auth/AuthContext"

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center p-8">
        <LoadingSkeleton rows={3} />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
