"use client"

import type React from "react"
import { createContext, useContext, useState, useEffect, type ReactNode } from "react"
import { authService, type User } from "../services/authService"

interface AuthContextType {
  user: User | null
  userType: "Admin" | "SuperAdmin"| "Customer" | null
  login: (email: string, password: string) => Promise<{ user: User }>
  register: (email: string, password: string, fullName: string) => Promise<{ user: User }>
  logout: () => void
  loading: boolean
  isAuthenticated: boolean
  isAdmin: boolean
  isSuperAdmin: boolean
  getDashboardByRole: (role: string) => string
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
  const [userType, setUserType] = useState<"Admin" | "SuperAdmin" | "Customer" | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem("token")

      if (token) {
        try {
          // اول authentication status را چک کنیم
          const authStatus = await authService.getAuthStatus()

          if (authStatus.auth_required && !authStatus.authenticated) {
            // اگر سرور می‌گوید authentication لازم است و authenticated نیستیم
            localStorage.removeItem("token")
            window.location.href = authStatus.redirect_to || "/login"
            return
          }

          if (authStatus.authenticated) {
            // اگر authenticated هستیم، user data را بگیریم
            const responseData = await authService.getCurrentUser()

            // تبدیل ساختار داده بک‌اند به ساختار مورد انتظار فرانت‌اند
            let userData: User | null = null;

            if (responseData && typeof responseData === 'object') {
              // بررسی اینکه آیا بک‌اند داده رو در فیلد user قرار داده یا نه
              const responseAny = responseData as any;

              if (responseAny.user && typeof responseAny.user === 'object') {
                // حالت جدید: بک‌اند داده رو در فیلد user قرار داده
                userData = responseAny.user as User;

                // اگر role در داده user نبود، از user_type استفاده کنیم
                if (!userData.role && responseAny.user_type) {
                  userData.role = responseAny.user_type === 'admin' ? 'Admin' : 'Customer';
                }
              } else if (responseAny.email) {
                // حالت قدیمی: داده مستقیم در response هست
                userData = responseData as User;
              }
            }

            if (userData && userData.email) {
              setUser(userData)
              // تنظیم userType بر اساس داده‌های دریافتی
              const responseAny = responseData as any
              const userTypeValue = responseAny.user_type || userData.role || null
              setUserType(userTypeValue)
            } else {
              localStorage.removeItem("token")
            }
          }
        } catch (error) {
          localStorage.removeItem("token")
        }
      }

      setLoading(false)
    }

    initAuth()
  }, [])

  const login = async (email: string, password: string) => {
    const response = await authService.login(email, password)
    localStorage.setItem("token", response.access_token)
    setUser(response.user)
    setUserType(response.user_type)
    console.log("AuthContext login: Setting userType to:", response.user_type)
    return { user: response.user }
  }

  const register = async (email: string, password: string, fullName: string) => {
    await authService.register(email, password, fullName)
    // After registration, user needs to login
    const loginResponse = await login(email, password)
    return { user: loginResponse.user }
  }

  const logout = () => {
    localStorage.removeItem("token")
    setUser(null)
    setUserType(null)
    authService.logout()
  }

  const isAuthenticated = !!user
  const isAdmin = userType === "Admin" || userType === "SuperAdmin"
  const isSuperAdmin = userType === "SuperAdmin"

  // Debug logging
  console.log("AuthContext computed values:", {
    user: user?.email,
    userType,
    isAuthenticated,
    isAdmin,
    isSuperAdmin,
    hasUser: !!user,
    userTypeType: typeof userType
  })

  const getDashboardByRole = (role: string): string => {
    switch (role) {
      case "SuperAdmin":
        return "/super-admin"
      case "Admin":
        return "/admin"
      default:
        return "/dashboard"
    }
  }

  const value: AuthContextType = {
    user,
    userType,
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
