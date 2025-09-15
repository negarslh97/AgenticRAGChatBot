"use client"

import type React from "react"
import { createContext, useContext, useState, useEffect, type ReactNode } from "react"
import { authService, type User, type LoginResponse } from "../services/authService"

interface AuthContextType {
  user: User | null
  login: (email: string, password: string) => Promise<LoginResponse>
  register: (email: string, password: string, fullName: string) => Promise<LoginResponse>
  logout: () => void
  loading: boolean
  isAuthenticated: boolean
  isAdmin: boolean
  isSuperAdmin: boolean
  getDashboardByRole: (role?: string) => string
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem("token")
      if (token) {
        try {
          const userData = await authService.getCurrentUser()
          setUser(userData)
        } catch (error) {
          localStorage.removeItem("token")
        }
      }
      setLoading(false)
    }

    initAuth()
  }, [])

  const login = async (email: string, password: string): Promise<LoginResponse> => {
    const response = await authService.login(email, password)
    localStorage.setItem("token", response.access_token)
    const user = response.user
    if (response.user_type === "customer") {
      user.role = "Customer"
    }
    setUser(user)
    return response
  }

  const register = async (email: string, password: string, fullName: string): Promise<LoginResponse> => {
    const userData = await authService.register(email, password, fullName)
    // After registration, user needs to login
    return await login(email, password)
  }

  const logout = () => {
    localStorage.removeItem("token")
    setUser(null)
    authService.logout()
  }

  const isAuthenticated = !!user
  const isAdmin = user?.role === "Admin" || user?.role === "SuperAdmin"
  const isSuperAdmin = user?.role === "SuperAdmin"

  const getDashboardByRole = (role?: string) => {
    switch (role) {
      case "SuperAdmin":
        return "/super-admin"
      case "Admin":
        return "/admin"
      case "Customer":
        return "/dashboard"
      case "Guest":
        return "/"
      default:
        return "/dashboard"
    }
  }

  const value: AuthContextType = {
    user,
    login,
    register,
    logout,
    loading,
    isAuthenticated,
    isAdmin,
    isSuperAdmin,
    getDashboardByRole,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
