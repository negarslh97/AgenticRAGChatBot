'use client'

import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import {
  MessageCircle,
  Ticket,
  BookOpen,
  UserCog,
  CheckCircle2,
  BookText,
  Clock,
  User,
  Bot,
  FileText,
  ArrowLeft
} from 'lucide-react'

interface DashboardStats {
  openTickets: number
  resolvedTickets: number
  articlesRead: number
}

interface Activity {
  id: string
  type: 'ticket_update' | 'ticket_response' | 'article_published'
  title: string
  description: string
  timestamp: string
  status?: 'در حال بررسی' | 'پاسخ داده شده' | 'حل شده'
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

  // Mock data for dashboard statistics
  const [stats] = useState<DashboardStats>({
    openTickets: 3,
    resolvedTickets: 12,
    articlesRead: 8
  })

  // Mock data for recent activities
  const [recentActivities] = useState<Activity[]>([
    {
      id: '1',
      type: 'ticket_update',
      title: 'تیکت #12345 به‌روزرسانی شد',
      description: 'وضعیت: در حال بررسی',
      timestamp: '۲ ساعت پیش',
      status: 'در حال بررسی'
    },
    {
      id: '2',
      type: 'ticket_response',
      title: 'پاسخ جدیدی برای تیکت #12342 دریافت کردید',
      description: 'پشتیبان به تیکت شما پاسخ داده است',
      timestamp: '۴ ساعت پیش',
      status: 'پاسخ داده شده'
    },
    {
      id: '3',
      type: 'article_published',
      title: 'مقاله جدیدی منتشر شد',
      description: 'چگونه رمز عبور خود را بازیابی کنیم؟',
      timestamp: '۱ روز پیش'
    },
    {
      id: '4',
      type: 'ticket_update',
      title: 'تیکت #12340 حل شد',
      description: 'تیکت شما با موفقیت حل شده است',
      timestamp: '۲ روز پیش',
      status: 'حل شده'
    },
    {
      id: '5',
      type: 'ticket_response',
      title: 'پاسخ جدیدی برای تیکت #12338 دریافت کردید',
      description: 'پشتیبان به تیکت شما پاسخ داده است',
      timestamp: '۳ روز پیش',
      status: 'پاسخ داده شده'
    },
    {
      id: '6',
      type: 'article_published',
      title: 'مقاله جدیدی منتشر شد',
      description: 'راهنمای استفاده از پایگاه دانش',
      timestamp: '۴ روز پیش'
    }
  ])

  // Navigation cards data
  const navigationCards = [
    {
      title: 'چت با Sally',
      description: 'برای دریافت پاسخ‌های فوری با دستیار هوش مصنوعی ما صحبت کنید.',
      icon: MessageCircle,
      link: '/chat',
      color: 'text-blue-600'
    },
    {
      title: 'تیکت‌های من',
      description: 'تیکت‌های پشتیبانی خود را مشاهده و مدیریت کنید.',
      icon: Ticket,
      link: '/tickets',
      color: 'text-green-600'
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

  const getActivityIcon = (type: Activity['type']) => {
    switch (type) {
      case 'ticket_update':
        return <Ticket className="h-4 w-4" />
      case 'ticket_response':
        return <MessageCircle className="h-4 w-4" />
      case 'article_published':
        return <BookOpen className="h-4 w-4" />
      default:
        return <FileText className="h-4 w-4" />
    }
  }

  const getStatusBadgeVariant = (status?: Activity['status']) => {
    switch (status) {
      case 'در حال بررسی':
        return 'warning'
      case 'پاسخ داده شده':
        return 'success'
      case 'حل شده':
        return 'default'
      default:
        return 'secondary'
    }
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

      {/* Header Section - Transparent with stronger text */}
      <div className="relative bg-transparent">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
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
      </div>

      {/* Main Content */}
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Quick Statistics Section - Glassmorphism effect */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="bg-white/50 backdrop-blur-lg border border-white/30 hover:shadow-xl transition-all duration-300">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600">تیکت‌های باز</p>
                  <p className="text-3xl font-bold text-slate-800 mt-2">{stats.openTickets}</p>
                </div>
                <div className="bg-blue-100 p-3 rounded-full shadow-md">
                  <Ticket className="h-6 w-6 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white/50 backdrop-blur-lg border border-white/30 hover:shadow-xl transition-all duration-300">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600">تیکت‌های حل شده</p>
                  <p className="text-3xl font-bold text-slate-800 mt-2">{stats.resolvedTickets}</p>
                </div>
                <div className="bg-green-100 p-3 rounded-full shadow-md">
                  <CheckCircle2 className="h-6 w-6 text-green-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white/50 backdrop-blur-lg border border-white/30 hover:shadow-xl transition-all duration-300">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600">مقالات خوانده شده</p>
                  <p className="text-3xl font-bold text-slate-800 mt-2">{stats.articlesRead}</p>
                </div>
                <div className="bg-purple-100 p-3 rounded-full shadow-md">
                  <BookOpen className="h-6 w-6 text-purple-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Navigation Grid - Enhanced glassmorphism with hover effects */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {navigationCards.map((card, index) => (
            <Link key={index} to={card.link}>
              <Card className="bg-white/60 backdrop-blur-lg border border-white/40 hover:border-blue-400 hover:shadow-2xl transition-all duration-300 hover:scale-105 cursor-pointer h-full group">
                <CardContent className="p-8 text-center">
                  <div className={`${card.color} mb-6 flex justify-center group-hover:scale-110 transition-transform duration-300`}>
                    <card.icon className="h-12 w-12" />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-800 mb-3 group-hover:text-blue-600 transition-colors duration-300">
                    {card.title}
                  </h3>
                  <p className="text-sm text-slate-600 leading-relaxed">
                    {card.description}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>

        {/* Recent Activity Section - Improved layout and modern badges */}
        <Card className="bg-white/60 backdrop-blur-lg border border-white/40">
          <CardHeader>
            <CardTitle className="text-xl font-bold text-slate-800">فعالیت‌های اخیر</CardTitle>
            <div className="text-slate-600 text-sm">
              آخرین فعالیت‌های حساب کاربری شما
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentActivities.map((activity) => (
                <div key={activity.id} className="flex items-center justify-between p-4 hover:bg-white/30 rounded-lg transition-colors group">
                  <div className="flex items-center space-x-4">
                    <div className="flex-shrink-0">
                      <div className="bg-white/50 p-2 rounded-full shadow-sm group-hover:shadow-md transition-shadow duration-300">
                        {getActivityIcon(activity.type)}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <h4 className="text-sm font-semibold text-slate-800">
                        {activity.title}
                      </h4>
                      <p className="text-sm text-slate-600">
                        {activity.description}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    {activity.status && (
                      <Badge variant={getStatusBadgeVariant(activity.status)} className="px-3 py-1">
                        {activity.status}
                      </Badge>
                    )}
                    <span className="text-xs text-slate-500 font-medium">
                      {activity.timestamp}
                    </span>
                  </div>
                </div>
              ))}
            </div>
            
            {recentActivities.length === 0 && (
              <div className="text-center py-8">
                <div className="text-slate-400 text-4xl mb-4">
                  <Clock className="h-16 w-16 mx-auto" />
                </div>
                <p className="text-slate-500">هیچ فعالیتی یافت نشد</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default DashboardPage