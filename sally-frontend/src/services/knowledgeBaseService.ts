import api from "./authService"

export interface Article {
  id: string
  title: string
  content: string
  summary?: string
  category_id?: string
  tags: string[]
  status: "draft" | "published" | "archived"
  is_public: boolean
  created_at: string
  updated_at: string
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
  is_public: boolean
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
    const response = await api.get("/admin/kb/articles")
    return response.data
  },

  async createArticle(articleData: CreateArticleData): Promise<{ id: string; message: string }> {
    const response = await api.post("/admin/kb/articles", articleData)
    return response.data
  },

  async updateArticle(articleId: string, articleData: UpdateArticleData): Promise<{ message: string }> {
    const response = await api.put(`/admin/kb/articles/${articleId}`, articleData)
    return response.data
  },

  async publishArticle(articleId: string): Promise<{ message: string }> {
    const response = await api.post(`/admin/kb/articles/${articleId}/publish`)
    return response.data
  },

  async deleteArticle(articleId: string): Promise<{ message: string }> {
    const response = await api.delete(`/admin/kb/articles/${articleId}`)
    return response.data
  },
}
