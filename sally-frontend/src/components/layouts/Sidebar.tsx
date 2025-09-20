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
  ChevronRight
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
      href: '/super-admin/knowledge-base',
      icon: BookOpen
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

  return (
    <div className="left-0 top-16 h-100% w-64 bg-white border-r border-gray-200 flex flex-col overflow-hidden">
      {/* Navigation Links */}
      <nav className="flex-1 px-4 py-8 space-y-2 overflow-y-auto">
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
                  className={`flex items-center justify-between w-full px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
                    isActive || hasActiveSubItem
                      ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-700'
                      : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  <div className="flex items-center">
                    <Icon className="ml-3 h-5 w-5" />
                    {item.name}
                  </div>
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </button>
                {isExpanded && (
                  <div className="mr-4 mt-1 space-y-1">
                    {item.submenu?.map((subItem) => (
                      <NavLink
                        key={subItem.name}
                        to={subItem.href}
                        className={({ isActive }) =>
                          `flex items-center px-4 py-2 text-sm font-medium rounded-lg transition-colors mr-2 ${
                            isActive
                              ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-700'
                              : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                          }`
                        }
                      >
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
                `flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-700'
                    : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
            >
              <Icon className="ml-3 h-5 w-5" />
              {item.name}
            </NavLink>
          )
        })}
      </nav>

      {/* User Profile Section */}
      {/* <div className="p-4 border-t border-gray-200">
        <div className="flex items-center space-x-3 mb-4">
          <Avatar className="h-10 w-10">
            {user?.full_name ? (
              <AvatarFallback className="bg-purple-100 text-purple-600 font-medium">
                {getInitials(user.full_name)}
              </AvatarFallback>
            ) : (
              <AvatarFallback className="bg-purple-100 text-purple-600 font-medium">
                U
              </AvatarFallback>
            )}
          </Avatar>
          <div className="flex-1 text-right">
            <p className="text-sm font-medium text-gray-900">
              {user?.full_name || user?.email}
            </p>
            <div className="flex items-center">
              <Crown className="h-3 w-3 text-purple-600 ml-1" />
              <span className="text-xs text-purple-600">ادمین ارشد</span>
            </div>
          </div>
        </div>

        <Button
          onClick={logout}
          variant="outline"
          size="sm"
          className="w-full flex items-center justify-center gap-2 text-red-600 hover:text-red-700 hover:bg-red-50"
        >
          <LogOut className="h-4 w-4" />
          خروج
        </Button>
      </div> */}
    </div>
  )
}

export default Sidebar