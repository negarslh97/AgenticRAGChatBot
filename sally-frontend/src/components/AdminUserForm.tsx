'use client'

import React, { useState, useEffect } from 'react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Label } from './ui/label'
import { AlertCircle, UserPlus } from 'lucide-react'
import toast from 'react-hot-toast'

interface Role {
  id: string
  name: string
  description?: string
}

interface AdminUserFormData {
  email: string
  password: string
  full_name: string
  role_id: string
}

interface AdminUserFormProps {
  onSuccess: () => void
  onCancel: () => void
}

const AdminUserForm: React.FC<AdminUserFormProps> = ({ onSuccess, onCancel }) => {
  const [formData, setFormData] = useState<AdminUserFormData>({
    email: '',
    password: '',
    full_name: '',
    role_id: ''
  })
  const [roles, setRoles] = useState<Role[]>([])
  const [loading, setLoading] = useState(false)
  const [fetchingRoles, setFetchingRoles] = useState(true)

  // دریافت نقش‌ها از API
  const fetchRoles = async () => {
    try {
      setFetchingRoles(true)
      const token = localStorage.getItem('token')
      if (!token) {
        throw new Error('No authentication token found')
      }

      const response = await fetch('/api/admin/roles', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      
      // فیلتر کردن نقش‌هایی که برای ادمین‌ها مرتبط هستن
      const adminRoles = data.filter((role: Role) => 
        role.name === 'SuperAdmin' || role.name === 'Admin'
      )
      
      setRoles(adminRoles)
      
      // اگر نقش Admin وجود داشت، به عنوان پیش‌فرض انتخاب کن
      const adminRole = adminRoles.find((role: Role) => role.name === 'Admin')
      if (adminRole) {
        setFormData(prev => ({ ...prev, role_id: adminRole.id }))
      }
    } catch (error) {
      console.error('❌ Error fetching roles:', error)
      toast.error('خطا در دریافت نقش‌ها')
      // در صورت خطا، نقش‌های پیش‌فرض رو استفاده کن
      setRoles([
        { id: 'default-admin', name: 'Admin', description: 'Administrator role' },
        { id: 'default-superadmin', name: 'SuperAdmin', description: 'Super Administrator role' }
      ])
    } finally {
      setFetchingRoles(false)
    }
  }

  // اعتبارسنجی فرم
  const validateForm = (): boolean => {
    if (!formData.email.trim()) {
      toast.error('لطفاً ایمیل را وارد کنید')
      return false
    }
    
    // اعتبارسنجی ایمیل
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(formData.email)) {
      toast.error('لطفاً ایمیل معتبر وارد کنید')
      return false
    }
    
    if (!formData.password.trim()) {
      toast.error('لطفاً رمز عبور را وارد کنید')
      return false
    }
    
    if (formData.password.length < 6) {
      toast.error('رمز عبور باید حداقل 6 کاراکتر باشد')
      return false
    }
    
    if (!formData.full_name.trim()) {
      toast.error('لطفاً نام کامل را وارد کنید')
      return false
    }
    
    if (!formData.role_id) {
      toast.error('لطفاً نقش را انتخاب کنید')
      return false
    }
    
    return true
  }

  // ارسال فرم
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }
    
    setLoading(true)
    
    try {
      const token = localStorage.getItem('token')
      if (!token) {
        throw new Error('No authentication token found')
      }

      console.log('📝 Creating admin with data:', formData)
      
      const response = await fetch('/api/admin/admins', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(formData)
      })

      console.log('📤 Response status:', response.status)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ Error response:', errorText)
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`)
      }

      const data = await response.json()
      console.log('✅ Admin created successfully:', data)
      
      toast.success('ادمین جدید با موفقیت ایجاد شد')
      onSuccess()
      
    } catch (error) {
      console.error('❌ Error creating admin:', error)
      toast.error(error instanceof Error ? error.message : 'خطا در ایجاد ادمین جدید')
    } finally {
      setLoading(false)
    }
  }

  // مدیریت تغییرات فرم
  const handleInputChange = (field: keyof AdminUserFormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  // لود نقش‌ها در اولین رندر
  useEffect(() => {
    fetchRoles()
  }, [])

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserPlus className="h-5 w-5" />
          افزودن ادمین جدید
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* ایمیل */}
          <div className="space-y-2">
            <Label htmlFor="email">ایمیل *</Label>
            <Input
              id="email"
              type="email"
              placeholder="admin@example.com"
              value={formData.email}
              onChange={(e) => handleInputChange('email', e.target.value)}
              disabled={loading}
              required
            />
          </div>

          {/* رمز عبور */}
          <div className="space-y-2">
            <Label htmlFor="password">رمز عبور *</Label>
            <Input
              id="password"
              type="password"
              placeholder="حداقل 6 کاراکتر"
              value={formData.password}
              onChange={(e) => handleInputChange('password', e.target.value)}
              disabled={loading}
              required
            />
          </div>

          {/* نام کامل */}
          <div className="space-y-2">
            <Label htmlFor="full_name">نام کامل *</Label>
            <Input
              id="full_name"
              type="text"
              placeholder="نام و نام خانوادگی"
              value={formData.full_name}
              onChange={(e) => handleInputChange('full_name', e.target.value)}
              disabled={loading}
              required
            />
          </div>

          {/* نقش */}
          <div className="space-y-2">
            <Label htmlFor="role">نقش *</Label>
            <Select
              value={formData.role_id}
              onValueChange={(value) => handleInputChange('role_id', value)}
              disabled={loading || fetchingRoles}
            >
              <SelectTrigger id="role">
                <SelectValue placeholder="انتخاب نقش" />
              </SelectTrigger>
              <SelectContent>
                {fetchingRoles ? (
                  <SelectItem value="loading" disabled>
                    در حال بارگذاری...
                  </SelectItem>
                ) : roles.length > 0 ? (
                  roles.map((role) => (
                    <SelectItem key={role.id} value={role.id}>
                      {role.name === 'SuperAdmin' ? 'ادمین ارشد' : 
                       role.name === 'Admin' ? 'ادمین' : role.name}
                    </SelectItem>
                  ))
                ) : (
                  <SelectItem value="no-roles" disabled>
                    نقشی یافت نشد
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>

          {/* دکمه‌ها */}
          <div className="flex gap-3 justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              disabled={loading}
            >
              لغو
            </Button>
            <Button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  در حال ایجاد...
                </>
              ) : (
                <>
                  <UserPlus className="h-4 w-4" />
                  ایجاد ادمین
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

export default AdminUserForm