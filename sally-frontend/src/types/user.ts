export interface User {
  id?: string;
  email: string;
  full_name?: string;
  role?: "SuperAdmin" | "Admin" | "Customer" | "Guest";
  created_at?: string;
  is_active?: boolean;
}