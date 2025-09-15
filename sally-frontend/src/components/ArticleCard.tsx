"use client"

import type React from "react"
import { Link } from "react-router-dom"
import type { Article } from "../services/knowledgeBaseService"

interface ArticleCardProps {
  article: Article
  isadminView?: boolean
}

const ArticleCard: React.FC<ArticleCardProps> = ({ article, isadminView = false }) => {
  const getStatusColor = (status: string) => {
    const colors = {
      draft: "bg-gray-100 text-gray-800",
      published: "bg-green-100 text-green-800",
      archived: "bg-red-100 text-red-800",
    }
    return colors[status as keyof typeof colors] || "bg-gray-100 text-gray-800"
  }

  const linkTo = isadminView ? `/admin/kb/articles/${article.id}` : `/kb/articles/${article.id}`

  return (
    <div className="card hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            <Link to={linkTo} className="hover:text-blue-600 transition-colors">
              {article.title}
            </Link>
          </h3>
          {article.summary && <p className="text-gray-600 text-sm mb-3 line-clamp-2">{article.summary}</p>}
        </div>
        {isadminView && (
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(article.status)}`}>
            {article.status.toUpperCase()}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center space-x-4">
          {article.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {article.tags.slice(0, 3).map((tag, index) => (
                <span key={index} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                  {tag}
                </span>
              ))}
              {article.tags.length > 3 && (
                <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full">
                  +{article.tags.length - 3} more
                </span>
              )}
            </div>
          )}
        </div>
        <div className="text-gray-500 text-xs">
          {isadminView ? (
            <div>
              <p>Created: {new Date(article.created_at).toLocaleDateString()}</p>
              <p>Updated: {new Date(article.updated_at).toLocaleDateString()}</p>
            </div>
          ) : (
            <p>Updated {new Date(article.updated_at).toLocaleDateString()}</p>
          )}
        </div>
      </div>
    </div>
  )
}

export default ArticleCard
