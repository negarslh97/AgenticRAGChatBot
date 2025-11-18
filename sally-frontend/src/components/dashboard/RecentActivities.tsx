'use client'

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Badge } from '../ui/badge'
import { LucideIcon } from 'lucide-react'

interface Activity {
  id: string
  type: 'article_published' | 'login' | 'profile_update'
  title: string
  description: string
  timestamp: string
  status?: 'در حال بررسی' | 'پاسخ داده شده' | 'حل شده' | 'موفق' | 'ناموفق'
  icon?: LucideIcon
  priority?: 'low' | 'medium' | 'high'
  metadata?: Record<string, any>
}

interface RecentActivitiesProps {
  activities: Activity[]
  maxItems?: number
  showIcons?: boolean
  showStatus?: boolean
  showPriority?: boolean
  variant?: 'default' | 'compact' | 'minimal'
  emptyMessage?: string
  emptyIcon?: LucideIcon
  onActivityClick?: (activity: Activity) => void
}

const RecentActivities: React.FC<RecentActivitiesProps> = ({
  activities,
  maxItems = 10,
  showIcons = true,
  showStatus = true,
  showPriority = false,
  variant = 'default',
  emptyMessage = 'هیچ فعالیتی یافت نشد',
  emptyIcon: EmptyIcon,
  onActivityClick
}) => {
  const getActivityIcon = (type: Activity['type']) => {
    const iconMap = {
      article_published: '📄',
      login: '🔐',
      profile_update: '👤'
    }
    return iconMap[type] || '📋'
  }

  const getStatusBadgeVariant = (status?: Activity['status']) => {
    switch (status) {
      case 'در حال بررسی':
        return 'warning'
      case 'پاسخ داده شده':
        return 'success'
      case 'حل شده':
        return 'default'
      case 'موفق':
        return 'default'
      case 'ناموفق':
        return 'destructive'
      default:
        return 'secondary'
    }
  }

  const getPriorityColor = (priority?: Activity['priority']) => {
    switch (priority) {
      case 'high':
        return 'text-red-600 bg-red-50'
      case 'medium':
        return 'text-yellow-600 bg-yellow-50'
      case 'low':
        return 'text-green-600 bg-green-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  const getVariantClasses = () => {
    switch (variant) {
      case 'compact':
        return 'p-3 space-y-3'
      case 'minimal':
        return 'p-4 space-y-2'
      default:
        return 'p-6 space-y-4'
    }
  }

  const displayActivities = activities.slice(0, maxItems)

  if (variant === 'minimal') {
    return (
      <div className="space-y-2">
        {displayActivities.map((activity) => (
          <div
            key={activity.id}
            className="flex items-center justify-between py-2 px-3 hover:bg-gray-50 rounded-lg transition-colors cursor-pointer"
            onClick={() => onActivityClick?.(activity)}
          >
            <div className="flex items-center space-x-3">
              {showIcons && (
                <span className="text-sm">{getActivityIcon(activity.type)}</span>
              )}
              <div>
                <p className="text-sm font-medium text-gray-900">{activity.title}</p>
                <p className="text-xs text-gray-500">{activity.description}</p>
              </div>
            </div>
            <span className="text-xs text-gray-400">{activity.timestamp}</span>
          </div>
        ))}
      </div>
    )
  }

  return (
    <Card className="bg-white/60 backdrop-blur-lg border border-white/40">
      <CardHeader>
        <CardTitle className="text-xl font-bold text-slate-800">
          فعالیت‌های اخیر
        </CardTitle>
        <div className="text-slate-600 text-sm">
          آخرین فعالیت‌های حساب کاربری شما
        </div>
      </CardHeader>
      <CardContent>
        <div className={getVariantClasses()}>
          {displayActivities.map((activity) => (
            <div
              key={activity.id}
              className={`flex items-center justify-between ${
                variant === 'compact' ? 'p-3' : 'p-4'
              } hover:bg-white/30 rounded-lg transition-colors group cursor-pointer`}
              onClick={() => onActivityClick?.(activity)}
            >
              <div className="flex items-center space-x-4">
                {showIcons && (
                  <div className="flex-shrink-0">
                    <div className="bg-white/50 p-2 rounded-full shadow-sm group-hover:shadow-md transition-shadow duration-300">
                      <span className="text-sm">{getActivityIcon(activity.type)}</span>
                    </div>
                  </div>
                )}
                <div className="space-y-1 flex-1">
                  <h4 className="text-sm font-semibold text-slate-800 group-hover:text-blue-600 transition-colors">
                    {activity.title}
                  </h4>
                  <p className="text-sm text-slate-600">
                    {activity.description}
                  </p>
                  {showPriority && activity.priority && (
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getPriorityColor(activity.priority)}`}>
                      {activity.priority === 'high' ? 'بالا' : activity.priority === 'medium' ? 'متوسط' : 'پایین'}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center space-x-3">
                {showStatus && activity.status && (
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

          {displayActivities.length === 0 && (
            <div className="text-center py-8">
              <div className="text-slate-400 text-4xl mb-4">
                {EmptyIcon ? <EmptyIcon className="h-16 w-16 mx-auto" /> : '⏰'}
              </div>
              <p className="text-slate-500">{emptyMessage}</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default RecentActivities
