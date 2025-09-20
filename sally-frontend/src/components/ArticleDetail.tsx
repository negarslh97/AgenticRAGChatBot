"use client"

import type React from "react"
import { useState, useEffect } from "react"
import { useParams, Link } from "react-router-dom"
import { knowledgeBaseService, type Article } from "../services/knowledgeBaseService"
import { useAuth } from "../context/AuthContext"
import toast from "react-hot-toast"

interface ArticleDetailProps {
  isadminView?: boolean
}

const ArticleDetail: React.FC<ArticleDetailProps> = ({ isadminView = false }) => {
  const { articleId } = useParams<{ articleId: string }>()
  const [article, setArticle] = useState<Article | null>(null)
  const [loading, setLoading] = useState(true)
  const { isAdmin, isSuperAdmin } = useAuth()

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
      toast.error(error.response?.data?.detail || "Failed to load article")
    } finally {
      setLoading(false)
    }
  }

  const handlePublish = async () => {
    if (!article || !isSuperAdmin) return

    try {
      await knowledgeBaseService.publishArticle(article.id)
      toast.success("Article published successfully!")
      loadArticle() // Reload to get updated status
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to publish article")
    }
  }

  const handleDelete = async () => {
    if (!article || !isSuperAdmin) return

    if (window.confirm("Are you sure you want to delete this article? This action cannot be undone.")) {
      try {
        await knowledgeBaseService.deleteArticle(article.id)
        toast.success("Article deleted successfully!")
        window.history.back()
      } catch (error: any) {
        toast.error(error.response?.data?.detail || "Failed to delete article")
      }
    }
  }

  const getStatusColor = (status: string) => {
    const colors = {
      DRAFT: "bg-gray-100 text-gray-800",
      PUBLISHED: "bg-green-100 text-green-800",
      ARCHIVED: "bg-red-100 text-red-800",
    }
    return colors[status as keyof typeof colors] || "bg-gray-100 text-gray-800"
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          <div className="space-y-2">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          </div>
        </div>
      </div>
    )
  }

  if (!article) {
    return (
      <div className="max-w-4xl mx-auto text-center py-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Article Not Found</h2>
        <Link to="/kb" className="btn-primary">
          Back to Knowledge Base
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Article Header */}
      <div className="mb-8">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-gray-900 mb-4">{article.title}</h1>

            <div className="flex items-center space-x-4 mb-4">
              {isadminView && (
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(article.status)}`}>
                  {article.status.toUpperCase()}
                </span>
              )}

              {article.tags.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {article.tags.map((tag, index) => (
                    <span key={index} className="px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded-full">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {article.summary && <p className="text-lg text-gray-600 mb-6 leading-relaxed">{article.summary}</p>}
          </div>

          {isadminView && (
            <div className="flex flex-col space-y-2 ml-6">
              {article.status === "DRAFT" && isSuperAdmin && (
                <button onClick={handlePublish} className="btn-primary text-sm">
                  Publish Article
                </button>
              )}

              {isAdmin && (
                <Link to={`/admin/kb/articles/${article.id}/edit`} className="btn-secondary text-sm">
                  Edit Article
                </Link>
              )}

              {isSuperAdmin && (
                <button
                  onClick={handleDelete}
                  className="bg-red-600 hover:bg-red-700 text-white text-sm px-3 py-2 rounded-lg transition-colors"
                >
                  Delete Article
                </button>
              )}
            </div>
          )}
        </div>

        <div className="text-sm text-gray-500 border-b border-gray-200 pb-4">
          <p>Created: {new Date(article.created_at).toLocaleDateString()}</p>
          <p>Last updated: {new Date(article.updated_at).toLocaleDateString()}</p>
        </div>
      </div>

      {/* Article Content */}
      <div className="prose prose-lg max-w-none">
        <div className="whitespace-pre-wrap text-gray-800 leading-relaxed">{article.content}</div>
      </div>

      {/* Navigation */}
      <div className="mt-12 pt-8 border-t border-gray-200">
        <Link to={isadminView ? "/admin/kb" : "/kb"} className="text-blue-600 hover:text-blue-500 font-medium">
          ← Back to {isadminView ? "Admin" : ""} Knowledge Base
        </Link>
      </div>
    </div>
  )
}

export default ArticleDetail
