"use client"

import type React from "react"
import { useState } from "react"
import { knowledgeBaseService, type SearchResult } from "../services/knowledgeBaseService"
import { Link } from "react-router-dom"
import toast from "react-hot-toast"

const ArticleSearch: React.FC = () => {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setHasSearched(true)

    try {
      const searchResults = await knowledgeBaseService.searchArticles(query)
      setResults(searchResults.results)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Search failed")
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value)
    if (!e.target.value.trim()) {
      setResults([])
      setHasSearched(false)
    }
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex space-x-2">
          <input
            type="text"
            value={query}
            onChange={handleInputChange}
            placeholder="Search knowledge base..."
            className="flex-1 input-field"
          />
          <button type="submit" className="btn-primary" disabled={loading || !query.trim()}>
            {loading ? "Searching..." : "Search"}
          </button>
        </div>
      </form>

      {hasSearched && (
        <div className="space-y-4">
          {loading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="card">
                    <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                    <div className="h-3 bg-gray-200 rounded w-full mb-2"></div>
                    <div className="h-3 bg-gray-200 rounded w-2/3"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : results.length === 0 ? (
            <div className="text-center py-8">
              <div className="text-gray-400 text-4xl mb-4">🔍</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No results found</h3>
              <p className="text-gray-500">Try different keywords or browse our categories below.</p>
            </div>
          ) : (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Search Results ({results.length} {results.length === 1 ? "result" : "results"})
              </h3>
              <div className="space-y-3">
                {results.map((result) => (
                  <div key={result.id} className="card hover:shadow-md transition-shadow">
                    <h4 className="font-medium text-gray-900 mb-2">
                      <Link to={`/kb/articles/${result.id}`} className="hover:text-blue-600 transition-colors">
                        {result.title}
                      </Link>
                    </h4>
                    {result.summary && <p className="text-gray-600 text-sm mb-2">{result.summary}</p>}
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span>Relevance: {Math.round((result.score / 10) * 100)}%</span>
                      <Link to={`/kb/articles/${result.id}`} className="text-blue-600 hover:text-blue-500 font-medium">
                        Read Article →
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ArticleSearch
