// import axios from "axios"

// const API_BASE_URL = "http://localhost:8000"

// Removed duplicate User interface, using the one from types/user.ts

// export interface LoginResponse {
//   access_token: string
//   token_type: string
//   user: User
// }

// // Create axios instance with interceptors
// const api = axios.create({
//   baseURL: API_BASE_URL,
// })

// // Add token to requests
// api.interceptors.request.use((config) => {
//   const token = localStorage.getItem("token")
//   if (token) {
//     config.headers.Authorization = `Bearer ${token}`
//   }
//   return config
// })

// // Handle token expiration
// api.interceptors.response.use(
//   (response) => response,
//   (error) => {
//     if (error.response?.status === 401) {
//       localStorage.removeItem("token")
//       window.location.href = "/login"
//     }
//     return Promise.reject(error)
//   },
// )

// export const authService = {
//   async login(email: string, password: string): Promise<LoginResponse> {
//     const formData = new FormData()
//     formData.append("username", email)
//     formData.append("password", password)

//     const response = await api.post("/api/auth/login", formData)
//     return response.data
//   },

//   async register(email: string, password: string, fullName: string): Promise<User> {
//     const formData = new FormData()
//     formData.append("username", email)
//     formData.append("password", password)

//     const response = await api.post("/api/auth/register", formData)
//     return response.data
//   },

//   async getCurrentUser(): Promise<User> {
//     const response = await api.get("/auth/me")
//     return response.data
//   },

//   async logout(): Promise<void> {
//     try {
//       await api.post("/auth/logout")
//     } catch (error) {
//       // Ignore errors on logout
//     }
//   },
// }

// export default api











// src/services/authService.ts

import axios from "axios";
import { User } from "../types/user";

const API_BASE_URL = "http://localhost:8000";

// ===================================================================================
// ١. اینترفیس User برای مطابقت با پاسخ بک‌اند اصلاح شد
// فیلد 'role' حذف و 'role_id' به عنوان فیلد اختیاری اضافه شد
// ===================================================================================
export { type User } from "../types/user"

// ===================================================================================
// ٢. اینترفیس LoginResponse برای مطابقت کامل با پاسخ بک‌اند بازنویسی شد
// ===================================================================================
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_type: "admin" | "customer"; // این فیلد جدید از بک‌اند می‌آید
  user: User;
}

// ===================================================================================
// این بخش نیازی به تغییر نداشت و صحیح است
// ===================================================================================
const api = axios.create({
  baseURL: API_BASE_URL,
});

// اضافه کردن توکن به هدر درخواست‌ها
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// مدیریت خطای 401 برای خروج خودکار کاربر
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      // برای جلوگیری از ریدایرکت‌های بی‌نهایت، چک می‌کنیم که در صفحه لاگین نباشیم
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
// ===================================================================================

export const authService = {
  /**
   * ٣. تابع لاگین: آدرس API به /api/auth/login اصلاح شد
   */
  async login(email: string, password: string): Promise<LoginResponse> {
    const formData = new FormData();
    formData.append("username", email);
    formData.append("password", password);

    const response = await api.post<LoginResponse>("/api/auth/login", formData);
    // ذخیره توکن در localStorage پس از لاگین موفق
    if (response.data.access_token) {
      localStorage.setItem("token", response.data.access_token);
    }
    return response.data;
  },

  /**
   * ٤. تابع ثبت‌نام:
   * - آدرس API به /api/auth/register/customer اصلاح شد
   * - ارسال full_name به بک‌اند اضافه شد
   * - روش ارسال داده به JSON تغییر یافت (رایج‌تر برای FastAPI)
   */
  async register(email: string, password: string, fullName: string): Promise<User> {
    const response = await api.post<User>("/api/auth/register/customer", {
      email,
      password,
      full_name: fullName,
    });
    return response.data;
  },

  /**
   * ٥. تابع گرفتن کاربر فعلی:
   * - آدرس API به /api/auth/me اصلاح شد
   *   (مطابق با endpoint واقعی در بک‌اند)
   */
  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>("/api/auth/me");
    return response.data;
  },

  /**
   * ٦. تابع خروج:
   * - آدرس API به /api/auth/logout اصلاح شد
   * - توکن از localStorage حذف می‌شود
   */
  async logout(): Promise<void> {
    localStorage.removeItem("token");
    try {
      // این درخواست به بک‌اند اطلاع می‌دهد که کاربر خارج شده است
      await api.post("/api/auth/logout");
    } catch (error) {
      // خطا در اینجا نادیده گرفته می‌شود چون کاربر در هر صورت از فرانت‌اند خارج شده
    }
  },
};

export default api;