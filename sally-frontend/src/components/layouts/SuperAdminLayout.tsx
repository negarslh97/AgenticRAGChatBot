'use client'

import React from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Navbar from '../Navbar'

const SuperAdminLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Navbar */}
      <Navbar />

      {/* Main Content Area with Sidebar */}
      <div className="flex">
        {/* Fixed Sidebar - Now positioned absolutely */}
        <Sidebar />

        {/* Main Content - Add left margin for fixed sidebar */}
        <main className="flex-1 ml-64 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default SuperAdminLayout