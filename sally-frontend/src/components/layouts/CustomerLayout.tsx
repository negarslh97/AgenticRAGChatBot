'use client'

import React from 'react'
import { Outlet } from 'react-router-dom'
import Navbar from '../Navbar'
import CustomerSidebar from './CustomerSidebar'

interface CustomerLayoutProps {
  children?: React.ReactNode
  showSidebar?: boolean
  sidebarWidth?: number
  backgroundPattern?: 'aurora' | 'gradient' | 'simple'
  showMobileSidebar?: boolean
  onMobileSidebarToggle?: () => void
}

// Navbar height constant - calculated from logo height + vertical padding + border
// Logo: h-[72px] = 72px, py-3 = 12px top + 12px bottom = 24px, border-b = 1px, total ~97px
// Adding 3px extra padding to ensure no overlap with any potential line-height or font metrics
const NAVBAR_HEIGHT = '120px' // 97px + 3px safety margin

// Note: Using static value for better performance and simplicity
// If Navbar height changes in the future, update this constant accordingly
// To verify the exact height, inspect the Navbar element in browser DevTools

const CustomerLayout: React.FC<CustomerLayoutProps> = ({
  children,
  showSidebar = true,
  sidebarWidth = 256, // 64 * 4px = 256px
  backgroundPattern = 'aurora',
  showMobileSidebar = false,
  onMobileSidebarToggle
}) => {
  const renderBackground = () => {
    switch (backgroundPattern) {
      case 'aurora':
        return (
          <>
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
          </>
        )
      case 'gradient':
        return (
          <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 opacity-50"></div>
        )
      case 'simple':
        return null
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Create new stacking context */}
      <div
        className="relative isolate"
        style={{ paddingTop: NAVBAR_HEIGHT }}
      >

        {/* Main Layout Container - Height calculated to account for Navbar */}
        <div
          className="relative"
          style={{ minHeight: `calc(100vh - ${NAVBAR_HEIGHT})` }}
        >
          {/* Main Content Area - With left padding for desktop sidebar */}
          <main className={`relative overflow-y-auto overflow-x-hidden transition-all duration-300 ${
            showSidebar ? 'lg:pr-64' : ''
          }`}>
            {/* Background Effects */}
            {renderBackground()}

            {/* Content Container */}
            <div className="relative min-h-full flex flex-col">
              <div className="flex-1 px-6 sm:px-8 lg:px-10 py-8">
                {children || <Outlet />}
              </div>
            </div>
          </main>

          {/* Desktop Sidebar - Fixed on the right side */}
          {showSidebar && (
            <aside className="hidden lg:block w-64 flex-shrink-0 h-full fixed top-0 right-0 z-30"
                style={{
                  top: NAVBAR_HEIGHT,
                  height: `calc(100vh - ${NAVBAR_HEIGHT})`
                }}>
              <CustomerSidebar />
            </aside>
          )}

          {/* Mobile Sidebar Overlay - Positioned below Navbar */}
          {showSidebar && showMobileSidebar && (
            <div className="lg:hidden fixed inset-0 z-40">
              <div
                className="fixed inset-0 bg-black bg-opacity-50"
                onClick={onMobileSidebarToggle}
              />
              <div
                className="fixed right-0 w-64 bg-white shadow-xl z-50"
                style={{
                  top: NAVBAR_HEIGHT,
                  height: `calc(100vh - ${NAVBAR_HEIGHT})`
                }}
              >
                <CustomerSidebar onClose={onMobileSidebarToggle} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default CustomerLayout
