"use client"

import { useState, useEffect } from "react"
import { useAuth } from "../context/AuthContext"
import AdminArticleForm from "../components/AdminArticleForm"
import AdminFileUpload from "../components/AdminFileUpload"
import { toast } from "react-hot-toast"
import { type Article } from "../services/knowledgeBaseService"
import { adminService } from "../services/adminService"

const AdminPanel: React.FC = () => {
  const { user } = useAuth()
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedStatus, setSelectedStatus] = useState<string>("")
  const [showCreateForm, setShowCreateForm] = useState(false)
  // TODO: Implement article editing functionality
  // const [editingArticle, setEditingArticle] = useState<Article | null>(null)
  const [showUploadForm, setShowUploadForm] = useState(false)
  const [publishModalOpen, setPublishModalOpen] = useState(false)
  const [articleToPublish, setArticleToPublish] = useState<Article | null>(null)
  const [selectedVisibility, setSelectedVisibility] = useState<"public" | "customer" | "internal">("public")

  // useEffect must be called before any conditional returns
  useEffect(() => {
    fetchArticles()
  }, [])

  // Fetch articles data
  const fetchArticles = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/super-admin/kb/articles`, {
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("token")}`
        }
      })

      if (!response.ok) {
        throw new Error("خطا در دریافت مقالات")
      }

      const data = await response.json()
      setArticles(data)
    } catch (error: any) {
      toast.error(error.message || "خطا در دریافت مقالات")
    } finally {
      setLoading(false)
    }
  }

  const publishArticle = async (articleId: string, visibility: "public" | "customer" | "internal") => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/super-admin/kb/articles/${articleId}/publish`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("token")}`
        },
        body: JSON.stringify({
          visibility
        })
      })

      if (!response.ok) {
        throw new Error("خطا در انتشار مقاله")
      }

      await response.json()
      toast.success("مقاله با موفقیت منتشر شد")
      fetchArticles()
      setPublishModalOpen(false)
    } catch (error: any) {
      toast.error(error.message || "خطا در انتشار مقاله")
    }
  }

  const updateArticleStatus = async (articleId: string, status: "draft" | "published" | "archived") => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/super-admin/kb/articles/${articleId}/status`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("token")}`
        },
        body: JSON.stringify({
          status
        })
      })

      if (!response.ok) {
        throw new Error("خطا در تغییر وضعیت مقاله")
      }

      await response.json()
      toast.success("وضعیت مقاله با موفقیت تغییر کرد")
      fetchArticles()
    } catch (error: any) {
      toast.error(error.message || "خطا در تغییر وضعیت مقاله")
    }
  }

  const deleteArticle = async (articleId: string) => {
    if (!window.confirm("آیا از حذف این مقاله مطمئن هستید؟")) {
      return
    }

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/super-admin/kb/articles/${articleId}`, {
        method: "DELETE",
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("token")}`
        }
      })

      if (!response.ok) {
        throw new Error("خطا در حذف مقاله")
      }

      toast.success("مقاله با موفقیت حذف شد")
      fetchArticles()
    } catch (error: any) {
      toast.error(error.message || "خطا در حذف مقاله")
    }
  }

  const handleUploadFile = async (file: File) => {
    try {
      const formData = new FormData()
      formData.append("file", file)

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/super-admin/kb/articles/upload`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("token")}`
        },
        body: formData
      })

      if (!response.ok) {
        throw new Error("خطا در آپلود فایل")
      }

      const data = await response.json()
      toast.success(`فایل ${file.name} با موفقیت آپلود شد و مقاله پیش‌نویس ایجاد شد!`)
      setShowUploadForm(false)
      fetchArticles()
      return data
    } catch (error: any) {
      toast.error(error.message || "خطا در آپلود فایل")
      throw error
    }
  }

  const openPublishModal = (article: Article) => {
    setArticleToPublish(article)
    setPublishModalOpen(true)
  }

  const closePublishModal = () => {
    setPublishModalOpen(false)
    setArticleToPublish(null)
    setSelectedVisibility("public")
  }

  const filteredArticles = selectedStatus
    ? articles.filter(article => article.status === selectedStatus)
    : articles


  const getStatusLabel = (status: string) => {
    switch (status) {
      case "draft": return "پیش‌نویس"
      case "published": return "منتشر شده"
      case "archived": return "بایگانی شده"
      default: return status
    }
  }


  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">پنل مدیریت Sally</h1>
              <p className="text-gray-600 mt-1">مدیریت سیستم و محتوا</p>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-500">
                خوش آمدید، {user?.full_name}
              </span>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                user?.role === "SuperAdmin"
                  ? "bg-purple-100 text-purple-800"
                  : "bg-blue-100 text-blue-800"
              }`}>
                {user?.role === "SuperAdmin" ? "ادمین ارشد" : "ادمین"}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Sidebar */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">منو</h2>
              
              <div className="space-y-2">
                <button
                  onClick={() => setShowUploadForm(!showUploadForm)}
                  className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 transition-colors"
                >
                  {showUploadForm ? "بستن آپلود فایل" : "آپلود فایل"}
                </button>

                <button
                  onClick={() => setShowCreateForm(!showCreateForm)}
                  className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors"
                >
                  {showCreateForm ? "بستن فرم ایجاد" : "ایجاد مقاله جدید"}
                </button>

                <div className="border-t pt-4 mt-4">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">فیلتر وضعیت</h3>
                  <select
                    value={selectedStatus}
                    onChange={(e) => setSelectedStatus(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">همه مقالات</option>
                    <option value="draft">پیش‌نویس</option>
                    <option value="published">منتشر شده</option>
                    <option value="archived">بایگانی شده</option>
                  </select>
                </div>

                <div className="border-t pt-4 mt-4">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">دسترسی سریع</h3>
                  <div className="space-y-1">
                    <button
                      onClick={() => setSelectedStatus("")}
                      className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded"
                    >
                      نمایش همه
                    </button>
                    <button
                      onClick={() => setSelectedStatus("draft")}
                      className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded"
                    >
                      پیش‌نویس‌ها
                    </button>
                    <button
                      onClick={() => setSelectedStatus("published")}
                      className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded"
                    >
                      منتشر شده‌ها
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-2">
            {showUploadForm && (
              <div className="mb-8">
                <AdminFileUpload
                  onUploadSuccess={(file: File) => {
                    handleUploadFile(file)
                  }}
                  onClose={() => setShowUploadForm(false)}
                />
              </div>
            )}

            {showCreateForm && (
              <div className="mb-8">
                <AdminArticleForm onArticleCreated={() => {
                  setShowCreateForm(false)
                  fetchArticles()
                }} />
              </div>
            )}

            <div className="bg-white rounded-lg shadow-sm border">
              <div className="px-6 py-4 border-b">
                <h2 className="text-lg font-semibold text-gray-900">
                  لیست مقالات ({filteredArticles.length})
                </h2>
              </div>

              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : filteredArticles.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-500">مقاله‌ای یافت نشد</p>
                </div>
              ) : (
                <div className="divide-y">
                  {filteredArticles.map((article) => (
                    <div key={article.id} className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="text-lg font-medium text-gray-900">
                            {article.title}
                          </h3>
                          {article.summary && (
                            <p className="text-gray-600 mt-1">{article.summary}</p>
                          )}
                          
                          <div className="flex flex-wrap items-center gap-2 mt-3">
                            {(() => {
                              const badge = adminService.getStatusBadge(article.status);
                              return (
                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${badge.bgColor} ${badge.color}`}>
                                  <span className="mr-1">{badge.icon}</span>
                                  {badge.text}
                                </span>
                              );
                            })()}
                            
                            {(() => {
                              const badge = adminService.getVisibilityBadge(article.visibility);
                              return (
                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${badge.bgColor} ${badge.color}`}>
                                  <span className="mr-1">{badge.icon}</span>
                                  {badge.text}
                                </span>
                              );
                            })()}
                            
                            <span className="text-xs text-gray-500">
                              نسخه {article.version}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center space-x-2 ml-4">
                          {article.status === "draft" && user?.role === "SuperAdmin" && (
                            <button
                              onClick={() => openPublishModal(article)}
                              className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                              title="انتشار مقاله"
                            >
                              انتشار
                            </button>
                          )}
                          
                          {article.status === "published" && user?.role === "SuperAdmin" && (
                            <button
                              onClick={() => updateArticleStatus(article.id, "draft")}
                              className="px-3 py-1 bg-yellow-600 text-white text-sm rounded hover:bg-yellow-700"
                              title="بازگشت به پیش‌نویس"
                            >
                              پیش‌نویس
                            </button>
                          )}

                          <button
                            onClick={() => updateArticleStatus(
                              article.id,
                              article.status === "archived" ? "draft" : "archived"
                            )}
                            className={`px-3 py-1 text-sm rounded ${
                              article.status === "archived"
                                ? "bg-blue-600 text-white hover:bg-blue-700"
                                : "bg-gray-600 text-white hover:bg-gray-700"
                            }`}
                            title={article.status === "archived" ? "بازگرداندن" : "بایگانی"}
                          >
                            {article.status === "archived" ? "بازگرداندن" : "بایگانی"}
                          </button>

                          <button
                            onClick={() => deleteArticle(article.id)}
                            className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700"
                            title="حذف مقاله"
                          >
                            حذف
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Publish Modal */}
      {publishModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                انتشار مقاله: {articleToPublish?.title}
              </h3>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  سطح دسترسی
                </label>
                <div className="space-y-2">
                  <div className="flex items-center">
                    <input
                      type="radio"
                      id="public"
                      name="visibility"
                      value="public"
                      checked={selectedVisibility === "public"}
                      onChange={() => setSelectedVisibility("public")}
                      className="h-4 w-4 text-blue-600"
                    />
                    <label htmlFor="public" className="ml-2 block text-sm text-gray-700">
                      عمومی (برای همه قابل مشاهده)
                    </label>
                  </div>
                  
                  <div className="flex items-center">
                    <input
                      type="radio"
                      id="customer"
                      name="visibility"
                      value="customer"
                      checked={selectedVisibility === "customer"}
                      onChange={() => setSelectedVisibility("customer")}
                      className="h-4 w-4 text-blue-600"
                    />
                    <label htmlFor="customer" className="ml-2 block text-sm text-gray-700">
                      مشتریان (فقط کاربران ثبت‌نام شده)
                    </label>
                  </div>
                  
                  <div className="flex items-center">
                    <input
                      type="radio"
                      id="internal"
                      name="visibility"
                      value="internal"
                      checked={selectedVisibility === "internal"}
                      onChange={() => setSelectedVisibility("internal")}
                      className="h-4 w-4 text-blue-600"
                    />
                    <label htmlFor="internal" className="ml-2 block text-sm text-gray-700">
                      داخلی (فقط ادمین‌ها و هوش مصنوعی)
                    </label>
                  </div>
                </div>
              </div>
              
              <div className="flex justify-end space-x-3">
                <button
                  onClick={closePublishModal}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  لغو
                </button>
                <button
                  onClick={() => articleToPublish && publishArticle(articleToPublish.id, selectedVisibility)}
                  className="px-4 py-2 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700"
                >
                  تایید و انتشار
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AdminPanel