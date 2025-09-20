"use client"

import React, { useState, useEffect } from "react"
import { useAuth } from "../context/AuthContext"
import { knowledgeBaseService, type Article } from "../services/knowledgeBaseService"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card"
import { Badge } from "../components/ui/badge"
import AdminFileUpload from "../components/AdminFileUpload"
import toast from "react-hot-toast"
import { Plus, Edit, Trash2, Eye, Search, ChevronLeft, ChevronRight, Upload } from "lucide-react"

// Article Form Component
const ArticleForm: React.FC<{
  article?: Article
  onSave: () => void
  onCancel: () => void
}> = ({ article, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    title: article?.title || "",
    content: article?.content || "",
    summary: article?.summary || "",
    category_id: article?.category_id || "",
    tags: article?.tags?.join(", ") || ""
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const data = {
        title: formData.title,
        content: formData.content,
        summary: formData.summary || undefined,
        category_id: formData.category_id || undefined,
        tags: formData.tags.split(",").map(tag => tag.trim()).filter(Boolean)
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
              value={formData.tags}
              onChange={(e) => setFormData(prev => ({ ...prev, tags: e.target.value }))}
              placeholder="برچسب1, برچسب2"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">محتوا *</label>
            <textarea
              value={formData.content}
              onChange={(e) => setFormData(prev => ({ ...prev, content: e.target.value }))}
              rows={10}
              required
              className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="محتوای مقاله را وارد کنید (TinyMCE در آینده اضافه خواهد شد)"
            />
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

const SuperAdminKnowledgeBasePage: React.FC = () => {
  const { user, isSuperAdmin, loading: authLoading } = useAuth()
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [currentPage, setCurrentPage] = useState(1)
  const [showForm, setShowForm] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [editingArticle, setEditingArticle] = useState<Article | undefined>()
  const [deleteConfirm, setDeleteConfirm] = useState<{ show: boolean; article?: Article }>({ show: false })
  const itemsPerPage = 10

  useEffect(() => {
    console.log("SuperAdminKnowledgeBasePage useEffect:", {
      authLoading,
      isSuperAdmin,
      user: user?.email,
      hasToken: !!localStorage.getItem('token')
    });
    
    // فقط اگر احراز هویت کامل شده و کاربر SuperAdmin باشه، دیتا رو لود کن
    if (!authLoading && isSuperAdmin && user) {
      console.log("✅ Conditions met, loading articles...");
      loadArticles()
    } else {
      console.log("⏳ Waiting for auth to complete...");
    }
  }, [isSuperAdmin, authLoading, user])

  const loadArticles = async () => {
    setLoading(true)
    try {
      console.log("Starting to load articles...")
      console.log("Token available:", !!localStorage.getItem("token"))
      
      const data = await knowledgeBaseService.getAllArticles()
      console.log("Raw response data:", data)
      console.log("Data type:", typeof data)
      console.log("Is Array:", Array.isArray(data))
      
      // بررسی دقیق داده‌ها
      if (data === null || data === undefined) {
        console.error("No data received from API")
        setArticles([])
        toast.error("هیچ داده‌ای از سرور دریافت نشد")
      } else if (Array.isArray(data)) {
        console.log("Received array with length:", data.length)
        setArticles(data)
      } else {
        console.error("Expected array but got:", typeof data, data)
        setArticles([])
        toast.error("فرمت داده‌های دریافتی نادرست است")
      }
    } catch (error: any) {
      console.error("Error loading articles:", error)
      console.error("Error details:", error.message)
      console.error("Error response:", error.response)
      
      if (error.response?.status === 401) {
        toast.error("خطای احراز هویت - لطفاً دوباره وارد شوید")
      } else if (error.response?.status === 403) {
        toast.error("دسترسی غیرمجاز - شما اجازه دسترسی به این بخش را ندارید")
      } else {
        toast.error("خطا در بارگذاری مقالات")
      }
      setArticles([])
    } finally {
      setLoading(false)
    }
  }

  const handlePublish = async (article: Article) => {
    try {
      await knowledgeBaseService.publishArticle(article.id, "public")
      toast.success("مقاله منتشر شد")
      loadArticles()
    } catch (error: any) {
      console.error("Error publishing article:", error)
      toast.error(error.message || "خطا در انتشار مقاله")
    }
  }

  const handleDelete = (article: Article) => {
    setDeleteConfirm({ show: true, article })
  }

  const confirmDelete = async () => {
    if (!deleteConfirm.article) return

    try {
      await knowledgeBaseService.deleteArticle(deleteConfirm.article.id)
      toast.success("مقاله حذف شد")
      loadArticles()
    } catch (error: any) {
      toast.error("خطا در حذف مقاله")
    } finally {
      setDeleteConfirm({ show: false })
    }
  }

  const cancelDelete = () => {
    setDeleteConfirm({ show: false })
  }

  const filteredArticles = Array.isArray(articles) ? articles.filter(article =>
    article.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    article.content.toLowerCase().includes(searchTerm.toLowerCase())
  ) : []

  const paginatedArticles = filteredArticles.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  )

  const totalPages = Math.ceil(filteredArticles.length / itemsPerPage)

  if (!isSuperAdmin) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">دسترسی غیرمجاز</h2>
        <p className="text-gray-600">فقط سوپر ادمین‌ها می‌توانند به این صفحه دسترسی داشته باشند.</p>
      </div>
    )
  }

  return (
    <div className="p-6" dir="rtl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">پایگاه دانش</h1>
        <p className="text-gray-600">این صفحه فقط برای سوپر ادمین‌ها قابل دسترسی است.</p>
      </div>

      {/* Form */}
      {showForm && (
        <ArticleForm
          article={editingArticle}
          onSave={() => {
            setShowForm(false)
            setEditingArticle(undefined)
            loadArticles()
          }}
          onCancel={() => {
            setShowForm(false)
            setEditingArticle(undefined)
          }}
        />
      )}

      {/* Upload Form */}
      {showUpload && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>آپلود فایل</CardTitle>
          </CardHeader>
          <CardContent>
            <AdminFileUpload
              onUploadSuccess={(data) => {
                toast.success(`فایل ${data.filename} با موفقیت آپلود شد!`)
                setShowUpload(false)
              }}
              onClose={() => setShowUpload(false)}
            />
          </CardContent>
        </Card>
      )}

      {/* Delete Confirmation Dialog */}
      {deleteConfirm.show && deleteConfirm.article && (
        <Card className="mb-6 border-red-200 bg-red-50">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="text-red-500 text-xl">⚠️</div>
              <div>
                <h3 className="text-lg font-semibold text-red-900">تأیید حذف مقاله</h3>
                <p className="text-red-700 mt-1">
                  آیا مطمئن هستید که می‌خواهید مقاله "{deleteConfirm.article.title}" را حذف کنید؟
                  این عملیات قابل بازگشت نیست.
                </p>
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={cancelDelete}
                className="border-gray-300"
              >
                لغو
              </Button>
              <Button
                variant="destructive"
                onClick={confirmDelete}
              >
                حذف مقاله
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex gap-2">
          <Button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            افزودن مقاله جدید
          </Button>
          <Button
            onClick={() => setShowUpload(true)}
            variant="outline"
            className="flex items-center gap-2"
          >
            <Upload className="h-4 w-4" />
            آپلود فایل
          </Button>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="جستجو در مقالات..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 pr-4 w-64"
            />
          </div>
        </div>
      </div>

      {/* Articles Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center">در حال بارگذاری...</div>
          ) : paginatedArticles.length === 0 ? (
            <div className="p-8 text-center">
              <div className="text-6xl mb-4">📚</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">مقاله‌ای یافت نشد</h3>
              <p className="text-gray-500">
                {searchTerm ? "هیچ مقاله‌ای با این عبارت یافت نشد." : "هنوز مقاله‌ای ایجاد نشده است."}
              </p>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>عنوان</TableHead>
                    <TableHead>دسته‌بندی</TableHead>
                    <TableHead>وضعیت</TableHead>
                    <TableHead>تاریخ ایجاد</TableHead>
                    <TableHead>عملیات</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedArticles.map((article) => (
                    <TableRow key={article.id}>
                      <TableCell className="font-medium">{article.title}</TableCell>
                      <TableCell>{article.category_id || "-"}</TableCell>
                      <TableCell>
                        <Badge variant={article.status === "PUBLISHED" ? "default" : "secondary"}>
                          {article.status === "PUBLISHED" ? "منتشر شده" : "پیش‌نویس"}
                        </Badge>
                      </TableCell>
                      <TableCell>{new Date(article.created_at).toLocaleDateString("fa-IR")}</TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setEditingArticle(article)
                              setShowForm(true)
                            }}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          {article.status === "DRAFT" && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handlePublish(article)}
                            >
                              انتشار
                            </Button>
                          )}
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => handleDelete(article)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex justify-center items-center gap-2 p-4 border-t">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>

                  <span className="text-sm text-gray-600">
                    صفحه {currentPage} از {totalPages}
                  </span>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    disabled={currentPage === totalPages}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default SuperAdminKnowledgeBasePage