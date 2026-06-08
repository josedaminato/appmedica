import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { AppShell } from "@/features/layout/AppShell"
import { LoginPage } from "@/features/auth/pages/LoginPage"
import { RegisterPage } from "@/features/auth/pages/RegisterPage"
import { ForgotPasswordPage } from "@/features/auth/pages/ForgotPasswordPage"
import { ResetPasswordPage } from "@/features/auth/pages/ResetPasswordPage"
import { AgendaPage } from "@/features/appointments/pages/AgendaPage"
import { NewAppointmentPage } from "@/features/appointments/pages/NewAppointmentPage"
import { DashboardPage } from "@/features/dashboard/DashboardPage"
import { InsurancesPage } from "@/features/insurances/pages/InsurancesPage"
import { PaymentsPage } from "@/features/payments/pages/PaymentsPage"
import { PatientsPage } from "@/features/patients/pages/PatientsPage"
import { PatientDetailPage } from "@/features/patients/pages/PatientDetailPage"
import { ReportsPage } from "@/features/reports/pages/ReportsPage"
import { TeamPage } from "@/features/users/pages/TeamPage"
import { HomePage } from "@/features/marketing/pages/HomePage"
import { ProtectedRoute } from "./ProtectedRoute"

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />

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

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
