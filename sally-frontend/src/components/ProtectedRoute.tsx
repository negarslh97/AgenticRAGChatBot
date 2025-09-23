"use client"

import type React from "react"
import type { ReactNode } from "react"
import { Navigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { useState, useEffect } from "react"

interface ProtectedRouteProps {
  children: ReactNode
  requiredRole?: "Customer" | "Admin" | "SuperAdmin"
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requiredRole }) => {
  const { user, userType, loading } = useAuth()
  const [isReady, setIsReady] = useState(false)
  
  console.log("ProtectedRoute render:", {
    loading,
    user: user?.email,
    userType,
    userRole: user?.role,
    requiredRole,
    hasToken: !!localStorage.getItem('token'),
    isReady
  });

  // تأخیر کوچیک برای مطمئن شدن از اینکه همه چیز آماده شده
  useEffect(() => {
    if (!loading && user) {
      console.log("✅ ProtectedRoute: Auth complete, waiting 100ms before rendering...");
      const timer = setTimeout(() => {
        console.log("✅ ProtectedRoute: Ready to render!");
        setIsReady(true)
      }, 100)
      return () => clearTimeout(timer)
    } else if (!loading && !user) {
      console.log("❌ ProtectedRoute: Auth complete but no user");
      setIsReady(false)
    }
  }, [loading, user])

  if (loading || !isReady) {
    console.log("⏳ ProtectedRoute: Waiting for auth or ready state...");
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!user) {
    console.log("❌ ProtectedRoute: No user, redirecting to login");
    return <Navigate to="/login" replace />
  }

  // اگر توکن وجود داره ولی یوزر نال هست، یعنی هنوز احراز هویت کامل نشده
  // در این حالت باید صبر کنیم تا احراز هویت کامل بشه
  const token = localStorage.getItem("token")
  if (token && !user) {
    console.log("⏳ ProtectedRoute: Token exists but user is null, waiting...");
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

    console.log("ProtectedRoute role check:", {
      userType,
      userLevel,
      requiredRole,
      requiredLevel,
      hasAccess: userLevel >= requiredLevel
    })

    if (userLevel < requiredLevel) {
      console.log("❌ ProtectedRoute: Insufficient permissions, redirecting to home")
      return <Navigate to="/" replace />
    }
  }

  return <>{children}</>
}

export default ProtectedRoute
