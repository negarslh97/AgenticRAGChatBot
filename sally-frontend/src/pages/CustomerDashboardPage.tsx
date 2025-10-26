'use client'

import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Button } from '../components/ui/button'
import CustomerLayout from '../components/layouts/CustomerLayout'
import DashboardStats from '../components/dashboard/DashboardStats'
import NavigationCards from '../components/dashboard/NavigationCards'
import RecentActivities from '../components/dashboard/RecentActivities'
import {
  MessageCircle,
  CheckCircle2,
  BookText,
  UserCog
} from 'lucide-react'

interface Activity {
  id: string
  type: 'article_published' | 'login' | 'profile_update'
  title: string
  description: string
  timestamp: string
  status?: 'در حال بررسی' | 'پاسخ داده شده' | 'حل شده' | 'موفق' | 'ناموفق'
  priority?: 'low' | 'medium' | 'high'
}

interface UserData {
  id: string
  full_name: string
  email: string
  role: string
  created_at: string
}

const DashboardPage: React.FC = () => {
  const { user } = useAuth()
  const [currentUser, setCurrentUser] = useState<UserData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showMobileSidebar, setShowMobileSidebar] = useState(false)

  // Mobile sidebar toggle handler
  const handleMobileSidebarToggle = () => {
    setShowMobileSidebar(!showMobileSidebar)
  }

  // Fetch user data from API
  useEffect(() => {
    const fetchUserData = async () => {
      try {
        const response = await fetch('/api/users/me', {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
          }
        })

        if (response.ok) {
          const userData = await response.json()
          setCurrentUser(userData)
        } else {
          console.error('Failed to fetch user data')
          // Fallback to context user if API fails
          if (user) {
            setCurrentUser({
              id: user.id || '1',
              full_name: user.full_name || 'کاربر',
              email: user.email || '',
              role: user.role || 'Customer',
              created_at: new Date().toISOString()
            })
          }
        }
      } catch (error) {
        console.error('Error fetching user data:', error)
        // Fallback to context user on network error
        if (user) {
          setCurrentUser({
            id: user.id || '1',
            full_name: user.full_name || 'کاربر',
            email: user.email || '',
            role: user.role || 'Customer',
            created_at: new Date().toISOString()
          })
        }
      } finally {
        setIsLoading(false)
      }
    }

    fetchUserData()
  }, [user])

  // Mock data for dashboard statistics - now using the new StatCard format
  const [statsData] = useState([
    {
      title: 'چت‌های فعال',
      value: 5,
      icon: MessageCircle,
      color: 'bg-blue-100',
      trend: {
        value: 12,
        label: 'نسبت به هفته گذشته',
        type: 'positive' as const
      }
    },
    {
      title: 'مقالات خوانده شده',
      value: 12,
      icon: CheckCircle2,
      color: 'bg-green-100',
      trend: {
        value: 25,
        label: 'نسبت به هفته گذشته',
        type: 'positive' as const
      }
    },
    {
      title: 'سوالات پاسخ داده شده',
      value: 8,
      icon: BookText,
      color: 'bg-purple-100',
      trend: {
        value: 5,
        label: 'نسبت به هفته گذشته',
        type: 'positive' as const
      }
    }
  ])

  // Mock data for recent activities - now using the new Activity format
  const [recentActivitiesData] = useState([
    {
      id: '3',
      type: 'article_published' as const,
      title: 'مقاله جدیدی منتشر شد',
      description: 'چگونه رمز عبور خود را بازیابی کنیم؟',
      timestamp: '۱ روز پیش'
    },
    {
      id: '4',
      type: 'login' as const,
      title: 'ورود به سیستم',
      description: 'با موفقیت وارد سیستم شدید',
      timestamp: '۲ روز پیش'
    }
  ])

  // Navigation cards data - now using the new NavigationCard format
  const navigationCardsData = [
    {
      title: 'چت با Sally',
      description: 'برای دریافت پاسخ‌های فوری با دستیار هوش مصنوعی ما صحبت کنید.',
      icon: MessageCircle,
      link: '/chat',
      color: 'text-blue-600',
      badge: 'جدید'
    },
    {
      title: 'پایگاه دانش',
      description: 'مقالات و راهنماهای ما را برای حل مشکلات جستجو کنید.',
      icon: BookText,
      link: '/knowledge-base',
      color: 'text-purple-600'
    },
    {
      title: 'تنظیمات حساب کاربری',
      description: 'اطلاعات پروفایل و تنظیمات امنیتی خود را ویرایش کنید.',
      icon: UserCog,
      link: '/profile',
      color: 'text-orange-600'
    }
  ]

  // Handle activity click
  const handleActivityClick = (activity: Activity) => {
    console.log('Activity clicked:', activity)
    // Here you can add navigation logic or modal opening
  }

  return (
    <CustomerLayout
      backgroundPattern="aurora"
      showMobileSidebar={showMobileSidebar}
      onMobileSidebarToggle={handleMobileSidebarToggle}
    >
      {/* Header Section */}
      <div className="mb-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-slate-800">
              {isLoading ? (
                'در حال بارگذاری...'
              ) : (
                `داشبورد کاربری - خوش آمدید، ${currentUser?.full_name || 'کاربر'}!`
              )}
            </h1>
            <p className="text-slate-600 mt-1">به پنل مدیریت خود خوش آمدید</p>
          </div>
          <Link to="/chat">
            <Button className="bg-blue-600 hover:bg-blue-700 text-white shadow-lg hover:shadow-xl transition-all duration-300">
              <MessageCircle className="ml-2 h-4 w-4" />
              چت با Sally
            </Button>
          </Link>
        </div>
      </div>

      {/* Dashboard Content */}
      <div className="space-y-8">
        {/* Statistics Section */}
        <DashboardStats
          stats={statsData}
          variant="glassmorphism"
          columns={3}
          showAnimations={true}
        />

        {/* Navigation Cards */}
        <NavigationCards
          cards={navigationCardsData}
          variant="grid"
          columns={4}
          showAnimations={true}
        />

        {/* Recent Activities */}
        <RecentActivities
          activities={recentActivitiesData}
          maxItems={6}
          showIcons={true}
          showStatus={true}
          showPriority={true}
          variant="default"
          onActivityClick={handleActivityClick}
        />
      </div>
      </CustomerLayout>
  )
}

export default DashboardPage