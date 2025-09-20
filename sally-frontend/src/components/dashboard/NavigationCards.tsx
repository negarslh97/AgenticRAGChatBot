'use client'

import React from 'react'
import { Link } from 'react-router-dom'
import { Card, CardContent } from '../ui/card'
import { LucideIcon } from 'lucide-react'

interface NavigationCard {
  title: string
  description: string
  icon: LucideIcon
  link: string
  color: string
  disabled?: boolean
  badge?: string
  onClick?: () => void
}

interface NavigationCardsProps {
  cards: NavigationCard[]
  variant?: 'grid' | 'list' | 'compact'
  columns?: 1 | 2 | 3 | 4
  showAnimations?: boolean
  className?: string
}

const NavigationCards: React.FC<NavigationCardsProps> = ({
  cards,
  variant = 'grid',
  columns = 4,
  showAnimations = true,
  className = ''
}) => {
  const getVariantClasses = () => {
    switch (variant) {
      case 'grid':
        return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4'
      case 'list':
        return 'space-y-4'
      case 'compact':
        return 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4'
      default:
        return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4'
    }
  }

  const getCardClasses = () => {
    const baseClasses = 'bg-white/60 backdrop-blur-lg border border-white/40 hover:border-blue-400 hover:shadow-2xl transition-all duration-300 cursor-pointer h-full group'

    if (showAnimations) {
      return `${baseClasses} hover:scale-105`
    }

    return `${baseClasses} hover:shadow-xl`
  }

  const getListCardClasses = () => {
    const baseClasses = 'bg-white/60 backdrop-blur-lg border border-white/40 hover:border-blue-400 hover:shadow-xl transition-all duration-300 cursor-pointer group'

    if (showAnimations) {
      return `${baseClasses} hover:scale-[1.02]`
    }

    return baseClasses
  }

  if (variant === 'list') {
    return (
      <div className={`space-y-4 ${className}`}>
        {cards.map((card, index) => (
          <Link key={index} to={card.disabled ? '#' : card.link} onClick={card.onClick}>
            <Card className={getListCardClasses()}>
              <CardContent className="p-6">
                <div className="flex items-center space-x-4">
                  <div className={`${card.color} flex-shrink-0 group-hover:scale-110 transition-transform duration-300`}>
                    <card.icon className="h-8 w-8" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-semibold text-slate-800 group-hover:text-blue-600 transition-colors duration-300">
                        {card.title}
                      </h3>
                      {card.badge && (
                        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                          {card.badge}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-600 leading-relaxed mt-1">
                      {card.description}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    )
  }

  return (
    <div className={`grid ${getVariantClasses()} gap-6 mb-8 ${className}`}>
      {cards.map((card, index) => (
        <Link key={index} to={card.disabled ? '#' : card.link} onClick={card.onClick}>
          <Card className={`${getCardClasses()} ${card.disabled ? 'opacity-50 cursor-not-allowed' : ''}`}>
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
              {card.badge && (
                <span className="inline-block mt-3 text-xs bg-blue-100 text-blue-800 px-3 py-1 rounded-full">
                  {card.badge}
                </span>
              )}
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  )
}

export default NavigationCards
