"use client"

import type React from "react"
import { useState, useEffect } from "react"
import { useParams, Link } from "react-router-dom"
import { knowledgeBaseService, type Article } from "../services/knowledgeBaseService"
import { adminService } from "../services/adminService"
import { Button } from "./ui/button"
import { MarkdownRenderer } from "./ui/markdown-renderer"
import toast from "react-hot-toast"

interface ArticleDetailProps {
  isadminView?: boolean
}

const ArticleDetail: React.FC<ArticleDetailProps> = ({ isadminView = false }) => {
  const { articleId } = useParams<{ articleId: string }>()
  const [article, setArticle] = useState<Article | null>(null)
  const [loading, setLoading] = useState(true)

  const loadArticle = async () => {
    try {
      // اگر در حالت admin هستیم، از admin API استفاده کنیم
      const articleData = isadminView
        ? await adminService.getArticle(articleId!)
        : await knowledgeBaseService.getArticle(articleId!)
      setArticle(articleData)
    } catch (error: any) {
      console.error("Error loading article:", error)
      toast.error(error.response?.data?.detail || "خطا در بارگذاری مقاله")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (articleId) {
      loadArticle()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [articleId])


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
        <Link to="/kb">
          <Button>Back to Knowledge Base</Button>
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
            <h1 className="text-3xl font-bold text-gray-900 mb-4">{article.title || "عنوان مقاله"}</h1>

            <div className="flex items-center space-x-4 mb-4">
              {isadminView && article.status && (
                <>
                  {(() => {
                    const badge = adminService.getStatusBadge(article.status);
                    return (
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${badge.bgColor} ${badge.color}`}>
                        <span className="mr-1">{badge.icon}</span>
                        {badge.text}
                      </span>
                    );
                  })()}
                </>
              )}

              {article.tags && article.tags.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {article.tags.map((tag, index) => (
                    <span key={index} className="px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded-full">
                      {tag.name}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {article.summary && <p className="text-lg text-gray-600 mb-6 leading-relaxed">{article.summary}</p>}
          </div>

          {isadminView && (
            <div className="mt-12 pt-8 border-t border-gray-200">
              <Link to={isadminView ? "/super-admin/knowledge-base" : "/kb"} className="text-blue-600 hover:text-blue-500 font-large">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
                </svg>
              </Link>
            </div>
          )}
        </div>

        <div className="text-sm text-gray-500 border-b border-gray-200 pb-4">
          <p>Created: {article.created_at ? new Date(article.created_at).toLocaleDateString() : "نامشخص"}</p>
          <p>Last updated: {article.updated_at ? new Date(article.updated_at).toLocaleDateString() : "نامشخص"}</p>
        </div>
      </div>

      {/* Article Content */}
      <MarkdownRenderer 
        content={article.content_markdown || article.content_html || "محتوایی برای نمایش وجود ندارد."}
        variant="default"
      />

      {/* Navigation */}
      
    </div>
  )
}

export default ArticleDetail
