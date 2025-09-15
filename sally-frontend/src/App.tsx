import { BrowserRouter as Router, Routes, Route } from "react-router-dom"
import { AuthProvider } from "./context/AuthContext"
import { Toaster } from "react-hot-toast"

// Pages
import Navbar from "./components/Navbar"
import HomePage from "./pages/HomePage"
import LoginPage from "./pages/LoginPage"
import RegisterPage from "./pages/RegisterPage"
import DashboardPage from "./pages/DashboardPage"
import ChatPage from "./pages/ChatPage"
import TicketsPage from "./pages/TicketsPage"
import KnowledgeBasePage from "./pages/KnowledgeBasePage"
import AdminPanel from "./pages/AdminPanel"
import SuperAdminDashboard from "./pages/SuperAdminDashboard"
import UserManagementPage from "./pages/UserManagementPage"

// Layouts
import SuperAdminLayout from "./components/layouts/SuperAdminLayout"

// Components
import ProtectedRoute from "./components/ProtectedRoute"

const App: React.FC = () => {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public routes with navbar */}
          <Route path="/" element={
            <div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-50">
              <Navbar />
              <main>
                <HomePage />
              </main>
            </div>
          } />
          <Route path="/login" element={
            <div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-50">
              <Navbar />
              <main>
                <LoginPage />
              </main>
            </div>
          } />
          <Route path="/register" element={
            <div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-50">
              <Navbar />
              <main>
                <RegisterPage />
              </main>
            </div>
          } />

          {/* Protected routes with navbar */}
          <Route path="/dashboard" element={
            <div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-50">
              <Navbar />
              <main>
                <DashboardPage />
              </main>
            </div>
          } />
          <Route path="/chat" element={
            <div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-50">
              <Navbar />
              <main>
                <ChatPage />
              </main>
            </div>
          } />
          <Route path="/knowledge-base/*" element={
            <div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-50">
              <Navbar />
              <main>
                <KnowledgeBasePage />
              </main>
            </div>
          } />
          <Route path="/tickets/*" element={
            <div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-50">
              <Navbar />
              <main>
                <ProtectedRoute>
                  <TicketsPage />
                </ProtectedRoute>
              </main>
            </div>
          } />
          <Route path="/admin" element={
            <div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-50">
              <Navbar />
              <main>
                <ProtectedRoute requiredRole="Admin">
                  <AdminPanel />
                </ProtectedRoute>
              </main>
            </div>
          } />

          {/* Super Admin routes with sidebar layout */}
          <Route
            path="/super-admin"
            element={
              <ProtectedRoute requiredRole="SuperAdmin">
                <SuperAdminLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<SuperAdminDashboard />} />
            <Route path="users" element={<UserManagementPage />} />
            <Route path="tickets" element={<div className="p-6"><h1 className="text-2xl font-bold">مدیریت تیکت‌ها</h1><p>این صفحه به زودی پیاده‌سازی خواهد شد.</p></div>} />
            <Route path="knowledge-base" element={<div className="p-6"><h1 className="text-2xl font-bold">پایگاه دانش</h1><p>این صفحه به زودی پیاده‌سازی خواهد شد.</p></div>} />
            <Route path="logs" element={<div className="p-6"><h1 className="text-2xl font-bold">لاگ‌های فعالیت</h1><p>این صفحه به زودی پیاده‌سازی خواهد شد.</p></div>} />
            <Route path="settings" element={<div className="p-6"><h1 className="text-2xl font-bold">تنظیمات سیستم</h1><p>این صفحه به زودی پیاده‌سازی خواهد شد.</p></div>} />
          </Route>
        </Routes>
        <Toaster position="top-right" />
      </Router>
    </AuthProvider>
  )
}

export default App
