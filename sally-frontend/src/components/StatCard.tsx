import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { LucideIcon } from 'lucide-react'

interface StatCardProps {
  title: string
  stats?: Array<{
    label: string
    value: number | string
  }>
  description?: string
  icon: LucideIcon
  iconColor?: string
  actions?: Array<{
    label: string
    onClick: () => void
    variant?: 'default' | 'outline' | 'secondary'
  }>
}

const StatCard: React.FC<StatCardProps> = ({
  title,
  stats,
  description,
  icon: Icon,
  iconColor = 'text-blue-600',
  actions
}) => {
  return (
    <Card className="bg-white/60 backdrop-blur-lg border border-white/40 hover:shadow-xl transition-all duration-300 hover:scale-105 flex flex-col h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold text-slate-800">
            {title}
          </CardTitle>
          <div className={`${iconColor} p-2 rounded-full bg-white/50 shadow-sm`}>
            <Icon className="h-6 w-6" />
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col">
        <div className="flex-1">
          {stats && stats.length > 0 && (
            <div className="space-y-2 mb-4">
              {stats.map((stat, index) => (
                <div key={index} className="flex justify-between items-center">
                  <span className="text-sm text-slate-600">{stat.label}</span>
                  <span className="text-lg font-bold text-slate-800">{stat.value}</span>
                </div>
              ))}
            </div>
          )}

          {description && (
            <p className="text-sm text-slate-600 mb-4 leading-relaxed">
              {description}
            </p>
          )}
        </div>

        {actions && actions.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-auto pt-4 border-t border-gray-100">
            {actions.map((action, index) => (
              <Button
                key={index}
                onClick={action.onClick}
                variant={action.variant || 'default'}
                size="sm"
                className="flex-1 min-w-0"
              >
                {action.label}
              </Button>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default StatCard