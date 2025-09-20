'use client'

import React, { useState, useEffect } from 'react'
import { Modal } from './ui/modal'
import { Form, FormField, FormSelectField, FormActions, SubmitButton, CancelButton } from './ui/form'
import { UserPlus, Shield, Mail, Lock, User } from 'lucide-react'
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

interface AdminUserModalEnhancedProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

const AdminUserModalEnhanced: React.FC<AdminUserModalEnhancedProps> = ({ 
  isOpen, 
  onClose, 
  onSuccess 
}) => {
  const [formData, setFormData] = useState<AdminUserFormData>({
    email: '',
    password: '',
    full_name: '',
    role_id: ''
  })
  const [roles, setRoles] = useState<Role[]>([])
  const [loading, setLoading] = useState(false)
  const [fetchingRoles, setFetchingRoles] = useState(true)
  const [errors, setErrors] = useState<Partial<AdminUserFormData>>({})

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
      
      // فیلتر نقش‌هایی که برای ادمین‌ها مرتبط هستن
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
    const newErrors: Partial<AdminUserFormData> = {}
    
    if (!formData.email.trim()) {
      newErrors.email = 'لطفاً ایمیل را وارد کنید'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'لطفاً ایمیل معتبر وارد کنید'
    }
    
    if (!formData.password.trim()) {
      newErrors.password = 'لطفاً رمز عبور را وارد کنید'
    } else if (formData.password.length < 6) {
      newErrors.password = 'رمز عبور باید حداقل 6 کاراکتر باشد'
    }
    
    if (!formData.full_name.trim()) {
      newErrors.full_name = 'لطفاً نام کامل را وارد کنید'
    }
    
    if (!formData.role_id) {
      newErrors.role_id = 'لطفاً نقش را انتخاب کنید'
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
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
      
      // ریست فرم
      setFormData({
        email: '',
        password: '',
        full_name: '',
        role_id: ''
      })
      setErrors({})
      
      // بستن مودال و اجرای callback موفقیت
      onSuccess()
      onClose()
      
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
    // پاک کردن خطای مربوطه
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }))
    }
  }

  // لود نقش‌ها در اولین رندر
  useEffect(() => {
    if (isOpen) {
      fetchRoles()
    }
  }, [isOpen])

  // آماده‌سازی گزینه‌های نقش
  const roleOptions = roles.map((role) => ({
    value: role.id,
    label: role.name === 'SuperAdmin' ? 'ادمین ارشد' : 
           role.name === 'Admin' ? 'ادمین' : role.name
  }))

  // طراحی جذاب با آیکون‌ها و رنگ‌های حرفه‌ای
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg">
            <UserPlus className="h-6 w-6 text-white" />
          </div>
          <div>
            <h3 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              افزودن ادمین جدید
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              اطلاعات ادمین جدید را وارد کنید
            </p>
          </div>
        </div>
      }
      size="md"
      className="!p-0"
    >
      <div className="p-6 bg-gradient-to-br from-slate-50 to-blue-50">
        <Form onSubmit={handleSubmit} className="space-y-6">
          {/* ایمیل با آیکون */}
          <FormField
            label="ایمیل"
            name="email"
            type="email"
            placeholder="admin@example.com"
            value={formData.email}
            onChange={(value) => handleInputChange('email', value)}
            error={errors.email}
            required
            disabled={loading}
            className="[&>div>input]:pl-10"
          >
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Mail className="h-5 w-5 text-gray-400" />
            </div>
          </FormField>

          {/* رمز عبور با آیکون */}
          <FormField
            label="رمز عبور"
            name="password"
            type="password"
            placeholder="حداقل 6 کاراکتر"
            value={formData.password}
            onChange={(value) => handleInputChange('password', value)}
            error={errors.password}
            required
            disabled={loading}
            className="[&>div>input]:pl-10"
          >
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Lock className="h-5 w-5 text-gray-400" />
            </div>
          </FormField>

          {/* نام کامل با آیکون */}
          <FormField
            label="نام کامل"
            name="full_name"
            type="text"
            placeholder="نام و نام خانوادگی"
            value={formData.full_name}
            onChange={(value) => handleInputChange('full_name', value)}
            error={errors.full_name}
            required
            disabled={loading}
            className="[&>div>input]:pl-10"
          >
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <User className="h-5 w-5 text-gray-400" />
            </div>
          </FormField>

          {/* نقش با آیکون */}
          <FormSelectField
            label="نقش"
            name="role"
            value={formData.role_id}
            onChange={(value) => handleInputChange('role_id', value)}
            options={roleOptions}
            placeholder="انتخاب نقش"
            required
            disabled={loading}
            loading={fetchingRoles}
            loadingText="در حال بارگذاری نقش‌ها..."
            emptyText="نقشی یافت نشد"
            className="[&>div>div>button]:pl-10"
          >
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Shield className="h-5 w-5 text-gray-400" />
            </div>
          </FormSelectField>

          {/* دکمه‌ها با طراحی جذاب */}
          <FormActions className="mt-8">
            <CancelButton 
              onClick={onClose}
              disabled={loading}
              className="hover:bg-gray-100 transition-colors"
            >
              انصراف
            </CancelButton>
            <SubmitButton
              loading={loading}
              loadingText="در حال ایجاد ادمین..."
              className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg hover:shadow-xl transition-all"
            >
              <UserPlus className="h-4 w-4" />
              ایجاد ادمین
            </SubmitButton>
          </FormActions>
        </Form>
      </div>
    </Modal>
  )
}

export default AdminUserModalEnhanced