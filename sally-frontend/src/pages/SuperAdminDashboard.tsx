'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import StatCard from '../components/StatCard'
import {
  Users,
  BookOpen,
  Settings,
  Crown,
  Database,
  MessageSquare
} from 'lucide-react'

interface DashboardStats {
  users: {
    totalAdmins: number
    totalCustomers: number
  }
  // tickets: {
  //   open: number
  //   awaitingReply: number
  //   resolved: number
  // }
  knowledgeBase: {
    published: number
    drafts: number
  }
  activityLogs: {
    total: number
  }
  chat: {
    conversations: number
    messages: number
  }
  weaviateCollections?: {
    small: {
      name: string
      count: number
      model: string
    }
    large: {
      name: string
      count: number
      model: string
    }
    currentModel: string
  }
}

const SuperAdminDashboard: React.FC = () => {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [stats, setStats] = useState<DashboardStats>({
    users: { totalAdmins: 0, totalCustomers: 0 },
    knowledgeBase: { published: 0, drafts: 0 },
    activityLogs: { total: 0 },
    chat: { conversations: 0, messages: 0 },
    weaviateCollections: {
      small: { name: 'MarkdownNode_Small', count: 0, model: 'text-embedding-3-small' },
      large: { name: 'MarkdownNode_Large', count: 0, model: 'text-embedding-3-large' },
      currentModel: 'text-embedding-3-small'
    }
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch dashboard stats function
  const fetchStats = useCallback(async (): Promise<void> => {
    try {
      setLoading(true)
      setError(null)

      // Check if user is authenticated and is SuperAdmin
      if (!user) {
        throw new Error('User not authenticated. Please log in.')
      }

      if (user.role !== 'SuperAdmin') {
        throw new Error('Access denied. SuperAdmin role required.')
      }

      // Get token from localStorage
      const token = localStorage.getItem('token')
      console.log('Token from localStorage:', token ? 'Present' : 'Missing')
      console.log('Current user:', user)

      if (!token) {
        throw new Error('No authentication token found. Please log in again.')
      }

      const response = await fetch('/api/admin/superadmin/stats', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      })

      console.log('API Response status:', response.status)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('API Error response:', errorText)
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`)
      }

      const data = await response.json()
      console.log('API Response data:', data)
      setStats(data)

    } catch (error) {
      console.error('Error fetching dashboard stats:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      setError(`خطا در بارگذاری آمار داشبورد: ${errorMessage}`)
      // Fallback mock data
      setStats({
        users: { totalAdmins: 0, totalCustomers: 0 },
        knowledgeBase: { published: 0, drafts: 0 },
        activityLogs: { total: 0 },
        chat: { conversations: 0, messages: 0 },
        weaviateCollections: {
          small: { name: 'MarkdownNode_Small', count: 0, model: 'text-embedding-3-small' },
          large: { name: 'MarkdownNode_Large', count: 0, model: 'text-embedding-3-large' },
          currentModel: 'text-embedding-3-small'
        }
      })
    } finally {
      setLoading(false)
    }
  }, [user])

  // Fetch dashboard stats on mount and user change
  useEffect(() => {
    if (user) {
      fetchStats()
    }
  }, [user, fetchStats])

  // Real-time updates - poll every 60 seconds for dashboard stats
  useEffect(() => {
    if (!user) return

    const interval = setInterval(() => {
      fetchStats()
    }, 60000) // 60 seconds

    return () => clearInterval(interval)
  }, [user, fetchStats])

  // Removed handleLogout since logout button is now in navbar

  // 🔧 Feature Flags - برای مخفی کردن موقت برخی قابلیت‌ها
  const FEATURE_FLAGS = {
    SHOW_ACTIVITY_LOGS: false, // مخفی کردن لاگ فعالیت‌ها
    SHOW_SETTINGS: false // مخفی کردن تنظیمات
  }

  const managementCards = [
    {
      title: 'مدیریت کاربران',
      stats: [
        { label: 'کل ادمین‌ها', value: stats.users.totalAdmins },
        { label: 'کل مشتریان', value: stats.users.totalCustomers }
      ],
      icon: Users,
      iconColor: 'text-blue-600',
      actions: [
        {
          label: 'مدیریت ادمین‌ها',
          onClick: () => navigate('/super-admin/admin/users')
        },
        {
          label: 'مدیریت مشتریان',
          onClick: () => navigate('/super-admin/customer/users')
        }
      ]
    },
    {
      title: 'مدیریت پایگاه دانش',
      stats: [
        { label: 'مقالات منتشر شده', value: stats.knowledgeBase.published },
        { label: 'پیش‌نویس‌ها', value: stats.knowledgeBase.drafts }
      ],
      icon: BookOpen,
      iconColor: 'text-purple-600',
      actions: [
        {
          label: 'مدیریت مقالات',
          onClick: () => navigate('/super-admin/knowledge-base')
        },
        {
          label: 'ایجاد مقاله جدید',
          onClick: () => navigate('/super-admin/knowledge-base/add')
        }
      ]
    },
    // 🔧 فعالیت چت - به صورت موقت مخفی شده
    ...(FEATURE_FLAGS.SHOW_ACTIVITY_LOGS ? [{
      title: 'فعالیت چت',
      stats: [
        { label: 'کل مکالمات', value: stats.chat.conversations },
        { label: 'کل پیام‌ها', value: stats.chat.messages }
      ],
      description: 'آمار گفتگوهای مشتریان و ادمین‌ها',
      icon: MessageSquare,
      iconColor: 'text-cyan-600',
      actions: [
        {
          label: 'مشاهده لاگ‌ها',
          onClick: () => navigate('/super-admin/logs')
        }
      ]
    }] : []),
    {
      title: 'Weaviate Collections',
      stats: [
        { label: 'Small Collection', value: stats.weaviateCollections?.small.count || 0 },
        { label: 'Large Collection', value: stats.weaviateCollections?.large.count || 0 },
        {
          label: 'Current Model',
          value: (
            <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-mono bg-blue-50 text-blue-700 border border-blue-200">
              {stats.weaviateCollections?.currentModel || 'Unknown'}
            </span>
          )
        }
      ],
      description: 'آمار collections Weaviate بر اساس مدل embedding',
      icon: Database,
      iconColor: 'text-indigo-600',
      actions: [
        {
          label: 'مشاهده جزئیات',
          onClick: () => alert(`مدل فعلی: ${stats.weaviateCollections?.currentModel}\nSmall: ${stats.weaviateCollections?.small.count} گره\nLarge: ${stats.weaviateCollections?.large.count} گره`)
        }
      ]
    },
    // 🔧 تنظیمات سیستم - به صورت موقت مخفی شده
    ...(FEATURE_FLAGS.SHOW_SETTINGS ? [{
      title: 'تنظیمات سیستم',
      description: 'پیکربندی پارامترهای اصلی برنامه و یکپارچه‌سازی‌ها',
      icon: Settings,
      iconColor: 'text-gray-600',
      actions: [
        {
          label: 'مدیریت تنظیمات سیستم',
          onClick: () => alert('این قابلیت به زودی اضافه خواهد شد')
        }
      ]
    }] : [])
  ]

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="text-red-600 text-lg mb-4">{error}</div>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            تلاش دوباره
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="relative min-h-screen bg-slate-50 overflow-hidden">
      {/* Aurora Background Effects */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-blue-200 rounded-full mix-blend-multiply filter blur-xl opacity-50 animate-blob"></div>
      <div className="absolute top-0 left-96 w-96 h-96 bg-purple-200 rounded-full mix-blend-multiply filter blur-xl opacity-50 animate-blob animation-delay-2000"></div>
      <div className="absolute bottom-0 right-1/2 w-96 h-96 bg-pink-200 rounded-full mix-blend-multiply filter blur-xl opacity-50 animate-blob animation-delay-4000"></div>

      {/* Custom CSS for animations */}
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes blob {
          0% {
            transform: translate(0px, 0px) scale(1);
          }
          33% {
            transform: translate(30px, -50px) scale(1.1);
          }
          66% {
            transform: translate(-20px, 20px) scale(0.9);
          }
          100% {
            transform: translate(0px, 0px) scale(1);
          }
        }
        .animate-blob {
          animation: blob 7s infinite;
        }
        .animation-delay-2000 {
          animation-delay: 2s;
        }
        .animation-delay-4000 {
          animation-delay: 4s;
        }
      `}} />

      {/* Header Section */}
      <div className="relative bg-transparent">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-slate-800 flex items-center gap-2">
                <Crown className="h-8 w-8 text-purple-600" />
                داشبورد ادمین ارشد
              </h1>
              <p className="text-slate-600 mt-1">به پنل مدیریت ارشد سیستم خوش آمدید</p>
            </div>
            {/* <div className="text-right">
              <p className="text-sm text-slate-600">خوش آمدید</p>
              <p className="font-semibold text-slate-800">{user?.full_name}</p>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                ادمین ارشد
              </span>
            </div> */}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {managementCards.map((card, index) => (
            <StatCard
              key={index}
              title={card.title}
              stats={card.stats}
              description={card.description}
              icon={card.icon}
              iconColor={card.iconColor}
              actions={card.actions}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

export default SuperAdminDashboard