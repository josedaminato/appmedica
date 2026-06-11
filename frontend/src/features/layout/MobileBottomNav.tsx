import { NavLink, useLocation } from "react-router-dom"
import { MoreHorizontal } from "lucide-react"
import { cn } from "@/lib/utils"
import { useAuth } from "@/features/auth/AuthContext"
import { visibleNavItems } from "./nav-config"

const PRIMARY_PATHS = ["/inicio", "/agenda", "/patients", "/payments"]

type MobileBottomNavProps = {
  onMoreClick: () => void
}

export function MobileBottomNav({ onMoreClick }: MobileBottomNavProps) {
  const { user } = useAuth()
  const location = useLocation()
  const items = visibleNavItems(user?.role).filter(
    (item) => item.enabled && PRIMARY_PATHS.includes(item.to),
  )

  const moreActive = !PRIMARY_PATHS.some((path) => location.pathname.startsWith(path))

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:hidden pb-[env(safe-area-inset-bottom)]"
      aria-label="Navegación principal"
    >
      <div className="flex h-16 items-stretch justify-around">
        {items.map(({ to, label, icon: Icon }) => {
          const active = location.pathname === to || location.pathname.startsWith(`${to}/`)
          return (
            <NavLink
              key={to}
              to={to}
              className={cn(
                "flex min-w-0 flex-1 flex-col items-center justify-center gap-0.5 px-1 text-[11px] font-medium transition-colors touch-manipulation",
                active ? "text-primary" : "text-muted-foreground",
              )}
            >
              <Icon className={cn("h-5 w-5 shrink-0", active && "stroke-[2.5]")} />
              <span className="truncate max-w-full">{label.split(" ")[0]}</span>
            </NavLink>
          )
        })}
        <button
          type="button"
          onClick={onMoreClick}
          className={cn(
            "flex min-w-0 flex-1 flex-col items-center justify-center gap-0.5 px-1 text-[11px] font-medium transition-colors touch-manipulation",
            moreActive ? "text-primary" : "text-muted-foreground",
          )}
          aria-label="Más opciones"
        >
          <MoreHorizontal className={cn("h-5 w-5 shrink-0", moreActive && "stroke-[2.5]")} />
          <span>Más</span>
        </button>
      </div>
    </nav>
  )
}
