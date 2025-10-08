/**
 * Category Service - مدیریت دسته‌بندی‌های Knowledge Base
 */

import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface Category {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  parent_id?: string | null;
  is_public: boolean;
  created_at: string;
  updated_at: string;
  articles_count?: number;
  children_count?: number;
}

export interface CategoryCreate {
  name: string;
  slug: string;
  description?: string;
  parent_id?: string | null;
  is_public: boolean;
}

export interface CategoryUpdate {
  name?: string;
  slug?: string;
  description?: string;
  parent_id?: string | null;
  is_public?: boolean;
}

export interface CategoryTreeNode {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  is_public: boolean;
  children: CategoryTreeNode[];
}

export interface CategoryDeleteResult {
  category_name: string;
  children_count: number;
  articles_count: number;
  deleted_categories: string[];
  affected_articles: any[];
  moved_children: string[];
  message: string;
}

class CategoryService {
  private getAuthHeader() {
    const token = localStorage.getItem('token');
    return {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    };
  }

  /**
   * دریافت لیست تمام دسته‌بندی‌ها
   */
  async getCategories(isPublicOnly = false, parentId?: string): Promise<Category[]> {
    try {
      const params = new URLSearchParams();
      if (isPublicOnly) params.append('is_public_only', 'true');
      if (parentId) params.append('parent_id', parentId);

      const url = `${API_URL}/api/super-admin/categories/?${params.toString()}`;
      const response = await axios.get(url, this.getAuthHeader());
      return response.data;
    } catch (error: any) {
      console.error('Error fetching categories:', error);
      throw error;
    }
  }

  /**
   * دریافت درخت سلسله‌مراتبی دسته‌بندی‌ها
   */
  async getCategoryTree(isPublicOnly = false): Promise<CategoryTreeNode[]> {
    try {
      const params = new URLSearchParams();
      if (isPublicOnly) params.append('is_public_only', 'true');

      const url = `${API_URL}/api/super-admin/categories/tree?${params.toString()}`;
      const response = await axios.get(url, this.getAuthHeader());
      return response.data;
    } catch (error: any) {
      console.error('Error fetching category tree:', error);
      throw error;
    }
  }

  /**
   * دریافت یک دسته‌بندی با ID
   */
  async getCategoryById(categoryId: string): Promise<Category> {
    try {
      const url = `${API_URL}/api/super-admin/categories/${categoryId}`;
      const response = await axios.get(url, this.getAuthHeader());
      return response.data;
    } catch (error: any) {
      console.error('Error fetching category:', error);
      throw error;
    }
  }

  /**
   * دریافت یک دسته‌بندی با slug
   */
  async getCategoryBySlug(slug: string): Promise<Category> {
    try {
      const url = `${API_URL}/api/super-admin/categories/slug/${slug}`;
      const response = await axios.get(url, this.getAuthHeader());
      return response.data;
    } catch (error: any) {
      console.error('Error fetching category by slug:', error);
      throw error;
    }
  }

  /**
   * ایجاد دسته‌بندی جدید
   */
  async createCategory(categoryData: CategoryCreate): Promise<Category> {
    try {
      const url = `${API_URL}/api/super-admin/categories/`;
      const response = await axios.post(url, categoryData, this.getAuthHeader());
      return response.data;
    } catch (error: any) {
      console.error('Error creating category:', error);
      throw error;
    }
  }

  /**
   * به‌روزرسانی دسته‌بندی
   */
  async updateCategory(
    categoryId: string,
    categoryData: CategoryUpdate,
    updateArticles = true
  ): Promise<Category> {
    try {
      const url = `${API_URL}/api/super-admin/categories/${categoryId}?update_articles=${updateArticles}`;
      const response = await axios.put(url, categoryData, this.getAuthHeader());
      return response.data;
    } catch (error: any) {
      console.error('Error updating category:', error);
      throw error;
    }
  }

  /**
   * حذف دسته‌بندی
   */
  async deleteCategory(
    categoryId: string,
    cascade = false,
    moveToParent = true
  ): Promise<CategoryDeleteResult> {
    try {
      const url = `${API_URL}/api/super-admin/categories/${categoryId}?cascade=${cascade}&move_to_parent=${moveToParent}`;
      const response = await axios.delete(url, this.getAuthHeader());
      return response.data;
    } catch (error: any) {
      console.error('Error deleting category:', error);
      throw error;
    }
  }

  /**
   * تبدیل string به slug (URL-friendly)
   */
  generateSlug(text: string): string {
    return text
      .toLowerCase()
      .trim()
      .replace(/[\s_]+/g, '-')        // Replace spaces and underscores with hyphens
      .replace(/[^\w\u0600-\u06FF-]/g, '') // Keep only alphanumeric, Persian, and hyphens
      .replace(/--+/g, '-')           // Replace multiple hyphens with single
      .replace(/^-+|-+$/g, '');       // Remove leading/trailing hyphens
  }
}

export default new CategoryService();
