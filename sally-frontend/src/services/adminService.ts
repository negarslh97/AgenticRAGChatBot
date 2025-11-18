// src/services/adminService.ts

// import axios from "axios";
import api from "./authService";
import { Article } from "./knowledgeBaseService";

// ============================================================================
// Interfaces for Admin API responses and requests
// ============================================================================

export interface ArticleCreateRequest {
  title: string;
  content: string;
  summary?: string;
}

export interface ArticleUpdateRequest {
  title?: string;
  content?: string;
  summary?: string;
}

export interface PublishArticleRequest {
  visibility?: "public" | "customer" | "internal";
}

export interface GeneratedMetadata {
  summary: string;
  tags: string[];
  suggested_category: string;
  suggested_visibility: string;
}

export interface Ticket {
  id: string;
  title: string;
  status: "open" | "in_progress" | "resolved" | "closed";
  priority: "low" | "medium" | "high" | "urgent";
  customer_id: string;
  assigned_to?: string;
  created_at: string;
  updated_at: string;
}

export interface TicketStatusUpdate {
  status: "open" | "in_progress" | "resolved" | "closed";
}

// ============================================================================
// Admin Service Functions
// ============================================================================

export const adminService = {
  // ============================================================================
  // Article Management Functions
  // ============================================================================


  /**
   * دریافت مقاله بر اساس ID
   */
  async getArticle(articleId: string): Promise<Article> {
    try {
      const response = await api.get<Article>(`/api/super-admin/kb/articles/${articleId}`);
      return response.data;
    } catch (error) {
      console.error("Error getting article:", error);
      throw new Error("خطا در دریافت مقاله");
    }
  },

  /**
   * ایجاد مقاله جدید در حالت پیش‌نویس
   */
  async createArticle(articleData: ArticleCreateRequest): Promise<{ id: string; message: string }> {
    try {
      const response = await api.post<{ id: string; message: string }>("/api/super-admin/kb/articles", articleData);
      return response.data;
    } catch (error) {
      console.error("Error creating article:", error);
      throw new Error("خطا در ایجاد مقاله");
    }
  },

  /**
   * بروزرسانی مقاله موجود
   */
  async updateArticle(articleId: string, articleData: ArticleUpdateRequest): Promise<{ message: string }> {
    try {
      const response = await api.put<{ message: string }>(`/api/super-admin/kb/articles/${articleId}`, articleData);
      return response.data;
    } catch (error) {
      console.error("Error updating article:", error);
      throw new Error("خطا در بروزرسانی مقاله");
    }
  },

  /**
   * انتشار مقاله (فقط ادمین ارشد)
   */
  async publishArticle(articleId: string, publishData?: PublishArticleRequest): Promise<{ message: string }> {
    try {
      const response = await api.post<{ message: string }>(`/api/super-admin/kb/articles/${articleId}/publish`, publishData || {});
      return response.data;
    } catch (error) {
      console.error("Error publishing article:", error);
      throw new Error("خطا در انتشار مقاله");
    }
  },

  /**
   * حذف مقاله (فقط ادمین ارشد)
   */
  async deleteArticle(articleId: string): Promise<{ message: string }> {
    try {
      const response = await api.delete<{ message: string }>(`/api/super-admin/kb/articles/${articleId}`);
      return response.data;
    } catch (error) {
      console.error("Error deleting article:", error);
      throw new Error("خطا در حذف مقاله");
    }
  },

  /**
   * بروزرسانی وضعیت مقاله
   */
  async updateArticleStatus(articleId: string, statusData: { status: string }): Promise<{ message: string }> {
    try {
      const response = await api.put<{ message: string }>(`/api/super-admin/kb/articles/${articleId}/status`, statusData);
      return response.data;
    } catch (error) {
      console.error("Error updating article status:", error);
      throw new Error("خطا در تغییر وضعیت مقاله");
    }
  },

  /**
   * آپلود فایل و ایجاد مقاله پیش‌نویس
   */
  async uploadFile(file: File): Promise<{ message: string; article_id?: string }> {
    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await api.post<{ message: string; article_id?: string }>("/api/super-admin/kb/articles/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      return response.data;
    } catch (error) {
      console.error("Error uploading file:", error);
      throw new Error("خطا در آپلود فایل");
    }
  },

  /**
   * تولید متادیتای هوش مصنوعی برای مقاله
   */
  async generateArticleMetadata(title: string, content: string): Promise<GeneratedMetadata> {
    try {
      const response = await api.post<GeneratedMetadata>("/api/admin/articles/generate-metadata", {
        title,
        content,
      });
      return response.data;
    } catch (error) {
      console.error("Error generating metadata:", error);
      throw new Error("خطا در تولید متادیتای هوش مصنوعی");
    }
  },

  /**
   * تبدیل متن ساده به Markdown با هوش مصنوعی
   */
  async convertTextToMarkdown(title: string, content: string): Promise<{
    success: boolean;
    markdown_content: string;
    original_length: number;
    markdown_length: number;
  }> {
    try {
      const response = await api.post<{
        success: boolean;
        markdown_content: string;
        original_length: number;
        markdown_length: number;
      }>("/api/super-admin/kb/convert-to-markdown", {
        title,
        content,
      });

      return response.data;
    } catch (error) {
      console.error("Error converting text to markdown:", error);
      throw new Error("خطا در تبدیل متن به Markdown");
    }
  },

  // ============================================================================
  // Ticket Management Functions
  // ============================================================================

  /**
   * دریافت لیست همه تیکت‌ها
   */

  // ============================================================================
  // Utility Functions
  // ============================================================================

  /**
   * تبدیل وضعیت مقاله به متن فارسی
   */
  getArticleStatusText(status: string): string {
    switch (status) {
      case "published":
        return "منتشر شده";
      case "draft":
        return "پیش‌نویس";
      case "archived":
        return "بایگانی شده";
      default:
        return status;
    }
  },

  /**
   * تبدیل سطح دسترسی به متن فارسی
   */
  getVisibilityText(visibility: string | null | undefined): string {
    switch (visibility) {
      case "public":
        return "عمومی";
      case "customer":
        return "مشتریان";
      case "internal":
        return "داخلی";
      case null:
      case undefined:
      case "":
        return "تعیین نشده";
      default:
        return visibility || "نامشخص";
    }
  },

  /**
   * دریافت رنگ و آیکون برای visibility
   */
  getVisibilityBadge(visibility: string | null | undefined): { text: string; color: string; bgColor: string; icon: string } {
    const text = this.getVisibilityText(visibility);

    switch (visibility) {
      case "public":
        return {
          text,
          color: "text-green-700",
          bgColor: "bg-green-100",
          icon: "🌐"
        };
      case "customer":
        return {
          text,
          color: "text-blue-700",
          bgColor: "bg-blue-100",
          icon: "👥"
        };
      case "internal":
        return {
          text,
          color: "text-purple-700",
          bgColor: "bg-purple-100",
          icon: "🔒"
        };
      default:
        return {
          text,
          color: "text-gray-700",
          bgColor: "bg-gray-100",
          icon: "❓"
        };
    }
  },

  /**
   * دریافت رنگ و آیکون برای وضعیت مقاله
   */
  getStatusBadge(status: string): { text: string; color: string; bgColor: string; icon: string } {
    const text = this.getStatusText(status);

    switch (status) {
      case "published":
        return {
          text,
          color: "text-green-700",
          bgColor: "bg-green-100",
          icon: "✅"
        };
      case "draft":
        return {
          text,
          color: "text-yellow-700",
          bgColor: "bg-yellow-100",
          icon: "📝"
        };
      case "archived":
        return {
          text,
          color: "text-red-700",
          bgColor: "bg-red-100",
          icon: "📦"
        };
      default:
        return {
          text,
          color: "text-gray-700",
          bgColor: "bg-gray-100",
          icon: "❓"
        };
    }
  },

  /**
   * دریافت متن وضعیت مقاله
   */
  getStatusText(status: string): string {
    switch (status) {
      case "published":
        return "منتشر شده";
      case "draft":
        return "پیش‌نویس";
      case "archived":
        return "بایگانی شده";
      default:
        return status || "نامشخص";
    }
  },

  /**
   * دریافت کلاس‌های CSS برای وضعیت مقاله
   */
  getStatusClasses(status: string): string {
    const badge = this.getStatusBadge(status);
    return `${badge.bgColor} ${badge.color}`;
  },

  /**
   * تبدیل وضعیت تیکت به متن فارسی
   */
  getTicketStatusText(status: string): string {
    switch (status) {
      case "open":
        return "باز";
      case "in_progress":
        return "در حال بررسی";
      case "resolved":
        return "حل شده";
      case "closed":
        return "بسته شده";
      default:
        return status;
    }
  },

  /**
   * تبدیل اولویت تیکت به متن فارسی
   */
  getTicketPriorityText(priority: string): string {
    switch (priority) {
      case "low":
        return "کم";
      case "medium":
        return "متوسط";
      case "high":
        return "بالا";
      case "urgent":
        return "فوری";
      default:
        return priority;
    }
  },
};

export default adminService;
