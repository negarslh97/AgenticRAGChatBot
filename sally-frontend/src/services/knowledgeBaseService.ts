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
  status: "draft" | "published" | "archived"
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
  parent_id?: string | null
  is_public: boolean
  articles_count?: number
  children_count?: number
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
  status?: "draft" | "published" | "archived"
  visibility?: "public" | "customer" | "internal"
}

export interface UpdateArticleData {
  title?: string
  content_markdown?: string
  content_html?: string
  summary?: string
  category_id?: string
  tag_names?: string[]
  status?: "draft" | "published" | "archived"
  visibility?: "public" | "customer" | "internal"
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
  embedder_model: string
  embedder_api_key_set: boolean
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

  async getAllCategoriesForAdmin(): Promise<Category[]> {
    const response = await api.get("/api/super-admin/categories/")
    return response.data
  },

  async searchArticles(query: string): Promise<{ results: SearchResult[] }> {
    const response = await api.get(`/kb/search?q=${encodeURIComponent(query)}`)
    return response.data
  },

  // admin API
  async getAllArticles(): Promise<Article[]> {
    try {
      const response = await api.get("/api/super-admin/kb/articles")
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

  async getArticleByAdmin(articleId: string): Promise<Article> {
    const response = await api.get(`/api/super-admin/kb/articles/${articleId}`)
    return response.data
  },

  async createArticle(articleData: CreateArticleData): Promise<Article> {
    const response = await api.post("/api/super-admin/kb/articles", articleData)
    return response.data
  },

  async updateArticle(articleId: string, articleData: UpdateArticleData): Promise<Article> {
    const response = await api.put(`/api/super-admin/kb/articles/${articleId}`, articleData)
    return response.data
  },

  async publishArticle(articleId: string, visibility: string = "public"): Promise<Article> {
    const response = await api.post(`/api/super-admin/kb/articles/${articleId}/publish`, { visibility })
    return response.data
  },

  async deleteArticle(articleId: string): Promise<void> {
    await api.delete(`/api/super-admin/kb/articles/${articleId}`)
  },

  // New endpoints for Docs-as-Code system
  async getArticleHistory(articleId: string): Promise<ArticleHistoryItem[]> {
    const response = await api.get(`/api/super-admin/kb/articles/${articleId}/history`)
    return response.data
  },

  async getSyncStatus(): Promise<SyncStatusResponse> {
    const response = await api.get("/api/super-admin/kb/sync/status")
    return response.data
  },

  async uploadAndConvertFile(file: File): Promise<FileUploadResponse> {
    const formData = new FormData()
    formData.append("file", file)
    
    const response = await api.post("/api/super-admin/kb/upload-convert", formData, {
      headers: {
        "Content-Type": "multipart/form-data"
      }
    })
    return response.data
  },

  // New endpoints for Weaviate sync management
  async checkArticlesSyncStatus(): Promise<{
    total_published: number
    synced: number
    not_synced: number
    not_synced_articles: Array<{ id: string; title: string; published_at: string | null }>
    sync_percentage: number
  }> {
    const response = await api.get("/api/super-admin/kb/sync/check-articles")
    return response.data
  },

  async getDetailedSyncStatus(): Promise<{
    total_published: number
    new_articles: {
      count: number
      articles: Array<{
        id: string
        title: string
        created_at: string | null
        published_at: string | null
      }>
    }
    modified_articles: {
      count: number
      articles: Array<{
        id: string
        title: string
        updated_at: string
        last_synced_at: string
      }>
    }
    synced_articles: {
      count: number
    }
    archived_in_weaviate: {
      count: number
      articles: Array<{
        id: string
        title: string
        archived_at: string | null
      }>
    }
    needs_action: boolean
  }> {
    const response = await api.get("/api/super-admin/kb/sync/detailed-status")
    return response.data
  },

  async syncAllArticlesToWeaviate(force: boolean = false): Promise<{
    success: boolean
    total_articles: number
    jobs_scheduled: number
    skipped: number
    job_ids: string[]
    message: string
  }> {
    const response = await api.post(`/api/super-admin/kb/sync/sync-all-articles?force=${force}`)
    return response.data
  },

  async removeArchivedFromWeaviate(): Promise<{
    success: boolean
    removed_count: number
    total_archived: number
    errors: string[] | null
    message: string
  }> {
    const response = await api.post("/api/super-admin/kb/sync/remove-archived")
    return response.data
  },

  async getWeaviateContents(limit: number = 100): Promise<{
    total_nodes: number
    returned_nodes: number
    articles_count: number
    articles: Array<{ article_id: string; nodes_count: number; titles: string[] }>
    nodes: Array<{
      uuid: string
      article_id: string
      title: string
      level: number
      content: string
      path: string
      order: number
    }>
  }> {
    const response = await api.get(`/api/super-admin/kb/weaviate/contents?limit=${limit}`)
    return response.data
  },

  async getWeaviateNodeDetails(nodeUuid: string): Promise<{
    uuid: string
    properties: any
    vector: number[] | null
    vector_length: number
    metadata: {
      creation_time: string | null
      last_update_time: string | null
    }
  }> {
    const response = await api.get(`/api/super-admin/kb/weaviate/node/${nodeUuid}`)
    return response.data
  }
}
