'use client'

import React, { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { Button } from '../ui/button'
import { Avatar, AvatarFallback } from '../ui/avatar'
import {
  LayoutDashboard,
  MessageCircle,
  Ticket,
  BookText,
  UserCog,
  Settings,
  LogOut,
  ChevronDown,
  ChevronRight,
  Activity,
  FileQuestion,
  X
} from 'lucide-react'

// Note: Navbar height is approximately 97px
// If navbar height changes in the future, update the sidebar positioning accordingly

interface CustomerSidebarProps {
  onClose?: () => void
}

const CustomerSidebar: React.FC<CustomerSidebarProps> = ({ onClose }) => {
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

  const navigationItems = [
    {
      name: 'داشبورد',
      href: '/dashboard',
      icon: LayoutDashboard
    },
    {
      name: 'چت با Sally',
      href: '/chat',
      icon: MessageCircle
    },
    {
      name: 'تیکت‌های پشتیبانی',
      icon: Ticket,
      submenu: [
        {
          name: 'تیکت‌های من',
          href: '/tickets'
        },
        {
          name: 'تیکت جدید',
          href: '/tickets/create'
        }
      ]
    },
    {
      name: 'پایگاه دانش',
      href: '/knowledge-base',
      icon: BookText
    },
    {
      name: 'فعالیت‌های اخیر',
      href: '/activity',
      icon: Activity
    },
    {
      name: 'تنظیمات',
      icon: Settings,
      submenu: [
        {
          name: 'پروفایل',
          href: '/profile'
        },
        {
          name: 'تنظیمات امنیتی',
          href: '/security'
        }
      ]
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
      {/* Mobile Close Button */}
      {onClose && (
        <div className="lg:hidden absolute top-4 right-4 z-10">
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      )}
      {/* User Profile Section */}
      <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-purple-50">
        <div className="flex items-center space-x-3 mb-4">
          <Avatar className="h-12 w-12">
            {user?.full_name ? (
              <AvatarFallback className="bg-blue-100 text-blue-600 font-medium text-lg">
                {getInitials(user.full_name)}
              </AvatarFallback>
            ) : (
              <AvatarFallback className="bg-blue-100 text-blue-600 font-medium text-lg">
                <UserCog className="h-6 w-6" />
              </AvatarFallback>
            )}
          </Avatar>
          <div className="flex-1 text-left">
            <p className="text-sm font-semibold text-gray-900">
              {user?.full_name || 'کاربر'}
            </p>
            <div className="flex items-center justify-start mt-1">
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getRoleColor(user?.role || 'Customer')}`}>
                {getRoleDisplay(user?.role || 'Customer')}
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
          const hasActiveSubItem = hasSubmenu && item.submenu?.some(sub => location.pathname === sub.href)

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

export default CustomerSidebar
