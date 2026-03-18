"use client"

import type { ReactNode } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { ProtectedRoute } from "@/components/protected-route"
import { useAuth } from "@/lib/auth-context"
import { Button } from "@/components/ui/button"
import { Users, BarChart3, Settings, LogOut, Menu } from "lucide-react"
import { useState } from "react"

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const { logout } = useAuth()
  const router = useRouter()
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const handleLogout = () => {
    logout()
    router.push("/")
  }

  const menuItems = [
    { href: "/dashboard", icon: Users, label: "Matches" },
    { href: "/dashboard/profile", icon: Settings, label: "Profile" },
    { href: "/dashboard/analytics", icon: BarChart3, label: "Analytics" },
  ]

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-background">
        {/* Sidebar */}
        <aside
          className={`${
            sidebarOpen ? "w-64" : "w-0"
          } border-r border-border bg-card transition-all duration-300 overflow-hidden flex flex-col`}
        >
          <div className="p-6 border-b border-border">
            <div className="text-2xl font-bold text-primary">Matcher</div>
            <p className="text-xs text-muted-foreground mt-1">AI Matching Platform</p>
          </div>

          <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
            {menuItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-background text-foreground transition"
              >
                <item.icon className="w-5 h-5" />
                <span>{item.label}</span>
              </Link>
            ))}
          </nav>

          <div className="border-t border-border p-4 space-y-2">
            <Button onClick={handleLogout} variant="outline" className="w-full justify-start gap-2 bg-transparent">
              <LogOut className="w-4 h-4" />
              Logout
            </Button>
          </div>
        </aside>

        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Top Bar */}
          <header className="border-b border-border bg-background px-6 py-4 flex items-center">
            <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2 hover:bg-card rounded-lg transition">
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex-1" />
            <div className="text-sm text-muted-foreground">Dashboard</div>
          </header>

          {/* Content Area */}
          <main className="flex-1 overflow-auto">{children}</main>
        </div>
      </div>
    </ProtectedRoute>
  )
}
