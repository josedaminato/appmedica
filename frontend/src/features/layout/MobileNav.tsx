import { NavLink } from "react-router-dom"
import { Menu } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"
import { APP_NAME } from "@/lib/constants"
import { useAuth } from "@/features/auth/AuthContext"
import { UrgentHelpSection } from "@/components/shared/UrgentHelpSection"
import { visibleNavItems } from "./nav-config"

type MobileNavProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  showTrigger?: boolean
}

export function MobileNav({ open, onOpenChange, showTrigger = true }: MobileNavProps) {
  const { user } = useAuth()
  const items = visibleNavItems(user?.role)

  function close() {
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {showTrigger && (
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          aria-label="Abrir menú"
          onClick={() => onOpenChange(true)}
        >
          <Menu className="h-5 w-5" />
        </Button>
      )}
      <DialogContent className="sm:max-w-xs p-0 gap-0 max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader className="border-b px-4 py-4 text-left shrink-0">
          <DialogTitle className="text-primary font-semibold tracking-tight">
            {APP_NAME}
          </DialogTitle>
        </DialogHeader>
        <nav className="flex flex-col p-2 overflow-y-auto flex-1">
          {items.map(({ to, label, icon: Icon, enabled }) =>
            enabled ? (
              <NavLink
                key={to}
                to={to}
                onClick={close}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-lg px-4 py-3.5 text-sm font-medium transition-colors touch-manipulation min-h-11",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                  )
                }
              >
                <Icon className="h-5 w-5 shrink-0" />
                {label}
              </NavLink>
            ) : (
              <span
                key={to}
                className="flex items-center gap-3 rounded-lg px-4 py-3.5 text-sm font-medium text-muted-foreground opacity-50 cursor-not-allowed min-h-11"
              >
                <Icon className="h-5 w-5 shrink-0" />
                {label}
                <span className="ml-auto text-[10px] uppercase">Pronto</span>
              </span>
            ),
          )}
        </nav>
        <div className="border-t p-4 shrink-0">
          <UrgentHelpSection compact />
        </div>
      </DialogContent>
    </Dialog>
  )
}
