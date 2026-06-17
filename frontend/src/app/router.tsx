import { lazy, Suspense } from "react"
import { BrowserRouter, Route, Routes } from "react-router-dom"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { AppShell } from "@/features/layout/AppShell"
import { ProtectedRoute } from "./ProtectedRoute"

const LoginPage = lazy(() =>
  import("@/features/auth/pages/LoginPage").then((m) => ({ default: m.LoginPage })),
)
const RegisterPage = lazy(() =>
  import("@/features/auth/pages/RegisterPage").then((m) => ({ default: m.RegisterPage })),
)
const ForgotPasswordPage = lazy(() =>
  import("@/features/auth/pages/ForgotPasswordPage").then((m) => ({ default: m.ForgotPasswordPage })),
)
const ResetPasswordPage = lazy(() =>
  import("@/features/auth/pages/ResetPasswordPage").then((m) => ({ default: m.ResetPasswordPage })),
)
const HomePage = lazy(() =>
  import("@/features/marketing/pages/HomePage").then((m) => ({ default: m.HomePage })),
)
const PrivacyPage = lazy(() =>
  import("@/features/marketing/pages/PrivacyPage").then((m) => ({ default: m.PrivacyPage })),
)
const TermsPage = lazy(() =>
  import("@/features/marketing/pages/TermsPage").then((m) => ({ default: m.TermsPage })),
)
const DashboardPage = lazy(() =>
  import("@/features/dashboard/DashboardPage").then((m) => ({ default: m.DashboardPage })),
)
const AgendaPage = lazy(() =>
  import("@/features/appointments/pages/AgendaPage").then((m) => ({ default: m.AgendaPage })),
)
const NewAppointmentPage = lazy(() =>
  import("@/features/appointments/pages/NewAppointmentPage").then((m) => ({ default: m.NewAppointmentPage })),
)
const PatientsPage = lazy(() =>
  import("@/features/patients/pages/PatientsPage").then((m) => ({ default: m.PatientsPage })),
)
const PatientDetailPage = lazy(() =>
  import("@/features/patients/pages/PatientDetailPage").then((m) => ({ default: m.PatientDetailPage })),
)
const InsurancesPage = lazy(() =>
  import("@/features/insurances/pages/InsurancesPage").then((m) => ({ default: m.InsurancesPage })),
)
const PaymentsPage = lazy(() =>
  import("@/features/payments/pages/PaymentsPage").then((m) => ({ default: m.PaymentsPage })),
)
const ReportsPage = lazy(() =>
  import("@/features/reports/pages/ReportsPage").then((m) => ({ default: m.ReportsPage })),
)
const TeamPage = lazy(() =>
  import("@/features/users/pages/TeamPage").then((m) => ({ default: m.TeamPage })),
)
const NotFoundPage = lazy(() =>
  import("@/features/marketing/pages/NotFoundPage").then((m) => ({ default: m.NotFoundPage })),
)

function PageLoader() {
  return (
    <div className="p-6">
      <LoadingSkeleton rows={5} />
    </div>
  )
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/privacidad" element={<PrivacyPage />} />
          <Route path="/terminos" element={<TermsPage />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route path="inicio" element={<DashboardPage />} />
              <Route path="agenda" element={<AgendaPage />} />
              <Route path="agenda/new" element={<NewAppointmentPage />} />
              <Route path="patients" element={<PatientsPage />} />
              <Route path="patients/:id" element={<PatientDetailPage />} />
              <Route path="insurances" element={<InsurancesPage />} />
              <Route path="payments" element={<PaymentsPage />} />
              <Route path="reports" element={<ReportsPage />} />
              <Route path="team" element={<TeamPage />} />
            </Route>
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
