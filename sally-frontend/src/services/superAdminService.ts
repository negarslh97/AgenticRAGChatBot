// src/services/superAdminService.ts

import axios from "axios";
import api from "./authService";

// ============================================================================
// Interfaces for Super Admin API responses and requests
// ============================================================================

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface Role {
  id: string;
  name: string;
  description?: string;
  permissions: Permission[];
  is_active: boolean;
}

export interface Permission {
  permission_key: string;
  description?: string;
  resource: string;
  action: string;
}

export interface AdminCreateRequest {
  email: string;
  password: string;
  full_name: string;
  role_id: string;
}

export interface AdminUpdateRequest {
  full_name?: string;
  role_id?: string;
  is_active?: boolean;
}

export interface Customer {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
}

export interface CustomerUpdateRequest {
  full_name?: string;
  is_active?: boolean;
}

export interface ActivityLog {
  id: string;
  user_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details?: any;
  created_at: string;
}

export interface DashboardStats {
  users: {
    totalAdmins: number;
    totalCustomers: number;
  };
  // tickets: {
  //   open: number;
  //   awaitingReply: number;
  //   resolved: number;
  // };
  knowledgeBase: {
    published: number;
    drafts: number;
  };
}

export interface SystemSettings {
  [key: string]: any;
}

// ============================================================================
// Super Admin Service Functions
// ============================================================================

