"use client"

import type { ReactNode } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { BarChart3, Users, Settings, LogOut, Menu, Shield } from "lucide-react"

export default function AdminLayout({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const router = useRouter()

  const handleLogout = () => {
    localStorage.removeItem("auth_token")
    localStorage.removeItem("user_email")
    router.push("/")
  }

  const menuItems = [
    { href: "/admin", icon: BarChart3, label: "Dashboard" },
    { href: "/admin/users", icon: Users, label: "Users" },
    { href: "/admin/analytics", icon: BarChart3, label: "Analytics" },
    { href: "/admin/settings", icon: Settings, label: "Settings" },
  ]

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? "w-64" : "w-0"
        } border-r border-border bg-card transition-all duration-300 overflow-hidden flex flex-col`}
      >
        <div className="p-6 border-b border-border">
          <div className="flex items-center gap-2 text-2xl font-bold text-primary">
            <Shield className="w-6 h-6" />
            Admin
          </div>
          <p className="text-xs text-muted-foreground mt-1">Control Panel</p>
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
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded-full" />
            <span className="text-sm text-muted-foreground">System Online</span>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  )
}
