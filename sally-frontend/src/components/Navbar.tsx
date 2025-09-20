import React from "react"
import { Link } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { Button } from "./ui/button"
import logo from "../assets/logo.png" // مسیر لوگو را به درستی تنظیم کنید
import { Menu } from "lucide-react"

interface NavbarProps {
  onMobileMenuToggle?: () => void
}

const Navbar: React.FC<NavbarProps> = ({ onMobileMenuToggle }) => {
  const { user, logout, isAuthenticated, isAdmin } = useAuth()

  const handleLogout = () => {
    logout()
  }

  return (
    // <nav className="bg-white border-b border-gray-200 px-4 py-3">
    <nav className="bg-white px-4 py-3 border-b border-gray-200">
      <div className="max-w-7xl mx-auto flex items-center justify-between">

        {/* Left side - Logo and Mobile Menu */}
        <div className="flex items-center">
          {/* Mobile Menu Button */}
          {isAuthenticated && onMobileMenuToggle && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onMobileMenuToggle}
              className="lg:hidden mr-3 p-2"
            >
              <Menu className="h-5 w-5" />
            </Button>
          )}

          <Link to={user ? "/dashboard" : "/"}>
            <img
                src={logo}
                alt="Sally Logo"
                className="h-[72px] w-auto"
            />
          </Link>
        </div>

        {/* Left side */}
        <div className="flex items-center space-x-4">
          {!isAuthenticated ? (
            // Guest view - Login and Register buttons
            <>
              <Link to="/login">
                <Button variant="ghost">ورود</Button>
              </Link>
              <Link to="/register">
                <Button>ثبت‌نام</Button>
              </Link>
            </>
          ) : (
            // Authenticated view - Logout and Profile buttons
            <>
              <Button
                variant="ghost"
                onClick={handleLogout}
                className="text-red-600 hover:text-red-700 hover:bg-red-50"
              >
                خروج
              </Button>
              <Link to="/dashboard">
                <Button variant="ghost">داشبورد</Button>
              </Link>
            </>
          )}
        </div>

      </div>

      {/* Navigation Links for authenticated users (below the main navbar) */}
      {isAuthenticated && (
        <div className="max-w-7xl mx-auto mt-3 border-t border-gray-200 pt-3">
          {/* <div className="hidden md:flex items-center justify-center space-x-6">
            <Link
              to="/dashboard"
              className="text-gray-700 hover:text-blue-600 transition-colors font-medium"
            >
              داشبورد
            </Link>
            <Link
              to="/chat"
              className="text-gray-700 hover:text-blue-600 transition-colors font-medium"
            >
              چت
            </Link>
            <Link
              to="/tickets"
              className="text-gray-700 hover:text-blue-600 transition-colors font-medium"
            >
              تیکت‌ها
            </Link>
            <Link
              to="/knowledge-base"
              className="text-gray-700 hover:text-blue-600 transition-colors font-medium"
            >
              پایگاه دانش
            </Link>
            {isAdmin && (
              <Link
                to="/admin"
                className="text-gray-700 hover:text-blue-600 transition-colors font-medium"
              >
                پنل ادمین
              </Link>
            )}
          </div>

          // Mobile navigation
          <div className="md:hidden flex flex-wrap gap-4 justify-center mt-2">
            <Link
              to="/dashboard"
              className="text-sm text-gray-700 hover:text-blue-600 transition-colors"
            >
              داشبورد
            </Link>
            <Link
              to="/chat"
              className="text-sm text-gray-700 hover:text-blue-600 transition-colors"
            >
              چت
            </Link>
            <Link
              to="/tickets"
              className="text-sm text-gray-700 hover:text-blue-600 transition-colors"
            >
              تیکت‌ها
            </Link>
            <Link
              to="/knowledge-base"
              className="text-sm text-gray-700 hover:text-blue-600 transition-colors"
            >
              پایگاه دانش
            </Link>
            {isAdmin && (
              <Link
                to="/admin"
                className="text-sm text-gray-700 hover:text-blue-600 transition-colors"
              >
                پنل ادمین
              </Link>
            )}
          </div> */}
        </div>
      )}
    </nav>
  )
}

export default Navbar