"use client"

import React, { useState, useEffect } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import { knowledgeBaseService, type Article } from "../services/knowledgeBaseService"
import { useAuth } from "../context/AuthContext"
import ArticleForm from "../components/ArticleForm"
import toast from "react-hot-toast"

const ArticleEditPage: React.FC = () => {
  const { articleId } = useParams<{ articleId: string }>()
  const navigate = useNavigate()
  const { isAdmin, isSuperAdmin } = useAuth()
  const [article, setArticle] = useState<Article | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (articleId) {
      loadArticle()
    }
  }, [articleId])

  const loadArticle = async () => {
    try {
      const articleData = await knowledgeBaseService.getArticle(articleId!)
      setArticle(articleData)
    } catch (error: any) {
      console.error("Error loading article:", error)
      toast.error(error.response?.data?.detail || "خطا در بارگذاری مقاله")
      navigate("/admin") // Redirect to admin panel if article not found
    } finally {
      setLoading(false)
    }
  }

  const handleSave = () => {
    toast.success("مقاله با موفقیت بروزرسانی شد")
    // Navigate back to article detail or admin panel
    navigate(-1)
  }

  const handleCancel = () => {
    navigate(-1) // Go back to previous page
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!article) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">مقاله یافت نشد</h2>
          <Link to="/admin" className="btn-primary">
            بازگشت به پنل مدیریت
          </Link>
        </div>
      </div>
    )
  }

  // Check if user has permission to edit
  if (!isAdmin && !isSuperAdmin) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">دسترسی غیرمجاز</h2>
          <p className="text-gray-600 mb-4">شما اجازه ویرایش مقاله را ندارید.</p>
          <Link to="/admin" className="btn-primary">
            بازگشت به پنل مدیریت
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">ویرایش مقاله</h1>
              <p className="text-gray-600 mt-1">{article.title}</p>
            </div>
            <button
              onClick={handleCancel}
              className="inline-flex items-center justify-center whitespace-nowrap text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-gray-300 bg-white hover:bg-gray-50 hover:text-gray-900 h-9 rounded-md px-3"
            >
              <svg className="ml-2 -mr-1 w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              بازگشت
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ArticleForm
          article={article}
          onSave={handleSave}
          onCancel={handleCancel}
        />
      </div>
    </div>
  )
}

export default ArticleEditPage
