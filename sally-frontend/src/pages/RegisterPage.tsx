"use client"

import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { Button } from "../components/ui/button"
import { toast } from "react-hot-toast"

const RegisterPage: React.FC = () => {
  const { register, getDashboardByRole } = useAuth()
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    password: "",
    confirm_password: ""
  })
  const [loading, setLoading] = useState(false)
  const [acceptTerms, setAcceptTerms] = useState(false)
  const [acceptPrivacy, setAcceptPrivacy] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const validateForm = () => {
    if (!formData.full_name.trim()) {
      toast.error("لطفاً نام کامل خود را وارد کنید")
      return false
    }
    
    if (!formData.email.trim()) {
      toast.error("لطفاً ایمیل خود را وارد کنید")
      return false
    }
    
    if (!formData.password) {
      toast.error("لطفاً رمز عبور خود را وارد کنید")
      return false
    }
    
    if (formData.password.length < 8) {
      toast.error("رمز عبور باید حداقل ۸ کاراکتر باشد")
      return false
    }
    
    if (formData.password !== formData.confirm_password) {
      toast.error("رمز عبور و تایید رمز عبور یکسان نیستند")
      return false
    }
    
    if (!acceptTerms) {
      toast.error("لطفاً شرایط استفاده را بپذیرید")
      return false
    }
    
    if (!acceptPrivacy) {
      toast.error("لطفاً حریم خصوصی را بپذیرید")
      return false
    }
    
    return true
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }

    setLoading(true)

    try {
      const response = await register(formData.email, formData.password, formData.full_name)
      toast.success("ثبت‌نام با موفقیت انجام شد")

      // تعیین داشبورد بر اساس نقش کاربر
      const userRole = response.user.role || "user"
      const dashboardPath = getDashboardByRole(userRole)

      navigate(dashboardPath)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "ثبت‌نام ناموفق بود")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary/5 to-secondary/10 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 fade-in">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-foreground mb-2">
            ایجاد حساب کاربری
          </h2>
          <p className="text-muted-foreground">
            در Sally ثبت‌نام کنید و از تمام ویژگی‌ها استفاده کنید
          </p>
        </div>
        
        <div className="card p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="full_name" className="block text-sm font-medium text-foreground mb-1">
                نام کامل
              </label>
              <input
                id="full_name"
                name="full_name"
                type="text"
                required
                value={formData.full_name}
                onChange={handleChange}
                className="input-field"
                placeholder="نام و نام خانوادگی"
              />
            </div>
            
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
                placeholder="حداقل ۸ کاراکتر"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                رمز عبور باید حداقل ۸ کاراکتر باشد
              </p>
            </div>
            
            <div>
              <label htmlFor="confirm_password" className="block text-sm font-medium text-foreground mb-1">
                تایید رمز عبور
              </label>
              <input
                id="confirm_password"
                name="confirm_password"
                type="password"
                required
                value={formData.confirm_password}
                onChange={handleChange}
                className="input-field"
                placeholder="رمز عبور را دوباره وارد کنید"
              />
            </div>
            
            <div className="space-y-3">
              <div className="flex items-start">
                <input
                  id="accept-terms"
                  name="accept-terms"
                  type="checkbox"
                  checked={acceptTerms}
                  onChange={(e) => setAcceptTerms(e.target.checked)}
                  className="h-4 w-4 text-primary focus:ring-primary border-input rounded mt-0.5"
                />
                <label htmlFor="accept-terms" className="ml-2 block text-sm text-foreground">
                  من <Link to="#" className="text-primary hover:opacity-80">شرایط استفاده</Link> را می‌پذیرم
                </label>
              </div>
              
              <div className="flex items-start">
                <input
                  id="accept-privacy"
                  name="accept-privacy"
                  type="checkbox"
                  checked={acceptPrivacy}
                  onChange={(e) => setAcceptPrivacy(e.target.checked)}
                  className="h-4 w-4 text-primary focus:ring-primary border-input rounded mt-0.5"
                />
                <label htmlFor="accept-privacy" className="ml-2 block text-sm text-foreground">
                  من <Link to="#" className="text-primary hover:opacity-80">سیاست حریم خصوصی</Link> را می‌پذیرم
                </label>
              </div>
            </div>
            
            <div>
              <Button
                type="submit"
                disabled={loading}
                className="w-full"
              >
                {loading ? "در حال ثبت‌نام..." : "ثبت‌نام"}
              </Button>
            </div>
            
            <div className="text-center">
              <p className="text-sm text-muted-foreground">
                حساب کاربری دارید؟{" "}
                <Link to="/login" className="font-medium text-primary hover:opacity-80">
                  وارد شوید
                </Link>
              </p>
            </div>
          </form>
        </div>
        
        <div className="text-center text-sm text-muted-foreground">
          <p>
            با ثبت‌نام در Sally، شما با قوانین ما موافقت می‌کنید
          </p>
        </div>
      </div>
    </div>
  )
}

export default RegisterPage
