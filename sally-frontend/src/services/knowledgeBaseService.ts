import api from "./authService"

export interface ArticleCategory {
  id: string
  name: string
  slug: string
}

export interface ArticleTag {
  id: string
  name: string
  color?: string
}

export interface Article {
  id: string
  title: string
  content_markdown: string
  content_html: string
  summary?: string
  category?: ArticleCategory
  tags: ArticleTag[]
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
  slug: string
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
  content_markdown: string
  content_html?: string
  summary?: string
  category_id?: string
  tag_names: string[]
}

export interface UpdateArticleData {
  title?: string
  content_markdown?: string
  content_html?: string
  summary?: string
  category_id?: string
  tag_names?: string[]
  is_public?: boolean
}

export interface ArticleHistoryItem {
  commit_hash: string
  author_name: string
  author_email: string
  message: string
  timestamp: string
  changes: string[]
}

export interface SyncStatusResponse {
  status: string
  last_sync?: string
  pending_operations: number
  health_status: string
}

export interface FileUploadResponse {
  success: boolean
  markdown_content: string
  title: string
  summary: string
  suggested_tags: string[]
  suggested_category?: string
  error?: string
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

  // New endpoints for Docs-as-Code system
  async getArticleHistory(articleId: string): Promise<ArticleHistoryItem[]> {
    const response = await api.get(`/admin/kb/articles/${articleId}/history`)
    return response.data
  },

  async getSyncStatus(): Promise<SyncStatusResponse> {
    const response = await api.get("/admin/kb/sync/status")
    return response.data
  },

  async uploadAndConvertFile(file: File): Promise<FileUploadResponse> {
    const formData = new FormData()
    formData.append("file", file)
    
    const response = await api.post("/admin/kb/upload-convert", formData, {
      headers: {
        "Content-Type": "multipart/form-data"
      }
    })
    return response.data
  }
}
