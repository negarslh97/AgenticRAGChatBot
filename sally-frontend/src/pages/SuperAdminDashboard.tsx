'use client'

import React, { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import StatCard from '../components/StatCard'
import { superAdminService, DashboardStats } from '../services/superAdminService'
import {
  Users,
  Ticket,
  BookOpen,
  Activity,
  Settings,
  Crown
} from 'lucide-react'

const SuperAdminDashboard: React.FC = () => {
  const { user } = useAuth()
  const [stats, setStats] = useState<DashboardStats>({
    users: { totalAdmins: 0, totalCustomers: 0 },
    tickets: { open: 0, awaitingReply: 0, resolved: 0 },
    knowledgeBase: { published: 0, drafts: 0 }
  })
  const [loading, setLoading] = useState(true)

  // Fetch dashboard stats
  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true)
        const dashboardStats = await superAdminService.getDashboardStats()
        setStats(dashboardStats)
      } catch (error) {
        console.error('Error fetching dashboard stats:', error)
        // Fallback data if API fails
        setStats({
          users: { totalAdmins: 0, totalCustomers: 0 },
          tickets: { open: 0, awaitingReply: 0, resolved: 0 },
          knowledgeBase: { published: 0, drafts: 0 }
        })
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [])

  // Removed handleLogout since logout button is now in navbar

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
          onClick: () => alert('این قابلیت به زودی اضافه خواهد شد')
        },
        {
          label: 'مدیریت مشتریان',
          onClick: () => alert('این قابلیت به زودی اضافه خواهد شد')
        }
      ]
    },
    {
      title: 'مدیریت تیکت‌ها',
      stats: [
        { label: 'تیکت‌های باز', value: stats.tickets.open },
        { label: 'در انتظار پاسخ', value: stats.tickets.awaitingReply },
        { label: 'حل شده', value: stats.tickets.resolved }
      ],
      icon: Ticket,
      iconColor: 'text-green-600',
      actions: [
        {
          label: 'مشاهده همه تیکت‌ها',
          onClick: () => alert('این قابلیت به زودی اضافه خواهد شد')
        },
        {
          label: 'تخصیص تیکت‌ها',
          onClick: () => alert('این قابلیت به زودی اضافه خواهد شد')
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
          onClick: () => alert('این قابلیت به زودی اضافه خواهد شد')
        },
        {
          label: 'ایجاد مقاله جدید',
          onClick: () => alert('این قابلیت به زودی اضافه خواهد شد')
        }
      ]
    },
    {
      title: 'لاگ‌های فعالیت سیستم',
      description: 'نظارت بر تمام اقدامات کاربران و سیستم',
      icon: Activity,
      iconColor: 'text-orange-600',
      actions: [
        {
          label: 'مشاهده لاگ‌های فعالیت',
          onClick: () => alert('این قابلیت به زودی اضافه خواهد شد')
        }
      ]
    },
    {
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
    }
  ]

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
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