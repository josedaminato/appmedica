import { NavLink } from "react-router-dom"
import { cn } from "@/lib/utils"
import { APP_NAME } from "@/lib/constants"
import { useAuth } from "@/features/auth/AuthContext"
import { UrgentHelpSection } from "@/components/shared/UrgentHelpSection"
import { visibleNavItems } from "./nav-config"

export function Sidebar() {
  const { user } = useAuth()
  const items = visibleNavItems(user?.role)

  return (
    <aside className="hidden w-60 shrink-0 border-r bg-card md:flex md:flex-col">
      <div className="flex h-14 items-center border-b px-4">
        <span className="font-semibold tracking-tight text-primary">{APP_NAME}</span>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {items.map(({ to, label, icon: Icon, enabled }) => (
          <NavLink
            key={to}
            to={enabled ? to : "#"}
            onClick={(e) => !enabled && e.preventDefault()}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                enabled && isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground",
                !enabled && "cursor-not-allowed opacity-50",
                enabled && !isActive && "hover:bg-accent hover:text-accent-foreground",
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
            {!enabled && <span className="ml-auto text-[10px] uppercase">Pronto</span>}
          </NavLink>
        ))}
      </nav>
      <div className="border-t p-3">
        <UrgentHelpSection compact />
      </div>
    </aside>
  )
}
