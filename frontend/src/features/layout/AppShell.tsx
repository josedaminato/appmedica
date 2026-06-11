import { useState } from "react"
import { Outlet } from "react-router-dom"
import { Sidebar } from "./Sidebar"
import { TopBar } from "./TopBar"
import { MobileNav } from "./MobileNav"
import { MobileBottomNav } from "./MobileBottomNav"

export function AppShell() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <TopBar onMenuClick={() => setMobileMenuOpen(true)} />
        <MobileNav open={mobileMenuOpen} onOpenChange={setMobileMenuOpen} showTrigger={false} />
        <main className="flex-1 overflow-auto p-4 pb-24 md:p-6 md:pb-6">
          <Outlet />
        </main>
        <MobileBottomNav onMoreClick={() => setMobileMenuOpen(true)} />
      </div>
    </div>
  )
}
