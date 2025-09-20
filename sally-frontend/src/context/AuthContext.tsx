"use client"

import type React from "react"
import { createContext, useContext, useState, useEffect, type ReactNode } from "react"
import { authService, type User } from "../services/authService"

interface AuthContextType {
  user: User | null
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
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    console.log("AuthContext: Starting auth initialization...");
    
    const initAuth = async () => {
      const token = localStorage.getItem("token")
      console.log("AuthContext: Token found:", !!token);
      
      if (token) {
        try {
          console.log("AuthContext: Fetching current user...");
          const responseData = await authService.getCurrentUser()
          console.log("AuthContext: Raw response data:", responseData);
          
          // تبدیل ساختار داده بک‌اند به ساختار مورد انتظار فرانت‌اند
          let userData: User | null = null;
          
          if (responseData && typeof responseData === 'object') {
            // بررسی اینکه آیا بک‌اند داده رو در فیلد user قرار داده یا نه
            const responseAny = responseData as any;
            
            if (responseAny.user && typeof responseAny.user === 'object') {
              // حالت جدید: بک‌اند داده رو در فیلد user قرار داده
              console.log("✅ AuthContext: Found user data in response.user field");
              userData = responseAny.user as User;
              
              // اگر role در داده user نبود، از user_type استفاده کنیم
              if (!userData.role && responseAny.user_type) {
                userData.role = responseAny.user_type === 'admin' ? 'Admin' : 'Customer';
              }
            } else if (responseAny.email) {
              // حالت قدیمی: داده مستقیم در response هست
              console.log("✅ AuthContext: Found user data directly in response");
              userData = responseData as User;
            }
          }
          
          console.log("AuthContext: Processed user data:", userData);
          console.log("AuthContext: User email:", userData?.email);
          console.log("AuthContext: User role:", userData?.role);
          
          if (userData && userData.email) {
            console.log("✅ AuthContext: User data is valid, setting user");
            setUser(userData)
          } else {
            console.log("❌ AuthContext: Invalid user data received");
            localStorage.removeItem("token")
          }
        } catch (error) {
          console.log("❌ AuthContext: Error fetching user, removing token", error);
          localStorage.removeItem("token")
        }
      } else {
        console.log("AuthContext: No token found");
      }
      
      console.log("AuthContext: Setting loading to false");
      setLoading(false)
    }

    initAuth()
  }, [])

  const login = async (email: string, password: string) => {
    const response = await authService.login(email, password)
    localStorage.setItem("token", response.access_token)
    setUser(response.user)
    return { user: response.user }
  }

  const register = async (email: string, password: string, fullName: string) => {
    const userData = await authService.register(email, password, fullName)
    // After registration, user needs to login
    const loginResponse = await login(email, password)
    return { user: loginResponse.user }
  }

  const logout = () => {
    localStorage.removeItem("token")
    setUser(null)
    authService.logout()
  }

  const isAuthenticated = !!user
  const isAdmin = user?.role === "Admin" || user?.role === "SuperAdmin"
  const isSuperAdmin = user?.role === "SuperAdmin"

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
