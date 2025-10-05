"use client"

import type React from "react"
import { useState, useEffect } from "react"
import { Routes, Route } from "react-router-dom"
import { knowledgeBaseService, type Article } from "../services/knowledgeBaseService"
import ArticleCard from "../components/ArticleCard"
import ArticleDetail from "../components/ArticleDetail"
import ArticleSearch from "../components/ArticleSearch"
import CategoryFilter from "../components/CategoryFilter"
import toast from "react-hot-toast"
import { BookOpen } from "lucide-react"

const KnowledgeBasePage: React.FC = () => {
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | undefined>()

  useEffect(() => {
    loadArticles()
  }, [selectedCategoryId])

  const loadArticles = async () => {
    setLoading(true)
    try {
      const articleData = await knowledgeBaseService.getPublicArticles(selectedCategoryId)
      setArticles(articleData)
    } catch (error: any) {
      toast.error("Failed to load articles")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Routes>
        <Route
          path="/"
          element={
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              {/* Header */}
              <div className="text-center mb-12">
                <h1 className="text-4xl font-bold text-gray-900 mb-4">Knowledge Base</h1>
                <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                  Find answers to common questions and learn how to get the most out of our platform
                </p>
              </div>

              {/* Search */}
              <div className="mb-12">
                <ArticleSearch />
              </div>

              {/* Main Content */}
              <div className="flex flex-col lg:flex-row gap-8">
                {/* Sidebar */}
                <div className="lg:w-64 flex-shrink-0">
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                    <CategoryFilter selectedCategoryId={selectedCategoryId} onCategoryChange={setSelectedCategoryId} />
                  </div>
                </div>

                {/* Articles */}
                <div className="flex-1">
                  {loading ? (
                    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                      {[...Array(6)].map((_, i) => (
                        <div key={i} className="animate-pulse">
                          <div className="card">
                            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                            <div className="h-3 bg-gray-200 rounded w-full mb-2"></div>
                            <div className="h-3 bg-gray-200 rounded w-2/3"></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : articles.length === 0 ? (
                    <div className="text-center py-12">
                      <div className="flex justify-center mb-4">
                        <div className="p-4 bg-gray-100 rounded-full">
                          <BookOpen className="h-16 w-16 text-gray-400" />
                        </div>
                      </div>
                      <h3 className="text-lg font-medium text-gray-900 mb-2">No articles found</h3>
                      <p className="text-gray-500">
                        {selectedCategoryId
                          ? "No articles in this category yet."
                          : "No articles available at the moment."}
                      </p>
                    </div>
                  ) : (
                    <div>
                      <div className="flex items-center justify-between mb-6">
                        <h2 className="text-2xl font-bold text-gray-900">
                          {selectedCategoryId ? "Category Articles" : "All Articles"}
                        </h2>
                        <span className="text-gray-500">
                          {articles.length} {articles.length === 1 ? "article" : "articles"}
                        </span>
                      </div>

                      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                        {articles.map((article) => (
                          <ArticleCard key={article.id} article={article} />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          }
        />
        <Route
          path="/articles/:articleId"
          element={
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              <ArticleDetail />
            </div>
          }
        />
      </Routes>
    </div>
  )
}

export default KnowledgeBasePage
