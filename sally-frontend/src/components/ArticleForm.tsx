"use client"

import React, { useState, useEffect } from "react"
import { knowledgeBaseService, type Article, type Category } from "../services/knowledgeBaseService"
import { adminService, type GeneratedMetadata } from "../services/adminService"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card"
import ArticleContentEditor from "./ArticleContentEditor"
import toast from "react-hot-toast"
import { Sparkles } from "lucide-react"

interface ArticleFormProps {
  article?: Article
  onSave: () => void
  onCancel: () => void
}

const ArticleForm: React.FC<ArticleFormProps> = ({ article, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    title: article?.title || "",
    content_markdown: article?.content_markdown || "",
    summary: article?.summary || "",
    category_id: article?.category?.id || "",
    tag_names: article?.tags?.map(tag => tag.name).join(", ") || "",
    status: article?.status?.toLowerCase() || "draft",
    visibility: article?.visibility || "public"
  })
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)
  const [aiLoading, setAiLoading] = useState(false)
  const [markdownConverting, setMarkdownConverting] = useState(false)

  useEffect(() => {
    loadCategories()
  }, [])

  const loadCategories = async () => {
    try {
      const cats = await knowledgeBaseService.getCategories()
      setCategories(Array.isArray(cats) ? cats : [])
    } catch (error) {
      console.error("Error loading categories:", error)
      setCategories([]) // Set to empty array on error
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const data = {
        title: formData.title,
        content_markdown: formData.content_markdown,
        content_html: undefined, // Will be generated from markdown
        summary: formData.summary || undefined,
        category_id: formData.category_id || undefined,
        tag_names: formData.tag_names.split(",").map(tag => tag.trim()).filter(Boolean),
        status: formData.status as "draft" | "published" | "archived",
        visibility: formData.status === "published" ? (formData.visibility as "public" | "customer" | "internal") : undefined
      }

      if (article) {
        await knowledgeBaseService.updateArticle(article.id, data)
        toast.success("مقاله با موفقیت بروزرسانی شد")
      } else {
        await knowledgeBaseService.createArticle(data)
        toast.success("مقاله با موفقیت ایجاد شد")
      }
      onSave()
    } catch (error: any) {
      toast.error(error.message || "خطا در ذخیره مقاله")
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

      // بروزرسانی فرم با متادیتای تولید شده
      setFormData(prev => ({
        ...prev,
        summary: metadata.summary,
        tag_names: metadata.tags.join(", "),
        category_id: metadata.suggested_category
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

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle>{article ? "ویرایش مقاله" : "ایجاد مقاله جدید"}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">عنوان *</label>
            <Input
              value={formData.title}
              onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
              required
              placeholder="عنوان مقاله را وارد کنید"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">خلاصه</label>
            <textarea
              value={formData.summary}
              onChange={(e) => setFormData(prev => ({ ...prev, summary: e.target.value }))}
              rows={3}
              className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="خلاصه مقاله را وارد کنید"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">دسته‌بندی</label>
            <select
              value={formData.category_id}
              onChange={(e) => setFormData(prev => ({ ...prev, category_id: e.target.value }))}
              className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">انتخاب دسته‌بندی...</option>
              {Array.isArray(categories) && categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">برچسب‌ها</label>
            <Input
              value={formData.tag_names}
              onChange={(e) => setFormData(prev => ({ ...prev, tag_names: e.target.value }))}
              placeholder="برچسب1, برچسب2"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">وضعیت مقاله *</label>
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

          {formData.status === "published" && (
            <div>
              <label className="block text-sm font-medium mb-1">سطح دسترسی *</label>
              <select
                value={formData.visibility}
                onChange={(e) => setFormData(prev => ({ ...prev, visibility: e.target.value as "public" | "customer" | "internal" }))}
                className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">انتخاب کنید...</option>
                <option value="public">عمومی</option>
                <option value="customer">مشتری</option>
                <option value="internal">داخلی (فقط ادمین‌ها)</option>
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

          <div>
            <label className="block text-sm font-medium mb-1">محتوا *</label>
            <ArticleContentEditor
              markdownContent={formData.content_markdown}
              htmlContent={article?.content_html}
              onMarkdownChange={(content) => setFormData(prev => ({ ...prev, content_markdown: content }))}
              placeholder="محتوای مقاله را وارد کنید یا متن ساده وارد کرده و دکمه 'تبدیل به Markdown' را کلیک کنید..."
            />
            <p className="text-xs text-gray-500 mt-1">
              💡 نکته: می‌توانید متن ساده وارد کرده و با کلیک روی دکمه "🤖 تبدیل به Markdown" آن را به فرمت ساختاریافته تبدیل کنید
            </p>
          </div>

          {/* AI Actions */}
          <div className="flex justify-center gap-4 mb-4">
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

          <div className="flex gap-2">
            <Button type="submit" disabled={loading}>
              {loading ? "در حال ذخیره..." : (article ? "بروزرسانی" : "ایجاد")}
            </Button>
            <Button type="button" variant="outline" onClick={onCancel}>
              لغو
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

export default ArticleForm
