"use client"

import type React from "react"
import type { ReactNode } from "react"
import { Navigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { useState, useEffect } from "react"
import { authService } from "../services/authService"

interface ProtectedRouteProps {
  children: ReactNode
  requiredRole?: "Customer" | "Admin" | "SuperAdmin"
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requiredRole }) => {
  const { user, userType, loading } = useAuth()
  const [isReady, setIsReady] = useState(false)
  const [serverAuthChecked, setServerAuthChecked] = useState(false)

  // چک کردن authentication status از سرور
  useEffect(() => {
    const checkServerAuth = async () => {
      try {
        // اگر در AuthContext loading هستیم، منتظر بمانیم
        if (loading) return

        // چک کردن authentication status از سرور
        const authStatus = await authService.getAuthStatus()
        setServerAuthChecked(true)

        // اگر سرور می‌گوید authentication لازم است، منتظر AuthContext بمانیم
        if (!authStatus.authenticated && authStatus.auth_required) {
          // AuthContext باید این را handle کند
          return
        }

        // اگر authentication موفق بوده، آماده نمایش component هستیم
        if (authStatus.authenticated || !authStatus.auth_required) {
          setIsReady(true)
        }
      } catch (error) {
        // در صورت خطا، منتظر AuthContext بمانیم
        setServerAuthChecked(true)
      }
    }

    checkServerAuth()
  }, [loading])

  // تأخیر کوچیک برای مطمئن شدن از اینکه همه چیز آماده شده
  useEffect(() => {
    if (!loading && user && serverAuthChecked) {
      const timer = setTimeout(() => {
        setIsReady(true)
      }, 100)
      return () => clearTimeout(timer)
    } else if (!loading && !user && serverAuthChecked) {
      setIsReady(false)
    }
  }, [loading, user, serverAuthChecked])

  if (loading || !isReady) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  // اگر توکن وجود داره ولی یوزر نال هست، یعنی هنوز احراز هویت کامل نشده
  // در این حالت باید صبر کنیم تا احراز هویت کامل بشه
  const token = localStorage.getItem("token")
  if (token && !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (requiredRole) {
    // استفاده از userType به جای user.role برای تعیین سطح دسترسی
    const roleHierarchy = {
      Customer: 1,
      Admin: 2,
      SuperAdmin: 3,
    }

    let userLevel = 0
    if (userType === "SuperAdmin") {
      userLevel = 3
    } else if (userType === "Admin") {
      userLevel = 2
    } else if (userType === "Customer") {
      userLevel = 1
    }

    const requiredLevel = roleHierarchy[requiredRole]

    if (userLevel < requiredLevel) {
      return <Navigate to="/" replace />
    }
  }

  return <>{children}</>
}

export default ProtectedRoute
