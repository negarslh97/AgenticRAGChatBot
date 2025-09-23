"use client"

import React, { useState } from "react"
import { knowledgeBaseService, type Article } from "../services/knowledgeBaseService"
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
    tag_names: article?.tags?.map(tag => tag.name).join(", ") || ""
  })
  const [loading, setLoading] = useState(false)
  const [aiLoading, setAiLoading] = useState(false)

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
        tag_names: formData.tag_names.split(",").map(tag => tag.trim()).filter(Boolean)
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
            <Input
              value={formData.category_id}
              onChange={(e) => setFormData(prev => ({ ...prev, category_id: e.target.value }))}
              placeholder="شناسه دسته‌بندی"
            />
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
            <label className="block text-sm font-medium mb-1">محتوا *</label>
            <ArticleContentEditor
              markdownContent={formData.content_markdown}
              htmlContent={article?.content_html}
              onMarkdownChange={(content) => setFormData(prev => ({ ...prev, content_markdown: content }))}
              placeholder="محتوای مقاله را وارد کنید..."
            />
          </div>

          {/* AI Metadata Generation Button */}
          <div className="flex justify-center mb-4">
            <Button
              type="button"
              onClick={handleGenerateMetadata}
              disabled={aiLoading || !formData.title.trim() || !formData.content_markdown.trim()}
              variant="outline"
              className="flex items-center gap-2 bg-gradient-to-r from-purple-50 to-blue-50 hover:from-purple-100 hover:to-blue-100 border-purple-200"
            >
              <Sparkles className="h-4 w-4 text-purple-600" />
              {aiLoading ? "در حال تولید..." : "تولید با هوش مصنوعی ✨"}
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
