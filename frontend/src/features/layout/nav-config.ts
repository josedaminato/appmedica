import type { UserRole } from "@/types/api"
import {
  Calendar,
  CreditCard,
  FileBarChart,
  LayoutDashboard,
  Shield,
  UserCog,
  Users,
  type LucideIcon,
} from "lucide-react"

export type NavItem = {
  to: string
  label: string
  icon: LucideIcon
  enabled: boolean
  ownerOnly?: boolean
}

export const navItems: NavItem[] = [
  { to: "/inicio", label: "Inicio", icon: LayoutDashboard, enabled: true },
  { to: "/patients", label: "Pacientes", icon: Users, enabled: true },
  { to: "/agenda", label: "Agenda", icon: Calendar, enabled: true },
  { to: "/insurances", label: "Obras sociales", icon: Shield, enabled: true },
  { to: "/payments", label: "Pagos y deudas", icon: CreditCard, enabled: true },
  { to: "/reports", label: "Reportes", icon: FileBarChart, enabled: true },
  { to: "/team", label: "Equipo", icon: UserCog, enabled: true, ownerOnly: true },
]

export function visibleNavItems(role: UserRole | undefined) {
  return navItems.filter((item) => !item.ownerOnly || role === "owner")
}
