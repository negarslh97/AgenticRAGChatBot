'use client'

import React from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Navbar from '../Navbar'
import SallyFloatingAgent from '../SallyFloatingAgent'

const SuperAdminLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Navbar */}
      <Navbar />

      {/* Main Content Area with Sidebar */}
      <div className="flex">
        {/* Desktop Sidebar - Fixed on the right side */}
        <div className="hidden lg:block w-64 flex-shrink-0 h-full fixed top-0 right-0 z-30"
             style={{
               top: '120px',
               height: `calc(100vh - 120px)`
             }}>
          <Sidebar />
        </div>

        {/* Main Content - Add right padding for desktop sidebar */}
        <main className="flex-1 lg:pr-64 p-6">
          <Outlet />
        </main>
      </div>

      {/* Floating Sally Agent Button */}
      <SallyFloatingAgent />
    </div>
  )
}

export default SuperAdminLayout