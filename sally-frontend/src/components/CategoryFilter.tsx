"use client"

import type React from "react"
import { useState, useEffect } from "react"
import { knowledgeBaseService, type Category } from "../services/knowledgeBaseService"
import toast from "react-hot-toast"

interface CategoryFilterProps {
  selectedCategoryId?: string
  onCategoryChange: (categoryId?: string) => void
}

const CategoryFilter: React.FC<CategoryFilterProps> = ({ selectedCategoryId, onCategoryChange }) => {
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadCategories()
  }, [])

  const loadCategories = async () => {
    try {
      const categoryData = await knowledgeBaseService.getCategories()
      setCategories(categoryData)
    } catch (error: any) {
      toast.error("Failed to load categories")
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded"></div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <h3 className="font-medium text-gray-900 mb-3">Categories</h3>

      <button
        onClick={() => onCategoryChange(undefined)}
        className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
          !selectedCategoryId ? "bg-blue-50 text-blue-700 border border-blue-200" : "text-gray-700 hover:bg-gray-50"
        }`}
      >
        All Articles
      </button>

      {categories.map((category) => (
        <button
          key={category.id}
          onClick={() => onCategoryChange(category.id)}
          className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
            selectedCategoryId === category.id
              ? "bg-blue-50 text-blue-700 border border-blue-200"
              : "text-gray-700 hover:bg-gray-50"
          }`}
        >
          <div>
            <p className="font-medium">{category.name}</p>
            {category.description && <p className="text-sm text-gray-500 mt-1">{category.description}</p>}
          </div>
        </button>
      ))}
    </div>
  )
}

export default CategoryFilter
