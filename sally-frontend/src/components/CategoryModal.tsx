'use client'

import React, { useState } from 'react'
import { Modal } from './ui/modal'
import { Form, FormField, FormSelectField, FormActions, SubmitButton, CancelButton } from './ui/form'
import { Plus, Edit3, Palette } from 'lucide-react'
import toast from 'react-hot-toast'
import categoryService, { Category, CategoryCreate, CategoryUpdate } from '../services/categoryService'
import CategoryBadge from './ui/category-badge'

interface CategoryModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  category?: Category | null // For editing
  mode: 'create' | 'edit'
}

const CategoryModal: React.FC<CategoryModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  category,
  mode
}) => {
  const [formData, setFormData] = useState<CategoryCreate | CategoryUpdate>({
    name: category?.name || '',
    slug: category?.slug || '',
    description: category?.description || '',
    color: category?.color || '#4CAF50',
    parent_id: category?.parent_id || null,
    is_public: category?.is_public ?? true
  })
  
  const [loading, setLoading] = useState(false)

  // Predefined color palette
  const predefinedColors = [
    '#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336',
    '#00BCD4', '#FFC107', '#795548', '#607D8B', '#E91E63',
    '#3F51B5', '#009688', '#FF5722', '#8BC34A', '#CDDC39',
    '#FF9800', '#9E9E9E', '#2196F3', '#673AB7', '#FFEB3B'
  ]

  // Generate slug from name
  const generateSlug = (name: string) => {
    return categoryService.generateSlug(name)
  }

  // Handle name change and auto-generate slug
  const handleNameChange = (name: string) => {
    setFormData(prev => ({
      ...prev,
      name,
      slug: mode === 'create' ? generateSlug(name) : prev.slug
    }))
  }

  // Validate form
  const validateForm = (): boolean => {
    const name = formData.name?.trim()
    const slug = formData.slug?.trim()
    const color = formData.color?.trim()
    
    if (!name) {
      toast.error('لطفاً نام دسته‌بندی را وارد کنید')
      return false
    }
    
    if (!slug) {
      toast.error('لطفاً slug را وارد کنید')
      return false
    }
    
    // Validate color format
    if (color && !/^#(?:[0-9a-fA-F]{3}){1,2}$/.test(color)) {
      toast.error('فرمت رنگ معتبر نیست. مثال: #4CAF50')
      return false
    }
    
    return true
  }

  // Submit form
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }
    
    setLoading(true)
    
    try {
      if (mode === 'create') {
        await categoryService.createCategory(formData as CategoryCreate)
        toast.success('دسته‌بندی جدید با موفقیت ایجاد شد')
      } else if (category) {
        await categoryService.updateCategory(category.id, formData as CategoryUpdate)
        toast.success('دسته‌بندی با موفقیت به‌روزرسانی شد')
      }
      
      // Reset form
      setFormData({
        name: '',
        slug: '',
        description: '',
        color: '#4CAF50',
        parent_id: null,
        is_public: true
      })
      
      onSuccess()
      onClose()
      
    } catch (error) {
      console.error('❌ Error saving category:', error)
      toast.error(error instanceof Error ? error.message : 'خطا در ذخیره دسته‌بندی')
    } finally {
      setLoading(false)
    }
  }

  // Reset form when modal opens/closes or category changes
  React.useEffect(() => {
    if (isOpen) {
      setFormData({
        name: category?.name || '',
        slug: category?.slug || '',
        description: category?.description || '',
        color: category?.color || '#4CAF50',
        parent_id: category?.parent_id || null,
        is_public: category?.is_public ?? true
      })
    }
  }, [isOpen, category, mode])

  const title = mode === 'create' ? 'افزودن دسته‌بندی جدید' : 'ویرایش دسته‌بندی'
  const Icon = mode === 'create' ? Plus : Edit3

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-green-500 to-teal-600 rounded-lg">
            <Icon className="h-6 w-6 text-white" />
          </div>
          <div>
            <h3 className="text-xl font-bold bg-gradient-to-r from-green-600 to-teal-600 bg-clip-text text-transparent">
              {title}
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              {mode === 'create' 
                ? 'مشخصات دسته‌بندی جدید را وارد کنید'
                : 'مشخصات دسته‌بندی را ویرایش کنید'
              }
            </p>
          </div>
        </div>
      }
      size="lg"
      className="!p-0"
    >
      <div className="p-6 bg-gradient-to-br from-slate-50 to-green-50">
        <Form onSubmit={handleSubmit} className="space-y-6">
          {/* Name */}
          <FormField
            label="نام دسته‌بندی"
            name="name"
            type="text"
            placeholder="نام دسته‌بندی"
            value={formData.name || ''}
            onChange={(value) => handleNameChange(value)}
            required
            disabled={loading}
          />

          {/* Slug */}
          <FormField
            label="Slug"
            name="slug"
            type="text"
            placeholder="slug-name"
            value={formData.slug || ''}
            onChange={(value) => setFormData(prev => ({ ...prev, slug: value }))}
            required
            disabled={loading}
          />

          {/* Description */}
          <FormField
            label="توضیحات"
            name="description"
            type="textarea"
            placeholder="توضیحات دسته‌بندی (اختیاری)"
            value={formData.description || ''}
            onChange={(value) => setFormData(prev => ({ ...prev, description: value }))}
            disabled={loading}
          />

          {/* Color Picker */}
          <div className="space-y-3">
            <label className="block text-sm font-medium text-gray-700">
              رنگ دسته‌بندی
            </label>
            
            <div className="flex items-center gap-4">
              {/* Custom Color Input */}
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  value={formData.color || '#4CAF50'}
                  onChange={(e) => setFormData(prev => ({ ...prev, color: e.target.value }))}
                  className="w-12 h-10 border border-gray-300 rounded-lg cursor-pointer"
                  disabled={loading}
                />
                <FormField
                  label="کد رنگ"
                  name="color"
                  type="text"
                  placeholder="#4CAF50"
                  value={formData.color || '#4CAF50'}
                  onChange={(value) => setFormData(prev => ({ ...prev, color: value }))}
                  disabled={loading}
                  className="w-32"
                />
              </div>
            </div>
            
            {/* Predefined Colors */}
            <div className="space-y-2">
              <label className="block text-xs text-gray-600">رنگ‌های پیشنهادی:</label>
              <div className="grid grid-cols-10 gap-2">
                {predefinedColors.map((color) => (
                  <button
                    key={color}
                    type="button"
                    className={`w-8 h-8 rounded-lg border-2 transition-all hover:scale-110 ${
                      formData.color === color ? 'border-gray-800 shadow-lg' : 'border-gray-300'
                    }`}
                    style={{ backgroundColor: color }}
                    onClick={() => setFormData(prev => ({ ...prev, color }))}
                    disabled={loading}
                    title={color}
                  />
                ))}
              </div>
            </div>
            
            {/* Color Preview */}
            <div className="mt-3">
              <label className="block text-xs text-gray-600 mb-1">پیش‌نمایش:</label>
              <CategoryBadge color={formData.color || '#4CAF50'}>
                {formData.name || 'نام دسته‌بندی'}
              </CategoryBadge>
            </div>
          </div>

          {/* Public/Private Toggle */}
          <FormSelectField
            label="وضعیت"
            name="visibility"
            value={formData.is_public ? 'public' : 'private'}
            onChange={(value) => setFormData(prev => ({ ...prev, is_public: value === 'public' }))}
            options={[
              { value: 'public', label: 'عمومی' },
              { value: 'private', label: 'خصوصی' }
            ]}
            disabled={loading}
          />

          {/* Submit Buttons */}
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
              loadingText={mode === 'create' ? 'در حال ایجاد...' : 'در حال به‌روزرسانی...'}
              className="bg-gradient-to-r from-green-600 to-teal-600 hover:from-green-700 hover:to-teal-700 text-white shadow-lg hover:shadow-xl transition-all"
            >
              <Icon className="h-4 w-4" />
              {mode === 'create' ? 'ایجاد دسته‌بندی' : 'ذخیره تغییرات'}
            </SubmitButton>
          </FormActions>
        </Form>
      </div>
    </Modal>
  )
}

export default CategoryModal