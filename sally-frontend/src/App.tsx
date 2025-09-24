import React, { Suspense, lazy } from "react"
import { BrowserRouter as Router, Routes, Route } from "react-router-dom"
import { AuthProvider } from "./context/AuthContext"
import { Toaster } from "react-hot-toast"

// Layouts
import MainLayout from "./components/layouts/MainLayout"
import SuperAdminLayout from "./components/layouts/SuperAdminLayout"

// Components
import ProtectedRoute from "./components/ProtectedRoute"
import AuthGuard from "./components/AuthGuard"
import ArticleDetail from "./components/ArticleDetail"

// Lazy loaded pages
const HomePage = lazy(() => import("./pages/HomePage"))
const LoginPage = lazy(() => import("./pages/LoginPage"))
const RegisterPage = lazy(() => import("./pages/RegisterPage"))
const DashboardPage = lazy(() => import("./pages/CustomerDashboardPage"))
const ChatPage = lazy(() => import("./pages/ChatPage"))
const TicketsPage = lazy(() => import("./pages/TicketsPage"))
const KnowledgeBasePage = lazy(() => import("./pages/KnowledgeBasePage"))
const AdminPanel = lazy(() => import("./pages/AdminPanel"))
const SuperAdminDashboard = lazy(() => import("./pages/SuperAdminDashboard"))
const SuperAdminKnowledgeBasePage = lazy(() => import("./pages/SuperAdminKnowledgeBasePage"))
const SuperAdminAddArticlePage = lazy(() => import("./pages/SuperAdminAddArticlePage"))
const SuperAdminUploadPage = lazy(() => import("./pages/SuperAdminUploadPage"))
const UserManagementPage = lazy(() => import("./pages/UserManagementPage"))
const AdminUsersPage = lazy(() => import("./pages/AdminUsersPage"))
const CustomerUsersPage = lazy(() => import("./pages/CustomerUsersPage"))
const UnauthorizedPage = lazy(() => import("./pages/UnauthorizedPage"))

// Loading component for Suspense
const LoadingSpinner: React.FC = () => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
  </div>
)

// 404 Not Found Component
const NotFoundPage: React.FC = () => (
  <MainLayout>
    <div className="flex items-center justify-center flex-1">
      <div className="text-center">
        <div className="text-6xl mb-4">🔍</div>
        <h1 className="text-3xl font-bold text-gray-900 mb-4">صفحه یافت نشد</h1>
        <p className="text-gray-600 mb-6">صفحه مورد نظر شما وجود ندارد.</p>
        <a
          href="/"
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 inline-block"
        >
          بازگشت به صفحه اصلی
        </a>
      </div>
    </div>
  </MainLayout>
)


const App: React.FC = () => {
  return (
    <AuthProvider>
      <Router>
        <Suspense fallback={<LoadingSpinner />}>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={
              <MainLayout>
                <HomePage />
              </MainLayout>
            } />
            <Route path="/login" element={
              <MainLayout>
                <LoginPage />
              </MainLayout>
            } />
            <Route path="/register" element={
              <MainLayout>
                <RegisterPage />
              </MainLayout>
            } />

            {/* Protected routes */}
            <Route path="/dashboard" element={
              <MainLayout>
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              </MainLayout>
            } />
            <Route path="/chat" element={
              <MainLayout>
                <ProtectedRoute>
                  <ChatPage />
                </ProtectedRoute>
              </MainLayout>
            } />
            <Route path="/knowledge-base/*" element={
              <MainLayout>
                <KnowledgeBasePage />
              </MainLayout>
            } />
            <Route path="/tickets/*" element={
              <MainLayout>
                <ProtectedRoute>
                  <TicketsPage />
                </ProtectedRoute>
              </MainLayout>
            } />
            <Route path="/admin" element={
              <MainLayout>
                <ProtectedRoute requiredRole="Admin">
                  <AdminPanel />
                </ProtectedRoute>
              </MainLayout>
            } />

            {/* Unauthorized page */}
            <Route path="/unauthorized" element={
              <UnauthorizedPage />
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
              <Route path="admin/users" element={<AdminUsersPage />} />
              <Route path="customer/users" element={<CustomerUsersPage />} />
              <Route path="tickets" element={<div className="p-6"><h1 className="text-2xl font-bold">مدیریت تیکت‌ها</h1><p>این صفحه به زودی پیاده‌سازی خواهد شد.</p></div>} />
              <Route path="knowledge-base" element={<SuperAdminKnowledgeBasePage />} />
              <Route
                path="knowledge-base/add"
                element={
                  <AuthGuard requiredRole="SuperAdmin">
                    <SuperAdminAddArticlePage />
                  </AuthGuard>
                }
              />
              <Route
                path="knowledge-base/upload"
                element={
                  <AuthGuard requiredRole="SuperAdmin">
                    <SuperAdminUploadPage />
                  </AuthGuard>
                }
              />
              <Route path="knowledge-base/articles/:articleId" element={<ArticleDetail isadminView={true} />} />
              <Route path="logs" element={<div className="p-6"><h1 className="text-2xl font-bold">لاگ‌های فعالیت</h1><p>این صفحه به زودی پیاده‌سازی خواهد شد.</p></div>} />
              <Route path="settings" element={<div className="p-6"><h1 className="text-2xl font-bold">تنظیمات سیستم</h1><p>این صفحه به زودی پیاده‌سازی خواهد شد.</p></div>} />
            </Route>

            {/* 404 Not Found */}
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Suspense>
        <Toaster position="top-right" />
      </Router>
    </AuthProvider>
  )
}

export default App
