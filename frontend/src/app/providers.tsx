import { QueryClientProvider } from "@tanstack/react-query"
import { AuthProvider } from "@/features/auth/AuthContext"
import { PlatformAuthProvider } from "@/features/platform/PlatformAuthContext"
import { queryClient } from "@/lib/query-client"

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <PlatformAuthProvider>{children}</PlatformAuthProvider>
      </AuthProvider>
    </QueryClientProvider>
  )
}
