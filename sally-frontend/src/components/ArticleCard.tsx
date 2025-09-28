"use client"

import type React from "react"
import { Link } from "react-router-dom"
import type { Article } from "../services/knowledgeBaseService"
import { adminService } from "../services/adminService"

interface ArticleCardProps {
  article: Article
  isadminView?: boolean
}

const ArticleCard: React.FC<ArticleCardProps> = ({ article, isadminView = false }) => {

  const linkTo = isadminView ? `/api/super-admin/kb/articles/${article.id}` : `/api/kb/articles/${article.id}`

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
          <>
            {(() => {
              const badge = adminService.getStatusBadge(article.status);
              return (
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${badge.bgColor} ${badge.color}`}>
                  <span className="mr-1">{badge.icon}</span>
                  {badge.text}
                </span>
              );
            })()}
            {article.visibility && (
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${(() => {
                const badge = adminService.getVisibilityBadge(article.visibility);
                return `${badge.bgColor} ${badge.color}`;
              })()}`}>
                {(() => {
                  const badge = adminService.getVisibilityBadge(article.visibility);
                  return (
                    <>
                      <span className="mr-1">{badge.icon}</span>
                      {badge.text}
                    </>
                  );
                })()}
              </span>
            )}
          </>
        )}
      </div>

      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center space-x-4">
          {article.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {article.tags.slice(0, 3).map((tag, index) => (
                <span key={index} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                  {tag.name}
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
