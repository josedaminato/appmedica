import { NavLink } from "react-router-dom"
import { Menu } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"
import { APP_NAME } from "@/lib/constants"
import { useAuth } from "@/features/auth/AuthContext"
import { UrgentHelpSection } from "@/components/shared/UrgentHelpSection"
import { visibleNavItems } from "./nav-config"

export function MobileNav() {
  const { user } = useAuth()
  const items = visibleNavItems(user?.role)

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden" aria-label="Abrir menú">
          <Menu className="h-5 w-5" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xs p-0 gap-0">
        <DialogHeader className="border-b px-4 py-3 text-left">
          <DialogTitle className="text-primary font-semibold tracking-tight">
            {APP_NAME}
          </DialogTitle>
        </DialogHeader>
        <nav className="flex flex-col p-2">
          {items.map(({ to, label, icon: Icon, enabled }) =>
            enabled ? (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                  )
                }
              >
                <Icon className="h-4 w-4" />
                {label}
              </NavLink>
            ) : (
              <span
                key={to}
                className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground opacity-50 cursor-not-allowed"
              >
                <Icon className="h-4 w-4" />
                {label}
                <span className="ml-auto text-[10px] uppercase">Pronto</span>
              </span>
            ),
          )}
        </nav>
        <div className="border-t p-3">
          <UrgentHelpSection compact />
        </div>
      </DialogContent>
    </Dialog>
  )
}
