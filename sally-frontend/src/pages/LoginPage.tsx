"use client"

import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { toast } from "react-hot-toast"

const LoginPage: React.FC = () => {
  const { login, getDashboardByRole } = useAuth()
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    email: "",
    password: ""
  })
  const [loading, setLoading] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      const response = await login(formData.email, formData.password)
      toast.success("ورود با موفقیت انجام شد")

      // تعیین داشبورد بر اساس نقش کاربر
      const userRole = response.user.role || "user"
      const dashboardPath = getDashboardByRole(userRole)

      navigate(dashboardPath)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "ورود ناموفق بود")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary/5 to-secondary/10 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 fade-in">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-foreground mb-2">
            خوش آمدید به Sally
          </h2>
          <p className="text-muted-foreground">
            وارد حساب کاربری خود شوید
          </p>
        </div>
        
        <div className="card p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-foreground mb-1">
                ایمیل
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                value={formData.email}
                onChange={handleChange}
                className="input-field"
                placeholder="example@email.com"
              />
            </div>
            
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-foreground mb-1">
                رمز عبور
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                value={formData.password}
                onChange={handleChange}
                className="input-field"
                placeholder="••••••••"
              />
            </div>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  id="remember-me"
                  name="remember-me"
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="h-4 w-4 text-primary focus:ring-primary border-input rounded"
                />
                <label htmlFor="remember-me" className="ml-2 block text-sm text-foreground">
                  مرا به خاطر بسپار
                </label>
              </div>
              
              <div className="text-sm">
                <Link to="#" className="font-medium text-primary hover:opacity-80">
                  رمز عبور را فراموش کردید؟
                </Link>
              </div>
            </div>
            
            <div>
              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full"
              >
                {loading ? "در حال ورود..." : "ورود به حساب"}
              </button>
            </div>
            
            <div className="text-center">
              <p className="text-sm text-muted-foreground">
                حساب کاربری ندارید؟{" "}
                <Link to="/register" className="font-medium text-primary hover:opacity-80">
                  ثبت‌نام کنید
                </Link>
              </p>
            </div>
          </form>
        </div>
        
        <div className="text-center text-sm text-muted-foreground">
          <p>
            با ورود به حساب کاربری شما با قوانین Sally موافقت می‌کنید
          </p>
        </div>
      </div>
    </div>
  )
}

export default LoginPage
