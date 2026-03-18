"use client"

import { createContext, useContext, useState, useEffect, type ReactNode } from "react"

interface User {
  id: string
  email: string
  name?: string
}

interface AuthContextType {
  user: User | null
  loading: boolean
  isAuthenticated: boolean
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check localStorage for auth token on mount
    const token = localStorage.getItem("auth_token")
    const email = localStorage.getItem("user_email")

    if (token && email) {
      // This will be replaced with actual Supabase/Clerk verification
      setUser({
        id: "temp_id",
        email: email,
        name: email.split("@")[0],
      })
    }
    setLoading(false)
  }, [])

  const logout = () => {
    localStorage.removeItem("auth_token")
    localStorage.removeItem("user_email")
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, isAuthenticated: !!user, logout }}>{children}</AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider")
  }
  return context
}
