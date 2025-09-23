"use client"

import { useState, useRef } from "react"
import { useAuth } from "../context/AuthContext"
import { toast } from "react-hot-toast"
import { knowledgeBaseService, FileUploadResponse } from "../services/knowledgeBaseService"

interface AdminArticleFormProps {
  onArticleCreated?: () => void
}

const AdminArticleForm: React.FC<AdminArticleFormProps> = ({ onArticleCreated }) => {
  const { user } = useAuth()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [formData, setFormData] = useState({
    title: "",
    content_markdown: "",
    summary: "",
    tag_names: "",
    status: "draft",
    visibility: ""
  })
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!user || (user.role !== "SuperAdmin" && user.role !== "Admin")) {
      toast.error("فقط ادمین‌ها می‌توانند مقاله ایجاد کنند")
      return
    }

    setLoading(true)
    try {
      await knowledgeBaseService.createArticle({
        title: formData.title,
        content_markdown: formData.content_markdown,
        summary: formData.summary || undefined,
        tag_names: formData.tag_names.split(",").map(tag => tag.trim()).filter(Boolean),
        status: formData.status as "draft" | "published" | "archived",
        visibility: formData.status === "published" ? (formData.visibility as "public" | "customer" | "internal") : undefined
      })

      toast.success("مقاله با موفقیت ایجاد شد!")
      
      // Reset form
      setFormData({
        title: "",
        content_markdown: "",
        summary: "",
        tag_names: "",
        status: "draft",
        visibility: ""
      })

      onArticleCreated?.()
    } catch (error: any) {
      toast.error(error.message || "خطا در ایجاد مقاله")
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }))
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      const result: FileUploadResponse = await knowledgeBaseService.uploadAndConvertFile(file)
      
      if (result.success) {
        setFormData(prev => ({
          ...prev,
          title: result.title,
          content_markdown: result.markdown_content,
          summary: result.summary,
          tag_names: result.suggested_tags.join(", "),
          status: "draft",
          visibility: ""
        }))
        toast.success("فایل با موفقیت آپلود و تبدیل شد!")
      } else {
        toast.error(result.error || "خطا در آپلود فایل")
      }
    } catch (error: any) {
      toast.error(error.message || "خطا در آپلود فایل")
    } finally {
      setUploading(false)
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
    }
  }

  const triggerFileInput = () => {
    fileInputRef.current?.click()
  }

  if (!user || (user.role !== "SuperAdmin" && user.role !== "Admin")) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
        <p className="text-destructive text-center">فقط ادمین‌ها می‌توانند به این بخش دسترسی داشته باشند</p>
      </div>
    )
  }

  return (
    <div className="card p-6">
      <h2 className="text-xl font-bold mb-4 text-foreground">ایجاد مقاله جدید</h2>
      
      {/* File Upload Section */}
      <div className="mb-6 p-4 border border-dashed border-gray-300 rounded-lg">
        <h3 className="text-lg font-medium mb-2">آپلود و تبدیل فایل</h3>
        <p className="text-sm text-gray-600 mb-3">فایل‌های PDF, Word, Excel, CSV, و متن را آپلود کنید تا به Markdown تبدیل شوند</p>
        
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.doc,.docx,.xlsx,.xls,.csv,.txt"
          onChange={handleFileUpload}
          className="hidden"
        />
        
        <button
          type="button"
          onClick={triggerFileInput}
          disabled={uploading}
          className="btn-secondary w-full"
        >
          {uploading ? "در حال آپلود و تبدیل..." : "انتخاب فایل و تبدیل به Markdown"}
        </button>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            عنوان مقاله *
          </label>
          <input
            type="text"
            name="title"
            value={formData.title}
            onChange={handleChange}
            required
            className="input-field"
            placeholder="عنوان مقاله را وارد کنید"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            خلاصه مقاله
          </label>
          <textarea
            name="summary"
            value={formData.summary}
            onChange={handleChange}
            rows={3}
            className="input-field"
            placeholder="خلاصه مقاله را وارد کنید"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            محتوای مقاله (Markdown) *
          </label>
          <textarea
            name="content_markdown"
            value={formData.content_markdown}
            onChange={handleChange}
            rows={15}
            required
            className="input-field font-mono text-sm"
            placeholder="محتوای markdown مقاله را وارد کنید"
          />
          <p className="text-xs text-gray-500 mt-1">
            از Markdown برای فرمت‌بندی استفاده کنید. پیش‌نمایش در زمان انتشار نمایش داده می‌شود.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            برچسب‌ها (با کاما جدا شوند)
          </label>
          <input
            type="text"
            name="tag_names"
            value={formData.tag_names}
            onChange={handleChange}
            className="input-field"
            placeholder="برچسب1, برچسب2, برچسب3"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            وضعیت مقاله *
          </label>
          <select
            name="status"
            value={formData.status}
            onChange={handleChange}
            required
            className="input-field"
          >
            <option value="draft">پیش‌نویس</option>
            <option value="published">منتشر شده</option>
            <option value="archived">بایگانی شده</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            وضعیت مقاله را انتخاب کنید. توجه: انتشار مستقیم فقط برای سوپر ادمین ممکن است.
          </p>
        </div>

        {formData.status === "published" && (
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">
              سطح دسترسی *
            </label>
            <select
              name="visibility"
              value={formData.visibility}
              onChange={handleChange}
              required
              className="input-field"
            >
              <option value="">انتخاب کنید...</option>
              <option value="public">عمومی</option>
              <option value="customer">مشتری</option>
              <option value="internal">داخلی (فقط ادمین‌ها)</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">
              تعیین کنید مقاله برای چه کسانی قابل مشاهده باشد.
            </p>
          </div>
        )}

        <button
          type="submit"
          disabled={loading || uploading}
          className="btn-primary w-full"
        >
          {loading ? "در حال ایجاد..." : "ایجاد مقاله"}
        </button>
      </form>
    </div>
  )
}

export default AdminArticleForm