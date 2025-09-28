"use client"

import React, { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { knowledgeBaseService, type Article } from "../services/knowledgeBaseService"
import { adminService } from "../services/adminService"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card"
import { Badge } from "../components/ui/badge"
import toast from "react-hot-toast"
import { Plus, Edit, Trash2, Search, ChevronLeft, ChevronRight, Upload } from "lucide-react"

const SuperAdminKnowledgeBasePage: React.FC = () => {
  const navigate = useNavigate()
  const { user, isSuperAdmin, loading: authLoading } = useAuth()
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [currentPage, setCurrentPage] = useState(1)
  const [deleteConfirm, setDeleteConfirm] = useState<{ show: boolean; article?: Article }>({ show: false })
  const itemsPerPage = 10

  useEffect(() => {
    // فقط اگر احراز هویت کامل شده و کاربر SuperAdmin باشه، دیتا رو لود کن
    if (!authLoading && isSuperAdmin && user) {
      loadArticles()
    }
  }, [isSuperAdmin, authLoading, user])

  const loadArticles = async () => {
    setLoading(true)
    try {
      
      const data = await knowledgeBaseService.getAllArticles()
      
      // بررسی دقیق داده‌ها
      if (data === null || data === undefined) {
        setArticles([])
        toast.error("هیچ داده‌ای از سرور دریافت نشد")
      } else if (Array.isArray(data)) {
        setArticles(data)
      } else {
        setArticles([])
        toast.error("فرمت داده‌های دریافتی نادرست است")
      }
    } catch (error: any) {
      toast.error("خطا در بارگذاری مقالات")
      
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

  const handleViewContent = (article: Article) => {
    window.location.href = `/super-admin/knowledge-base/articles/${article.id}`
  }

  // پاک کردن کدهای modal قدیمی که دیگر استفاده نمی‌شوند
  // const [showContentModal, setShowContentModal] = useState(false)
  // const [selectedArticle, setSelectedArticle] = useState<Article | undefined>()

  // const closeContentModal = () => {
  //   setShowContentModal(false)
  //   setSelectedArticle(undefined)
  // }

  const filteredArticles = Array.isArray(articles) ? articles.filter(article =>
    article.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    article.content_markdown.toLowerCase().includes(searchTerm.toLowerCase())
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
            onClick={() => navigate("/super-admin/knowledge-base/add")}
            className="flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            افزودن مقاله جدید
          </Button>
          <Button
            onClick={() => navigate("/super-admin/knowledge-base/upload")}
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
                    <TableHead>سطح دسترسی</TableHead>
                    <TableHead>تاریخ ایجاد</TableHead>
                    <TableHead>عملیات</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedArticles.map((article) => (
                    <TableRow key={article.id}>
                      <TableCell className="font-medium">
                        <button
                          onClick={() => handleViewContent(article)}
                          className="text-blue-600 hover:text-blue-800 hover:underline text-right"
                        >
                          {article.title}
                        </button>
                      </TableCell>
                      <TableCell>{article.category?.name || "-"}</TableCell>
                      <TableCell>
                        {(() => {
                          const badge = adminService.getStatusBadge(article.status);
                          return (
                            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${badge.bgColor} ${badge.color}`}>
                              <span className="mr-1">{badge.icon}</span>
                              {badge.text}
                            </span>
                          );
                        })()}
                      </TableCell>
                      <TableCell>
                        {(() => {
                          const badge = adminService.getVisibilityBadge(article.visibility);
                          return (
                            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${badge.bgColor} ${badge.color}`}>
                              <span className="mr-1">{badge.icon}</span>
                              {badge.text}
                            </span>
                          );
                        })()}
                      </TableCell>
                      <TableCell>{new Date(article.created_at).toLocaleDateString("fa-IR")}</TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => navigate(`/super-admin/knowledge-base/edit/${article.id}`)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          {article.status === "draft" && (
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