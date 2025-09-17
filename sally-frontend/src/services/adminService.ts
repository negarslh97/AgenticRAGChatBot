// src/services/adminService.ts

import axios from "axios";
import api from "./authService";

// ============================================================================
// Interfaces for Admin API responses and requests
// ============================================================================

export interface Article {
  id: string;
  title: string;
  content?: string;
  summary?: string;
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
  visibility?: "public" | "customer" | "internal" | null;
  author_id: string;
  version: number;
  created_at: string;
  updated_at: string;
  published_at?: string;
}

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
   * دریافت لیست همه مقالات (شامل پیش‌نویس‌ها)
   */
  async getAllArticles(): Promise<Article[]> {
    try {
      const response = await api.get<Article[]>("/api/admin/kb/articles");
      return response.data;
    } catch (error) {
      console.error("Error fetching articles:", error);
      throw new Error("خطا در دریافت مقالات");
    }
  },

  /**
   * ایجاد مقاله جدید در حالت پیش‌نویس
   */
  async createArticle(articleData: ArticleCreateRequest): Promise<{ id: string; message: string }> {
    try {
      const response = await api.post<{ id: string; message: string }>("/api/admin/kb/articles", articleData);
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
      const response = await api.put<{ message: string }>(`/api/admin/kb/articles/${articleId}`, articleData);
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
      const response = await api.post<{ message: string }>(`/api/admin/kb/articles/${articleId}/publish`, publishData || {});
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
      const response = await api.delete<{ message: string }>(`/api/admin/kb/articles/${articleId}`);
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
      const response = await api.put<{ message: string }>(`/api/admin/kb/articles/${articleId}/status`, statusData);
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

      const response = await api.post<{ message: string; article_id?: string }>("/api/admin/kb/upload", formData, {
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

  // ============================================================================
  // Ticket Management Functions
  // ============================================================================

  /**
   * دریافت لیست همه تیکت‌ها
   */
  async getAllTickets(): Promise<Ticket[]> {
    try {
      const response = await api.get<Ticket[]>("/api/admin/tickets");
      return response.data;
    } catch (error) {
      console.error("Error fetching tickets:", error);
      throw new Error("خطا در دریافت تیکت‌ها");
    }
  },

  /**
   * تخصیص تیکت به ادمین
   */
  async assignTicket(ticketId: string, assignedTo?: string): Promise<{ message: string }> {
    try {
      const response = await api.put<{ message: string }>(`/api/admin/tickets/${ticketId}/assign`, {
        assigned_to: assignedTo,
      });
      return response.data;
    } catch (error) {
      console.error("Error assigning ticket:", error);
      throw new Error("خطا در تخصیص تیکت");
    }
  },

  /**
   * بروزرسانی وضعیت تیکت
   */
  async updateTicketStatus(ticketId: string, statusData: TicketStatusUpdate): Promise<{ message: string }> {
    try {
      const response = await api.put<{ message: string }>(`/api/admin/tickets/${ticketId}/status`, statusData);
      return response.data;
    } catch (error) {
      console.error("Error updating ticket status:", error);
      throw new Error("خطا در بروزرسانی وضعیت تیکت");
    }
  },

  // ============================================================================
  // Utility Functions
  // ============================================================================

  /**
   * تبدیل وضعیت مقاله به متن فارسی
   */
  getArticleStatusText(status: string): string {
    switch (status) {
      case "PUBLISHED":
        return "منتشر شده";
      case "DRAFT":
        return "پیش‌نویس";
      case "ARCHIVED":
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
      default:
        return "تعیین نشده";
    }
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
