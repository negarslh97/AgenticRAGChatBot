'use client'

import React, { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { Button } from '../ui/button'
import { Avatar, AvatarFallback } from '../ui/avatar'
import {
  LayoutDashboard,
  Users,
  Ticket,
  BookOpen,
  Activity,
  Settings,
  LogOut,
  Crown,
  ChevronDown,
  ChevronRight,
  FileQuestion,
  MessageCircle
} from 'lucide-react'

const Sidebar: React.FC = () => {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [expandedMenus, setExpandedMenus] = useState<string[]>([])

  const toggleMenu = (menuName: string) => {
    setExpandedMenus(prev =>
      prev.includes(menuName)
        ? prev.filter(name => name !== menuName)
        : [...prev, menuName]
    )
  }

  const isMenuExpanded = (menuName: string) => expandedMenus.includes(menuName)

  const isSubItemActive = (href: string) => location.pathname === href

  const navigationItems = [
    {
      name: 'داشبورد',
      href: '/super-admin',
      icon: LayoutDashboard
    },
    {
      name: 'چت با Sally',
      href: '/super-admin/chat',
      icon: MessageCircle
    },
    {
      name: 'مدیریت کاربران',
      icon: Users,
      submenu: [
        {
          name: 'مدیریت ادمین‌ها',
          href: '/super-admin/admin/users'
        },
        {
          name: 'مدیریت مشتریان',
          href: '/super-admin/customer/users'
        }
      ]
    },
    {
      name: 'مدیریت تیکت‌ها',
      href: '/super-admin/tickets',
      icon: Ticket
    },
    {
      name: 'پایگاه دانش',
      icon: BookOpen,
      submenu: [
        {
          name: 'مدیریت مقالات',
          href: '/super-admin/knowledge-base'
        },
        {
          name: '🔄 Re-indexing',
          href: '/super-admin/knowledge-base/reindex'
        }
      ]
    },
    {
      name: 'لاگ‌های فعالیت',
      href: '/super-admin/logs',
      icon: Activity
    },
    {
      name: 'تنظیمات سیستم',
      href: '/super-admin/settings',
      icon: Settings
    }
  ]

  const getInitials = (fullName: string) => {
    return fullName
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }

  const getRoleDisplay = (role: string) => {
    switch (role) {
      case 'Customer':
        return 'مشتری'
      case 'Guest':
        return 'مهمان'
      case 'Admin':
        return 'ادمین'
      case 'SuperAdmin':
        return 'ادمین ارشد'
      default:
        return role
    }
  }

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'Customer':
        return 'bg-green-100 text-green-800'
      case 'Guest':
        return 'bg-gray-100 text-gray-800'
      case 'Admin':
        return 'bg-blue-100 text-blue-800'
      case 'SuperAdmin':
        return 'bg-purple-100 text-purple-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="h-full w-64 bg-white border-l border-gray-200 flex flex-col shadow-lg">
      {/* User Profile Section */}
      <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-blue-50">
        <div className="flex items-center space-x-3 mb-4">
          <Avatar className="h-12 w-12">
            {user?.full_name ? (
              <AvatarFallback className="bg-purple-100 text-purple-600 font-medium text-lg">
                {getInitials(user.full_name)}
              </AvatarFallback>
            ) : (
              <AvatarFallback className="bg-purple-100 text-purple-600 font-medium text-lg">
                <Crown className="h-6 w-6" />
              </AvatarFallback>
            )}
          </Avatar>
          <div className="flex-1 text-left">
            <p className="text-sm font-semibold text-gray-900">
              {user?.full_name || 'ادمین ارشد'}
            </p>
            <div className="flex items-center justify-start mt-1">
              <Crown className="h-3 w-3 text-purple-600 ml-1" />
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getRoleColor(user?.role || 'SuperAdmin')}`}>
                {getRoleDisplay(user?.role || 'SuperAdmin')}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Links - Scrollable section */}
      <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto min-h-0">
        {navigationItems.map((item) => {
          const Icon = item.icon
          const hasSubmenu = item.submenu && item.submenu.length > 0
          const isExpanded = isMenuExpanded(item.name)
          const isActive = item.href ? location.pathname === item.href : false
          const hasActiveSubItem = hasSubmenu && item.submenu?.some(sub => isSubItemActive(sub.href))

          if (hasSubmenu) {
            return (
              <div key={item.name}>
                <button
                  onClick={() => toggleMenu(item.name)}
                  className={`flex items-center justify-between w-full px-4 py-3 text-sm font-medium rounded-lg transition-colors duration-200 ${
                    isActive || hasActiveSubItem
                      ? 'bg-blue-50 text-blue-700 border-l-3 border-blue-700 shadow-sm'
                      : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  <div className="flex items-center">
                    <Icon className="mr-3 h-5 w-5" />
                    {item.name}
                  </div>
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </button>
                {isExpanded && (
                  <div className="ml-4 mt-2 space-y-1">
                    {item.submenu?.map((subItem) => (
                      <NavLink
                        key={subItem.name}
                        to={subItem.href}
                        className={({ isActive }) =>
                          `flex items-center px-4 py-2.5 text-sm font-medium rounded-lg transition-colors duration-200 ml-2 ${
                            isActive
                              ? 'bg-blue-50 text-blue-700 border-l-3 border-blue-700 shadow-sm'
                              : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                          }`
                        }
                      >
                        <FileQuestion className="mr-2 h-4 w-4" />
                        {subItem.name}
                      </NavLink>
                    ))}
                  </div>
                )}
              </div>
            )
          }

          return (
            <NavLink
              key={item.name}
              to={item.href!}
              className={({ isActive }) =>
                `flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors duration-200 ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 border-l-3 border-blue-700 shadow-sm'
                    : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
            >
              <Icon className="mr-3 h-5 w-5" />
              {item.name}
            </NavLink>
          )
        })}
      </nav>

      {/* Logout Button - Sticky Footer */}
      <div className="p-4 border-t border-gray-200 mt-auto">
        <Button
          onClick={logout}
          variant="outline"
          size="sm"
          className="w-full flex items-center justify-center gap-2 text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200 hover:border-red-300 transition-colors duration-200"
        >
          <LogOut className="h-4 w-4" />
          خروج
        </Button>
      </div>
    </div>
  )
}

export default Sidebar