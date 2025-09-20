import api from "./authService"

export interface Article {
  id: string
  title: string
  content: string
  summary?: string
  category_id?: string
  tags: string[]
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED"
  visibility?: "public" | "customer" | "internal" | null
  author_id: string
  version: number
  created_at: string
  updated_at: string
  published_at?: string
}

export interface Category {
  id: string
  name: string
  description?: string
  is_public: boolean
}

export interface SearchResult {
  id: string
  title: string
  summary?: string
  score: number
}

export interface CreateArticleData {
  title: string
  content: string
  summary?: string
  category_id?: string
  tags: string[]
}

export interface UpdateArticleData {
  title?: string
  content?: string
  summary?: string
  category_id?: string
  tags?: string[]
  is_public?: boolean
}

export const knowledgeBaseService = {
  // Public API
  async getPublicArticles(categoryId?: string, search?: string): Promise<Article[]> {
    const params = new URLSearchParams()
    if (categoryId) params.append("category_id", categoryId)
    if (search) params.append("search", search)

    const response = await api.get(`/kb/articles?${params.toString()}`)
    return response.data
  },

  async getArticle(articleId: string): Promise<Article> {
    const response = await api.get(`/kb/articles/${articleId}`)
    return response.data
  },

  async getCategories(): Promise<Category[]> {
    const response = await api.get("/kb/categories")
    return response.data
  },

  async searchArticles(query: string): Promise<{ results: SearchResult[] }> {
    const response = await api.get(`/kb/search?q=${encodeURIComponent(query)}`)
    return response.data
  },

  // admin API
  async getAllArticles(): Promise<Article[]> {
    try {
      const response = await api.get("/admin/kb/articles")
      console.log("KB Service - Raw response:", response)
      console.log("KB Service - Response data:", response.data)
      
      // بررسی اینکه داده درست برگشته یا نه
      if (response.data && Array.isArray(response.data)) {
        return response.data
      } else if (response.data && response.data.data && Array.isArray(response.data.data)) {
        return response.data.data
      } else {
        console.error("Unexpected response format:", response.data)
        return []
      }
    } catch (error) {
      console.error("KB Service - Error in getAllArticles:", error)
      throw error
    }
  },

  async createArticle(articleData: CreateArticleData): Promise<Article> {
    const response = await api.post("/admin/kb/articles", articleData)
    return response.data
  },

  async updateArticle(articleId: string, articleData: UpdateArticleData): Promise<Article> {
    const response = await api.put(`/admin/kb/articles/${articleId}`, articleData)
    return response.data
  },

  async publishArticle(articleId: string, visibility: string = "public"): Promise<Article> {
    const response = await api.post(`/admin/kb/articles/${articleId}/publish`, { visibility })
    return response.data
  },

  async deleteArticle(articleId: string): Promise<void> {
    await api.delete(`/admin/kb/articles/${articleId}`)
  },
}
