"use client"

import React, { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { knowledgeBaseService } from "../services/knowledgeBaseService"
import { adminService, type GeneratedMetadata } from "../services/adminService"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card"
import ArticleContentEditor from "../components/ArticleContentEditor"
import toast from "react-hot-toast"
import { Sparkles, ArrowRight, Save, X } from "lucide-react"

const SuperAdminAddArticlePage: React.FC = () => {
  const navigate = useNavigate()
  const { user, isSuperAdmin, loading: authLoading } = useAuth()

  const [formData, setFormData] = useState({
    title: "",
    content_markdown: "",
    summary: "",
    category_id: "",
    tag_names: "",
    status: "draft",
    visibility: ""
  })
  const [categories, setCategories] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [aiLoading, setAiLoading] = useState(false)
  const [markdownConverting, setMarkdownConverting] = useState(false)

  useEffect(() => {
    // فقط یک بار دسته‌بندی‌ها را بارگذاری کن
    if (!authLoading && isSuperAdmin && user) {
      console.log("SuperAdminAddArticlePage: Loading categories for SuperAdmin")
      loadCategories()
    }
  }, [authLoading, isSuperAdmin, user])

  const loadCategories = async () => {
    try {
      const cats = await knowledgeBaseService.getAllCategoriesForAdmin()
      setCategories(Array.isArray(cats) ? cats : [])
    } catch (error) {
      console.error("Error loading categories:", error)
      setCategories([])
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const data = {
        title: formData.title,
        content_markdown: formData.content_markdown,
        content_html: undefined,
        summary: formData.summary || undefined,
        category_id: formData.category_id || undefined,
        tag_names: formData.tag_names.split(",").map(tag => tag.trim()).filter(Boolean),
        status: formData.status as "draft" | "published" | "archived",
        visibility: formData.status === "published" ? (formData.visibility as "public" | "customer" | "internal") : undefined
        }
      await knowledgeBaseService.createArticle(data)
      toast.success("مقاله با موفقیت ایجاد شد")
      navigate("/super-admin/knowledge-base")
    } catch (error: any) {
      toast.error(error.message || "خطا در ایجاد مقاله")
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateMetadata = async () => {
    if (!formData.title.trim() || !formData.content_markdown.trim()) {
      toast.error("لطفاً عنوان و محتوای مقاله را وارد کنید")
      return
    }

    setAiLoading(true)
    try {
      const metadata: GeneratedMetadata = await adminService.generateArticleMetadata(
        formData.title,
        formData.content_markdown
      )

      // تبدیل نام دسته‌بندی به ObjectId
      let categoryId = ""
      if (metadata.suggested_category) {
        const category = categories.find(cat => 
          cat.name === metadata.suggested_category || 
          cat.name.includes(metadata.suggested_category) ||
          metadata.suggested_category.includes(cat.name)
        )
        if (category) {
          categoryId = category.id
        }
      }

      setFormData(prev => ({
        ...prev,
        summary: metadata.summary,
        tag_names: metadata.tags.join(", "),
        category_id: categoryId || prev.category_id // اگر دسته‌بندی پیدا نشد، مقدار قبلی را نگه دار
      }))

      toast.success("متادیتای هوش مصنوعی با موفقیت تولید شد ✨")
    } catch (error: any) {
      console.error("Error generating metadata:", error)
      toast.error(error.message || "خطا در تولید متادیتای هوش مصنوعی")
    } finally {
      setAiLoading(false)
    }
  }

  const handleConvertToMarkdown = async () => {
    if (!formData.content_markdown.trim()) {
      toast.error("لطفاً ابتدا محتوایی وارد کنید")
      return
    }

    setMarkdownConverting(true)
    try {
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
      setMarkdownConverting(false)
    }
  }
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!isSuperAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">دسترسی غیرمجاز</h2>
          <p className="text-gray-600">فقط سوپر ادمین‌ها می‌توانند به این صفحه دسترسی داشته باشند.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8" dir="rtl">
      <div className="max-w-4xl mx-auto px-4">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-4">
            <Button
              variant="outline"
              onClick={() => navigate("/super-admin/knowledge-base")}
              className="flex items-center gap-2"
            >
              <ArrowRight className="h-4 w-4" />
              بازگشت به لیست مقالات
            </Button>
            <h1 className="text-3xl font-bold text-gray-900">ایجاد مقاله جدید</h1>
          </div>
          <p className="text-gray-600">مقاله جدید خود را ایجاد کنید و با هوش مصنوعی متادیتا تولید کنید.</p>
        </div>

        {/* Form */}
        <Card>
          <CardHeader>
            <CardTitle>جزئیات مقاله</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* عنوان */}
              <div>
                <label className="block text-sm font-medium mb-2">عنوان *</label>
                <Input
                  value={formData.title}
                  onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                  required
                  placeholder="عنوان مقاله را وارد کنید"
                  className="text-lg"
                />
              </div>

              {/* خلاصه */}
              <div>
                <label className="block text-sm font-medium mb-2">خلاصه</label>
                <textarea
                  value={formData.summary}
                  onChange={(e) => setFormData(prev => ({ ...prev, summary: e.target.value }))}
                  rows={3}
                  className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="خلاصه مقاله را وارد کنید"
                />
              </div>

              {/* دسته‌بندی */}
              <div>
                <label className="block text-sm font-medium mb-2">دسته‌بندی</label>
                <select
                  value={formData.category_id}
                  onChange={(e) => setFormData(prev => ({ ...prev, category_id: e.target.value }))}
                  className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">انتخاب دسته‌بندی...</option>
                  {Array.isArray(categories) && categories
                    .sort((a, b) => {
                      // مرتب‌سازی: ابتدا ریشه‌ها، سپس زیردسته‌ها
                      const aHasParent = categories.some(c => c.id === a.parent_id);
                      const bHasParent = categories.some(c => c.id === b.parent_id);
                      if (aHasParent && !bHasParent) return 1;
                      if (!aHasParent && bHasParent) return -1;
                      return a.name.localeCompare(b.name);
                    })
                    .map((category) => {
                      const isChild = categories.some(c => c.id === category.parent_id);
                      const indent = isChild ? '  └── ' : '';
                      return (
                        <option key={category.id} value={category.id}>
                          {indent}{category.name} {category.is_public ? '' : '(خصوصی)'}
                        </option>
                      );
                    })}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  دسته‌بندی‌های خصوصی با (خصوصی) مشخص شده‌اند • زیردسته‌ها با indentation نمایش داده می‌شوند
                </p>
              </div>

              {/* برچسب‌ها */}
              <div>
                <label className="block text-sm font-medium mb-2">برچسب‌ها</label>
                <Input
                  value={formData.tag_names}
                  onChange={(e) => setFormData(prev => ({ ...prev, tag_names: e.target.value }))}
                  placeholder="برچسب1, برچسب2"
                />
              </div>

              {/* وضعیت مقاله */}
              <div>
                <label className="block text-sm font-medium mb-2">وضعیت مقاله *</label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData(prev => ({ ...prev, status: e.target.value }))}
                  className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="draft">پیش‌نویس</option>
                  <option value="published">منتشر شده</option>
                  <option value="archived">بایگانی شده</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  وضعیت مقاله را انتخاب کنید. توجه: انتشار فقط برای سوپر ادمین ممکن است.
                </p>
              </div>

              {/* سطح دسترسی (فقط برای مقالات منتشر شده) */}
              {formData.status === "published" && (
                <div>
                  <label className="block text-sm font-medium mb-2">سطح دسترسی *</label>
                  <select
                    value={formData.visibility}
                    onChange={(e) => setFormData(prev => ({ ...prev, visibility: e.target.value }))}
                    className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">انتخاب کنید...</option>
                    <option value="PUBLIC">عمومی</option>
                    <option value="CUSTOMER">مشتری</option>
                    <option value="INTERNAL">داخلی (فقط ادمین‌ها)</option>
                  </select>
                  <div className="mt-2 space-y-1">
                    <p className="text-xs text-gray-500">
                      تعیین کنید مقاله برای چه کسانی قابل مشاهده باشد:
                    </p>
                    <div className="text-xs text-gray-600 space-y-1">
                      {["public", "customer", "internal"].map((vis) => {
                        const badge = adminService.getVisibilityBadge(vis);
                        return (
                          <div key={vis} className="flex items-center">
                            <span className="mr-2">{badge.icon}</span>
                            <span className={`${badge.color} font-medium`}>{badge.text}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* محتوا */}
              <div>
                <label className="block text-sm font-medium mb-2">محتوا *</label>
                <ArticleContentEditor
                  markdownContent={formData.content_markdown}
                  htmlContent=""
                  onMarkdownChange={(content) => setFormData(prev => ({ ...prev, content_markdown: content }))}
                  placeholder="محتوای مقاله را وارد کنید یا متن ساده وارد کرده و دکمه 'تبدیل به Markdown' را کلیک کنید..."
                />
                <p className="text-xs text-gray-500 mt-1">
                  💡 نکته: می‌توانید متن ساده وارد کرده و با کلیک روی دکمه "🤖 تبدیل به Markdown" آن را به فرمت ساختاریافته تبدیل کنید
                </p>
              </div>

              {/* AI Actions */}
              <div className="flex justify-center gap-4 mb-6">
                <Button
                  type="button"
                  onClick={handleConvertToMarkdown}
                  disabled={markdownConverting || !formData.content_markdown.trim()}
                  variant="outline"
                  className="flex items-center gap-2 bg-gradient-to-r from-blue-50 to-cyan-50 hover:from-blue-100 hover:to-cyan-100 border-blue-200"
                >
                  {markdownConverting ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                      در حال تبدیل...
                    </>
                  ) : (
                    <>
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 4V2a1 1 0 011-1h8a1 1 0 011 1v2m-9 0h10m-10 0v16a2 2 0 002 2h6a2 2 0 002-2V4" />
                      </svg>
                      🤖 تبدیل به Markdown
                    </>
                  )}
                </Button>
                <Button
                  type="button"
                  onClick={handleGenerateMetadata}
                  disabled={aiLoading || !formData.title.trim() || !formData.content_markdown.trim()}
                  variant="outline"
                  className="flex items-center gap-2 bg-gradient-to-r from-purple-50 to-blue-50 hover:from-purple-100 hover:to-blue-100 border-purple-200"
                >
                  <Sparkles className="h-4 w-4 text-purple-600" />
                  {aiLoading ? "در حال تولید..." : "تولید متادیتا ✨"}
                </Button>
              </div>

              {/* Actions */}
              <div className="flex gap-4 justify-end">
                <Button type="submit" disabled={loading} className="flex items-center gap-2">
                  <Save className="h-4 w-4" />
                  {loading ? "در حال ذخیره..." : "ایجاد مقاله"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate("/super-admin/knowledge-base")}
                  className="flex items-center gap-2"
                >
                  <X className="h-4 w-4" />
                  لغو
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default SuperAdminAddArticlePage
