'use client'

import React from 'react'
import { Card, CardContent } from '../ui/card'
import { LucideIcon } from 'lucide-react'

interface StatCard {
  title: string
  value: number | string
  icon: LucideIcon
  color: string
  description?: string
  trend?: {
    value: number
    label: string
    type: 'positive' | 'negative' | 'neutral'
  }
}

interface DashboardStatsProps {
  stats: StatCard[]
  variant?: 'glassmorphism' | 'solid' | 'minimal'
  columns?: 1 | 2 | 3 | 4
  showAnimations?: boolean
}

const DashboardStats: React.FC<DashboardStatsProps> = ({
  stats,
  variant = 'glassmorphism',
  columns = 3,
  showAnimations = true
}) => {
  const getVariantClasses = () => {
    switch (variant) {
      case 'glassmorphism':
        return 'bg-white/50 backdrop-blur-lg border border-white/30 hover:shadow-xl'
      case 'solid':
        return 'bg-white shadow-md hover:shadow-lg'
      case 'minimal':
        return 'bg-transparent border border-gray-200 hover:bg-gray-50'
      default:
        return 'bg-white/50 backdrop-blur-lg border border-white/30 hover:shadow-xl'
    }
  }

  const getGridClasses = () => {
    switch (columns) {
      case 1:
        return 'grid-cols-1'
      case 2:
        return 'grid-cols-1 md:grid-cols-2'
      case 3:
        return 'grid-cols-1 md:grid-cols-3'
      case 4:
        return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4'
      default:
        return 'grid-cols-1 md:grid-cols-3'
    }
  }

  return (
    <div className={`grid ${getGridClasses()} gap-6 mb-8`}>
      {stats.map((stat, index) => {
        const Icon = stat.icon
        return (
          <Card
            key={index}
            className={`${getVariantClasses()} transition-all duration-300 ${showAnimations ? 'hover:scale-105' : ''}`}
          >
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-600 mb-1">
                    {stat.title}
                  </p>
                  <div className="flex items-baseline space-x-2">
                    <p className="text-3xl font-bold text-slate-800">
                      {stat.value}
                    </p>
                    {stat.trend && (
                      <span
                        className={`text-sm font-medium ${
                          stat.trend.type === 'positive'
                            ? 'text-green-600'
                            : stat.trend.type === 'negative'
                            ? 'text-red-600'
                            : 'text-gray-600'
                        }`}
                      >
                        {stat.trend.type === 'positive' ? '+' : ''}
                        {stat.trend.value}%
                      </span>
                    )}
                  </div>
                  {stat.description && (
                    <p className="text-xs text-slate-500 mt-1">
                      {stat.description}
                    </p>
                  )}
                  {stat.trend && (
                    <p className="text-xs text-slate-500 mt-1">
                      {stat.trend.label}
                    </p>
                  )}
                </div>
                <div className={`p-3 rounded-full shadow-md ${stat.color}`}>
                  <Icon className="h-6 w-6" />
                </div>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

export default DashboardStats
