'use client'

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { useAuth } from '../context/AuthContext'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table'
import {
  MessageSquare,
  Users,
  Activity,
  Search,
  Crown,
  Calendar,
  Clock,
  BarChart3,
  PieChart
} from 'lucide-react'

interface ConversationStats {
  totalConversations: number
  totalMessages: number
  averageMessagesPerConversation: number
  activeConversations: number
  completedConversations: number
  conversationsToday: number
  conversationsThisWeek: number
  conversationsThisMonth: number
  topActiveHours: Array<{ hour: number; count: number }>
  userParticipationStats: Array<{ userType: string; count: number; percentage: number }>
}

interface UserActivity {
  id: string
  name: string
  email: string
  userType: 'Customer' | 'Admin'
  totalConversations: number
  totalMessages: number
  lastActivity: string
  isActive: boolean
  averageMessagesPerConversation: number
}

interface RecentConversation {
  id: string
  customerName: string
  customerEmail: string
  adminName?: string
  startTime: string
  endTime?: string
  messageCount: number
  status: 'active' | 'completed'
  duration?: string
}

const SuperAdminLogsPage: React.FC = () => {
  const { user, isSuperAdmin } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [conversationStats, setConversationStats] = useState<ConversationStats | null>(null)
  const [userActivities, setUserActivities] = useState<UserActivity[]>([])
  const [recentConversations, setRecentConversations] = useState<RecentConversation[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [filterUserType, setFilterUserType] = useState<'all' | 'Customer' | 'Admin'>('all')


  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Get token from localStorage
      const token = localStorage.getItem('token')
      if (!token) {
        throw new Error('No authentication token found. Please log in again.')
      }
      
      const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
      
      // Fetch all data in parallel
      const [conversationStatsResponse, userActivitiesResponse, recentConversationsResponse] = await Promise.all([
        fetch('/api/admin/logs/conversation-stats', { headers }),
        fetch('/api/admin/logs/user-activities', { headers }),
        fetch('/api/admin/logs/recent-conversations', { headers })
      ])
      
      // Check if all responses are ok
      if (!conversationStatsResponse.ok || !userActivitiesResponse.ok || !recentConversationsResponse.ok) {
        throw new Error('Failed to fetch data from API')
      }
      
      // Parse responses
      const conversationStatsData = await conversationStatsResponse.json()
      const userActivitiesData = await userActivitiesResponse.json()
      const recentConversationsData = await recentConversationsResponse.json()
      
      setConversationStats(conversationStatsData)
      setUserActivities(userActivitiesData)
      setRecentConversations(recentConversationsData)
      
    } catch (error) {
      console.error('Error fetching logs data:', error)
      const errorMessage = error instanceof Error ? error.message : 'خطا در بارگذاری اطلاعات لاگ‌ها'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isSuperAdmin && user) {
      fetchData()
    }
  }, [isSuperAdmin, user, fetchData])
  
  // Add auto-refresh functionality
  useEffect(() => {
    if (!isSuperAdmin || !user) return
    
    const interval = setInterval(() => {
      fetchData()
    }, 30000) // Refresh every 30 seconds
    
    return () => clearInterval(interval)
  }, [isSuperAdmin, user, fetchData])

  const filteredUserActivities = userActivities.filter(userActivity => {
    const matchesSearch = userActivity.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         userActivity.email.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesFilter = filterUserType === 'all' || userActivity.userType === filterUserType
    return matchesSearch && matchesFilter
  })

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('fa-IR')
  }


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
          <Button onClick={() => window.location.reload()}>
            تلاش دوباره
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Crown className="h-8 w-8 text-purple-600" />
            <h1 className="text-3xl font-bold text-slate-800">لاگ‌ها و آمار سیستم</h1>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchData()}
              className="flex items-center gap-2"
            >
              <Clock className="h-4 w-4" />
              تازه‌سازی
            </Button>
            <Badge variant="secondary" className="text-xs">
              به‌روزرسانی خودکار هر ۳۰ ثانیه
            </Badge>
          </div>
        </div>
        <p className="text-slate-600">آمار و گزارش‌های تفصیلی مکالمات و فعالیت‌های کاربران</p>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">کل مکالمات</CardTitle>
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{conversationStats?.totalConversations.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              {conversationStats?.activeConversations} فعال
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">کل پیام‌ها</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{conversationStats?.totalMessages.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              میانگین {conversationStats?.averageMessagesPerConversation} پیام
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">امروز</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{conversationStats?.conversationsToday}</div>
            <p className="text-xs text-muted-foreground">
              {conversationStats?.conversationsThisWeek} این هفته
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">کاربران فعال</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{userActivities.filter(u => u.isActive).length}</div>
            <p className="text-xs text-muted-foreground">
              از {userActivities.length} کاربر
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Tabs */}
      <Tabs defaultValue="conversations" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="conversations">آمار مکالمات</TabsTrigger>
          <TabsTrigger value="users">فعالیت کاربران</TabsTrigger>
          <TabsTrigger value="recent">مکالمات اخیر</TabsTrigger>
        </TabsList>

        {/* Conversations Tab */}
        <TabsContent value="conversations" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Hourly Activity Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  ساعات فعالیت
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {conversationStats?.topActiveHours.map((hour) => {
                    const maxCount = Math.max(...conversationStats.topActiveHours.map(h => h.count));
                    return (
                      <div key={hour.hour} className="flex items-center gap-3">
                        <div className="w-12 text-sm">{hour.hour}:00</div>
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{ width: `${(hour.count / maxCount) * 100}%` }}
                          ></div>
                        </div>
                        <div className="w-12 text-sm text-right">{hour.count}</div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {/* User Participation */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <PieChart className="h-5 w-5" />
                  مشارکت کاربران
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {conversationStats?.userParticipationStats.map((stat) => (
                    <div key={stat.userType} className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-3 h-3 bg-blue-600 rounded-full"></div>
                        <span className="text-sm font-medium">{stat.userType}</span>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-bold">{stat.count}</div>
                        <div className="text-xs text-muted-foreground">{stat.percentage}%</div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Users Tab */}
        <TabsContent value="users" className="space-y-6">
          {/* Filters */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex-1">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                    <Input
                      placeholder="جستجو بر اساس نام یا ایمیل..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant={filterUserType === 'all' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setFilterUserType('all')}
                  >
                    همه
                  </Button>
                  <Button
                    variant={filterUserType === 'Customer' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setFilterUserType('Customer')}
                  >
                    مشتریان
                  </Button>
                  <Button
                    variant={filterUserType === 'Admin' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setFilterUserType('Admin')}
                  >
                    ادمین‌ها
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* User Activities Table */}
          <Card>
            <CardHeader>
              <CardTitle>فعالیت کاربران</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>کاربر</TableHead>
                    <TableHead>نوع</TableHead>
                    <TableHead>مکالمات</TableHead>
                    <TableHead>پیام‌ها</TableHead>
                    <TableHead>میانگین</TableHead>
                    <TableHead>آخرین فعالیت</TableHead>
                    <TableHead>وضعیت</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredUserActivities.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{user.name}</div>
                          <div className="text-sm text-muted-foreground">{user.email}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={user.userType === 'Admin' ? 'default' : 'secondary'}>
                          {user.userType}
                        </Badge>
                      </TableCell>
                      <TableCell>{user.totalConversations}</TableCell>
                      <TableCell>{user.totalMessages}</TableCell>
                      <TableCell>{user.averageMessagesPerConversation.toFixed(1)}</TableCell>
                      <TableCell>{formatDate(user.lastActivity)}</TableCell>
                      <TableCell>
                        <Badge variant={user.isActive ? 'default' : 'secondary'}>
                          {user.isActive ? 'فعال' : 'غیرفعال'}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Recent Conversations Tab */}
        <TabsContent value="recent" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>مکالمات اخیر</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>مشتری</TableHead>
                    <TableHead>ادمین</TableHead>
                    <TableHead>زمان شروع</TableHead>
                    <TableHead>مدت زمان</TableHead>
                    <TableHead>تعداد پیام</TableHead>
                    <TableHead>وضعیت</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recentConversations.map((conversation) => (
                    <TableRow key={conversation.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{conversation.customerName}</div>
                          <div className="text-sm text-muted-foreground">{conversation.customerEmail}</div>
                        </div>
                      </TableCell>
                      <TableCell>{conversation.adminName || '-'}</TableCell>
                      <TableCell>{formatDate(conversation.startTime)}</TableCell>
                      <TableCell>{conversation.duration || '-'}</TableCell>
                      <TableCell>{conversation.messageCount}</TableCell>
                      <TableCell>
                        <Badge variant={conversation.status === 'active' ? 'default' : 'secondary'}>
                          {conversation.status === 'active' ? 'فعال' : 'تکمیل شده'}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default SuperAdminLogsPage