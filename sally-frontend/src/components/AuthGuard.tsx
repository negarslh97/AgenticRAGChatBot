import React from 'react'
import { useAuth } from '../context/AuthContext'
import { useLocation, useNavigate } from 'react-router-dom'

interface AuthGuardProps {
  children: React.ReactNode
  requiredRole?: 'Customer' | 'Admin' | 'SuperAdmin'
  redirectTo?: string
}

const AuthGuard: React.FC<AuthGuardProps> = ({
  children,
  requiredRole,
  redirectTo = '/login'
}) => {
  const { user, userType, loading, isSuperAdmin, isAdmin, isAuthenticated } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  // Debug logging
  console.log("AuthGuard render:", {
    user: user?.email,
    userType,
    loading,
    isAuthenticated,
    isAdmin,
    isSuperAdmin,
    requiredRole,
    currentPath: location.pathname
  })

  // اگر هنوز در حال لود کردن هستیم، loading spinner نشان بده
  if (loading) {
    console.log("AuthGuard: Loading, showing spinner")
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  // اگر کاربر احراز هویت نشده، به صفحه لاگین هدایت کن
  if (!isAuthenticated || !user) {
    console.log("AuthGuard: User not authenticated, redirecting to login")
    navigate('/login', { replace: true })
    return null
  }

  // چک کردن role اگر مشخص شده باشد
  if (requiredRole) {
    let hasRequiredRole = false

    if (requiredRole === 'SuperAdmin' && isSuperAdmin) {
      hasRequiredRole = true
    } else if (requiredRole === 'Admin' && isAdmin) {
      hasRequiredRole = true
    } else if (requiredRole === 'Customer' && userType === 'Customer') {
      hasRequiredRole = true
    }

    if (!hasRequiredRole) {
      console.log(`AuthGuard: User doesn't have required role ${requiredRole}, redirecting to unauthorized`)
      navigate('/unauthorized', { replace: true })
      return null
    }
  }

  // اگر همه چک‌ها پاس شد، component را رندر کن
  console.log("AuthGuard: All checks passed, rendering children")
  return <>{children}</>
}

export default AuthGuard
