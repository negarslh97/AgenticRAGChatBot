"use client"

import { useState, useRef } from "react"
import { useAuth } from "../context/AuthContext"
import { toast } from "react-hot-toast"
import { knowledgeBaseService, FileUploadResponse } from "../services/knowledgeBaseService"
import { Button } from "./ui/button"

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
  const [convertingToMarkdown, setConvertingToMarkdown] = useState(false)

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

  const handleConvertToMarkdown = async () => {
    if (!formData.content_markdown.trim()) {
      toast.error("لطفاً ابتدا محتوایی وارد کنید")
      return
    }

    setConvertingToMarkdown(true)
    try {
      const { adminService } = await import("../services/adminService")
      const result = await adminService.convertTextToMarkdown(
        formData.title || "متن بدون عنوان",
        formData.content_markdown
      )

      if (result.success) {
        setFormData(prev => ({
          ...prev,
          content_markdown: result.markdown_content
        }))
        toast.success(`متن با موفقیت به Markdown تبدیل شد! (${result.original_length} → ${result.markdown_length} کاراکتر)\n💡 به تب "ویرایش" بروید تا محتوای Markdown را ببینید`)
      } else {
        toast.error("خطا در تبدیل متن به Markdown")
      }
    } catch (error: any) {
      if (error.response?.status === 403) {
        toast.error("شما دسترسی لازم برای انتشار مقالات را ندارید. فقط ادمین ارشد می‌تواند مقالات را منتشر کند.")
      } else {
        toast.error(error.message || "خطا در تبدیل متن به Markdown")
      }
    } finally {
      setConvertingToMarkdown(false)
    }
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
        
        <Button
          type="button"
          onClick={triggerFileInput}
          disabled={uploading}
          variant="secondary"
          className="w-full"
        >
          {uploading ? "در حال آپلود و تبدیل..." : "انتخاب فایل و تبدیل به Markdown"}
        </Button>
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
          <div className="flex items-center justify-between mb-1">
            <label className="block text-sm font-medium text-foreground">
              محتوای مقاله (Markdown) *
            </label>
            <button
              type="button"
              onClick={handleConvertToMarkdown}
              disabled={convertingToMarkdown || !formData.content_markdown.trim()}
              className="inline-flex items-center px-3 py-1 text-xs font-medium rounded-md text-blue-700 bg-blue-50 hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {convertingToMarkdown ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-3 w-3 text-blue-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  در حال تبدیل...
                </>
              ) : (
                <>
                  <svg className="mr-1 h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 4V2a1 1 0 011-1h8a1 1 0 011 1v2m-9 0h10m-10 0v16a2 2 0 002 2h6a2 2 0 002-2V4" />
                  </svg>
                  تبدیل به Markdown
                </>
              )}
            </button>
          </div>
          <textarea
            name="content_markdown"
            value={formData.content_markdown}
            onChange={handleChange}
            rows={15}
            required
            className="input-field font-mono text-sm"
            placeholder="محتوای markdown مقاله را وارد کنید یا متن ساده وارد کرده و دکمه 'تبدیل به Markdown' را کلیک کنید"
          />
          <p className="text-xs text-gray-500 mt-1">
            نکته: می‌توانید متن ساده وارد کرده و با کلیک روی دکمه "تبدیل به Markdown" آن را به فرمت ساختاریافته تبدیل کنید
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
              <option value="PUBLIC">عمومی</option>
              <option value="CUSTOMER">مشتری</option>
              <option value="INTERNAL">داخلی (فقط ادمین‌ها)</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">
              تعیین کنید مقاله برای چه کسانی قابل مشاهده باشد.
            </p>
          </div>
        )}

        <Button
          type="submit"
          disabled={loading || uploading}
          className="w-full"
        >
          {loading ? "در حال ایجاد..." : "ایجاد مقاله"}
        </Button>
      </form>
    </div>
  )
}

export default AdminArticleForm