export const superAdminService = {
  // ============================================================================
  // User Management Functions
  // ============================================================================

  /**
   * دریافت لیست همه کاربران (فقط ادمین ارشد)
   */
  async getAllUsers(): Promise<User[]> {
    try {
      const response = await api.get<User[]>("/api/admin/users");
      return response.data;
    } catch (error) {
      console.error("Error fetching users:", error);
      throw new Error("خطا در دریافت کاربران");
    }
  },

  /**
   * ایجاد ادمین جدید (فقط ادمین ارشد)
   */
  async createAdmin(adminData: AdminCreateRequest): Promise<User> {
    try {
      const response = await api.post<User>("/api/admin/users", adminData);
      return response.data;
    } catch (error) {
      console.error("Error creating admin:", error);
      throw new Error("خطا در ایجاد ادمین");
    }
  },

  /**
   * بروزرسانی ادمین موجود (فقط ادمین ارشد)
   */
  async updateAdmin(adminId: string, adminData: AdminUpdateRequest): Promise<{ message: string }> {
    try {
      const response = await api.put<{ message: string }>(`/api/admin/users/${adminId}`, adminData);
      return response.data;
    } catch (error) {
      console.error("Error updating admin:", error);
      throw new Error("خطا در بروزرسانی ادمین");
    }
  },

  /**
   * حذف کاربر (فقط ادمین ارشد)
   */
  async deleteUser(userId: string): Promise<{ message: string }> {
    try {
      const response = await api.delete<{ message: string }>(`/api/admin/users/${userId}`);
      return response.data;
    } catch (error) {
      console.error("Error deleting user:", error);
      throw new Error("خطا در حذف کاربر");
    }
  },

  // ============================================================================
  // Role Management Functions
  // ============================================================================

  /**
   * دریافت لیست همه نقش‌ها
   */
  async getAllRoles(): Promise<Role[]> {
    try {
      const response = await api.get<Role[]>("/api/admin/roles");
      return response.data;
    } catch (error) {
      console.error("Error fetching roles:", error);
      throw new Error("خطا در دریافت نقش‌ها");
    }
  },

  /**
   * ایجاد نقش جدید
   */
  async createRole(roleData: { name: string; description?: string; permissions: Permission[] }): Promise<Role> {
    try {
      const response = await api.post<Role>("/api/admin/roles", roleData);
      return response.data;
    } catch (error) {
      console.error("Error creating role:", error);
      throw new Error("خطا در ایجاد نقش");
    }
  },

  /**
   * بروزرسانی نقش موجود
   */
  async updateRole(roleId: string, roleData: { description?: string; permissions?: Permission[]; is_active?: boolean }): Promise<{ message: string }> {
    try {
      const response = await api.put<{ message: string }>(`/api/admin/roles/${roleId}`, roleData);
      return response.data;
    } catch (error) {
      console.error("Error updating role:", error);
      throw new Error("خطا در بروزرسانی نقش");
    }
  },

  /**
   * حذف نقش
   */
  async deleteRole(roleId: string): Promise<{ message: string }> {
    try {
      const response = await api.delete<{ message: string }>(`/api/admin/roles/${roleId}`);
      return response.data;
    } catch (error) {
      console.error("Error deleting role:", error);
      throw new Error("خطا در حذف نقش");
    }
  },

  // ============================================================================
  // Customer Management Functions
  // ============================================================================

  /**
   * دریافت لیست همه مشتریان
   */
  async getAllCustomers(): Promise<Customer[]> {
    try {
      const response = await api.get<Customer[]>("/api/admin/customers");
      return response.data;
    } catch (error) {
      console.error("Error fetching customers:", error);
      throw new Error("خطا در دریافت مشتریان");
    }
  },

  /**
   * بروزرسانی مشتری
   */
  async updateCustomer(customerId: string, customerData: CustomerUpdateRequest): Promise<{ message: string }> {
    try {
      const response = await api.put<{ message: string }>(`/api/admin/customers/${customerId}`, customerData);
      return response.data;
    } catch (error) {
      console.error("Error updating customer:", error);
      throw new Error("خطا در بروزرسانی مشتری");
    }
  },

  /**
   * حذف مشتری
   */
  async deleteCustomer(customerId: string): Promise<{ message: string }> {
    try {
      const response = await api.delete<{ message: string }>(`/api/admin/customers/${customerId}`);
      return response.data;
    } catch (error) {
      console.error("Error deleting customer:", error);
      throw new Error("خطا در حذف مشتری");
    }
  },

  // ============================================================================
  // Dashboard and Statistics Functions
  // ============================================================================

  /**
   * دریافت آمار داشبورد
   */
  async getDashboardStats(): Promise<DashboardStats> {
    try {
      const response = await api.get<DashboardStats>("/api/admin/dashboard/stats");
      return response.data;
    } catch (error) {
      console.error("Error fetching dashboard stats:", error);
      throw new Error("خطا در دریافت آمار داشبورد");
    }
  },

  // ============================================================================
  // Activity Logs Functions
  // ============================================================================

  /**
   * دریافت لاگ‌های فعالیت سیستم (فقط ادمین ارشد)
   */
  async getActivityLogs(limit: number = 100): Promise<ActivityLog[]> {
    try {
      const response = await api.get<ActivityLog[]>(`/api/admin/activity-logs?limit=${limit}`);
      return response.data;
    } catch (error) {
      console.error("Error fetching activity logs:", error);
      throw new Error("خطا در دریافت لاگ‌های فعالیت");
    }
  },

  // ============================================================================
  // System Settings Functions
  // ============================================================================

  /**
   * دریافت تنظیمات سیستم
   */
  async getSystemSettings(): Promise<SystemSettings> {
    try {
      const response = await api.get<SystemSettings>("/api/admin/system-settings");
      return response.data;
    } catch (error) {
      console.error("Error fetching system settings:", error);
      throw new Error("خطا در دریافت تنظیمات سیستم");
    }
  },

  /**
   * بروزرسانی تنظیمات سیستم
   */
  async updateSystemSettings(settings: SystemSettings): Promise<{ message: string }> {
    try {
      const response = await api.put<{ message: string }>("/api/admin/system-settings", settings);
      return response.data;
    } catch (error) {
      console.error("Error updating system settings:", error);
      throw new Error("خطا در بروزرسانی تنظیمات سیستم");
    }
  },

  // ============================================================================
  // Utility Functions
  // ============================================================================

  /**
   * تبدیل نقش به متن فارسی
   */
  getRoleText(role: string): string {
    switch (role.toLowerCase()) {
      case "superadmin":
        return "ادمین ارشد";
      case "admin":
        return "ادمین";
      case "customer":
        return "مشتری";
      default:
        return role;
    }
  },

  /**
   * تبدیل وضعیت فعالیت به متن فارسی
   */
  getStatusText(isActive: boolean): string {
    return isActive ? "فعال" : "غیرفعال";
  },

  /**
   * تبدیل عملیات لاگ به متن فارسی
   */
  getActionText(action: string): string {
    const actionMap: { [key: string]: string } = {
      create_user: "ایجاد کاربر",
      update_user: "بروزرسانی کاربر",
      delete_user: "حذف کاربر",
      create_article: "ایجاد مقاله",
      update_article: "بروزرسانی مقاله",
      publish_article: "انتشار مقاله",
      delete_article: "حذف مقاله",
      login: "ورود به سیستم",
      logout: "خروج از سیستم",
    };

    return actionMap[action] || action;
  },

  /**
   * تبدیل نوع منبع به متن فارسی
   */
  getResourceTypeText(resourceType: string): string {
    const resourceMap: { [key: string]: string } = {
      user: "کاربر",
      admin: "ادمین",
      customer: "مشتری",
      article: "مقاله",
      role: "نقش",
    };

    return resourceMap[resourceType] || resourceType;
  },
};

export default superAdminService;
