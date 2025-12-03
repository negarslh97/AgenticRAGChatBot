import React from 'react'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'

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
  const navigate = useNavigate()

  // اگر هنوز در حال لود کردن هستیم، loading spinner نشان بده
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  // اگر کاربر احراز هویت نشده، به صفحه لاگین هدایت کن
  if (!isAuthenticated || !user) {
    navigate(redirectTo, { replace: true })
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
      navigate('/unauthorized', { replace: true })
      return null
    }
  }

  // اگر همه چک‌ها پاس شد، component را رندر کن
  return <>{children}</>
}

export default AuthGuard
