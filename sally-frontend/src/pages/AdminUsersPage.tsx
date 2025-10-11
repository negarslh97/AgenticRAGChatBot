'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { useAuth } from '../context/AuthContext'
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  ColumnDef,
  SortingState,
  ColumnFiltersState,
} from '@tanstack/react-table'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu'
import AdminUserModal from '../components/AdminUserModal'
import {
  Plus,
  Search,
  MoreHorizontal,
  Edit,
  Trash2,
  UserCheck,
  UserX
} from 'lucide-react'
import toast from 'react-hot-toast'

interface User {
  id: string
  email: string
  full_name: string
  role: {
    id: string
    name: string
    description?: string
  }
  is_active: boolean
  created_at: string
}

const columnHelper = createColumnHelper<User>()

const AdminUsersPage: React.FC = () => {
  const { user, loading: authLoading, isAuthenticated } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [globalFilter, setGlobalFilter] = useState('')
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [dropdownOpen, setDropdownOpen] = useState<string | null>(null)
  const [roles, setRoles] = useState<string[]>([]) // نقش‌های موجود در دیتابیس
  const [showForm, setShowForm] = useState(false) // نمایش/مخفی کردن فرم

  // Fetch roles from API
  const fetchRoles = async () => {
    try {
      const token = localStorage.getItem('token')
      if (!token) {
        throw new Error('No authentication token found')
      }

      console.log("fetchRoles: Fetching roles from API...");
      const response = await fetch('/api/admin/roles', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      console.log("fetchRoles: Roles received:", data);
      
      // استخراج نام نقش‌ها از داده دریافتی
      const roleNames = data.map((role: any) => role.name)
      console.log("fetchRoles: Extracted role names:", roleNames);
      
      // فیلتر کردن نقش‌هایی که برای ادمین‌ها مرتبط هستن
      const adminRoles = roleNames.filter((role: string) =>
        role === 'SuperAdmin' || role === 'Admin'
      )
      
      setRoles(adminRoles)
    } catch (error) {
      console.error('❌ Error fetching roles:', error)
      // در صورت خطا، نقش‌های پیش‌فرض رو استفاده کن
      setRoles(['SuperAdmin', 'Admin'])
    }
  }

  // Helper functions for displaying selected values
  const getRoleDisplayText = (value: string | {id: string, name: string}) => {
    if (value === 'all') return 'همه نقش‌ها'
    
    // اگر value یه شیء باشه (از جدول)، نام نقش رو استخراج کن
    const roleName = typeof value === 'object' ? value.name : value
    
    // بررسی اینکه آیا نقش در لیست نقش‌های دیتابیس هست
    const foundRole = roles.find(role => role === roleName)
    if (foundRole) {
      // تبدیل نام نقش به فارسی
      const roleLabels: { [key: string]: string } = {
        'SuperAdmin': 'ادمین ارشد',
        'Admin': 'ادمین',
        'Customer': 'مشتری',
        'Guest': 'مهمان'
      }
      return roleLabels[roleName] || roleName
    }
    
    return roleName
  }

  const getStatusDisplayText = (value: string | boolean) => {
    const statusLabels = {
      all: 'همه وضعیت‌ها',
      true: 'فعال',
      false: 'غیرفعال'
    }
    return statusLabels[value as keyof typeof statusLabels] || 'همه وضعیت‌ها'
  }

  // Fetch admins from API
  const fetchAdmins = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem('token')
      console.log("fetchAdmins: Starting with token:", !!token);
      
      if (!token) {
        console.log("❌ fetchAdmins: No token found");
        throw new Error('No authentication token found')
      }
      
      console.log("✅ fetchAdmins: Token found, proceeding with request...");

      const params = new URLSearchParams()
      if (globalFilter) params.append('search', globalFilter)
      
      // فیلتر وضعیت - تبدیل boolean به string
      const isActiveFilter = table.getColumn('is_active')?.getFilterValue()
      if (isActiveFilter !== undefined && isActiveFilter !== '') {
        params.append('is_active', String(isActiveFilter))
      }
      
      // فیلتر نقش - تبدیل به رشته برای ارسال به API
      const roleFilter = table.getColumn('role')?.getFilterValue()
      if (roleFilter && roleFilter !== 'all') {
        params.append('role_name', String(roleFilter))
      }

      console.log("fetchAdmins: Sending request to /api/admin/admins");
      const response = await fetch(`/api/admin/admins?${params}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      })
      console.log("fetchAdmins: Response received, status:", response.status);

      if (!response.ok) {
        console.log("❌ fetchAdmins: Response not OK, status:", response.status);
        const errorText = await response.text()
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`)
      }
      
      console.log("✅ fetchAdmins: Response OK, parsing data...");

      const data = await response.json()
      console.log("✅ fetchAdmins: Data parsed successfully, count:", data.length);
      console.log("✅ fetchAdmins: Full data structure:", data);
      
      // بررسی ساختار داده دریافتی
      if (data && data.length > 0) {
        console.log("fetchAdmins: First user data:", data[0]);
        console.log("fetchAdmins: First user role:", data[0]?.role);
      }
      
      setUsers(data)
    } catch (error) {
      console.error('❌ fetchAdmins: Error fetching admins:', error)
      // Fallback to empty array
      setUsers([])
    } finally {
      console.log("fetchAdmins: Finished");
      setLoading(false)
    }
  }

  const columns = useMemo<ColumnDef<User, any>[]>(() => [
    columnHelper.accessor('full_name', {
      header: 'نام',
      cell: (info) => (
        <div className="font-medium">{info.getValue()}</div>
      ),
    }),
    columnHelper.accessor('email', {
      header: 'ایمیل',
      cell: (info) => (
        <div className="text-sm text-gray-600">{info.getValue()}</div>
      ),
    }),
    columnHelper.accessor('role', {
      header: 'نقش',
      cell: (info) => {
        const role = info.getValue()
        const roleColors = {
          SuperAdmin: 'bg-purple-100 text-purple-800',
          Admin: 'bg-blue-100 text-blue-800',
          Customer: 'bg-green-100 text-green-800',
          Guest: 'bg-gray-100 text-gray-800'
        }
        const roleLabels = {
          SuperAdmin: 'ادمین ارشد',
          Admin: 'ادمین',
          Customer: 'مشتری',
          Guest: 'مهمان'
        }

        // استخراج نام نقش از شیء role
        const roleName = role?.name || 'Unknown'
        
        return (
          <Badge className={roleColors[roleName as keyof typeof roleColors]}>
            {roleLabels[roleName as keyof typeof roleLabels]}
          </Badge>
        )
      },
      filterFn: 'equals',
    }),
    columnHelper.accessor('is_active', {
      header: 'وضعیت',
      cell: (info) => (
        <Badge variant={info.getValue() ? 'default' : 'secondary'}>
          {info.getValue() ? (
            <div className="flex items-center gap-1">
              <UserCheck className="h-3 w-3" />
              فعال
            </div>
          ) : (
            <div className="flex items-center gap-1">
              <UserX className="h-3 w-3" />
              غیرفعال
            </div>
          )}
        </Badge>
      ),
      filterFn: 'equals',
    }),
    columnHelper.display({
      id: 'actions',
      header: 'عملیات',
      cell: (info) => (
        <DropdownMenu
          open={dropdownOpen === info.row.original.id}
          onOpenChange={(open) => setDropdownOpen(open ? info.row.original.id : null)}
        >
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem
              onClick={() => {
                handleEditUser(info.row.original)
                setDropdownOpen(null)
              }}
              className="flex items-center gap-2"
            >
              <Edit className="h-4 w-4" />
              ویرایش
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => {
                handleDeleteUser(info.row.original.id)
                setDropdownOpen(null)
              }}
              className="flex items-center gap-2 text-red-600"
            >
              <Trash2 className="h-4 w-4" />
              حذف
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    }),
  ], [dropdownOpen])

  const table = useReactTable({
    data: users,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    state: {
      sorting,
      columnFilters,
      globalFilter,
    },
  })

  useEffect(() => {
    // لود نقش‌ها در اولین رندر
    fetchRoles()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    console.log("AdminUsersPage useEffect:", {
      authLoading,
      isAuthenticated,
      user: user?.email,
      hasToken: !!localStorage.getItem('token')
    });
    
    // فقط اگر احراز هویت کامل شده و کاربر لاگین کرده باشه، دیتا رو لود کن
    if (!authLoading && isAuthenticated && user) {
      console.log("✅ Conditions met, fetching admins...");
      fetchAdmins()
    } else {
      console.log("⏳ Waiting for auth to complete...");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [globalFilter, authLoading, isAuthenticated, user])

  // Real-time updates - poll every 30 seconds
  useEffect(() => {
    if (!authLoading && isAuthenticated && user) {
      const interval = setInterval(() => {
        fetchAdmins()
      }, 30000) // 30 seconds

      return () => clearInterval(interval)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, isAuthenticated, user])

  const handleAddUser = () => {
    setShowForm(true)
  }

  const handleFormSuccess = () => {
    setShowForm(false)
    // ریفرش لیست ادمین‌ها
    fetchAdmins()
    toast.success('ادمین جدید با موفقیت ایجاد شد')
  }

  const handleFormCancel = () => {
    setShowForm(false)
  }

  const handleEditUser = (user: User) => {
    alert(`ویرایش ادمین: ${user.full_name} - این قابلیت به زودی پیاده‌سازی خواهد شد`)
  }

  const handleDeleteUser = (userId: string) => {
    // eslint-disable-next-line no-restricted-globals
    if (confirm('آیا از حذف این ادمین اطمینان دارید؟')) {
      alert(`حذف ادمین با ID: ${userId} - این قابلیت به زودی پیاده‌سازی خواهد شد`)
    }
  }

  // اگر هنوز در حال چک کردن احراز هویت هستیم، لودینگ احراز هویت رو نشون بده
  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  // اگر احراز هویت انجام نشده یا کاربر لاگین نکرده، هیچی نشون نده (ProtectedRoute خودش هندل می‌کنه)
  if (!isAuthenticated || !user) {
    return null
  }

  // اگر در حال لود دیتا هستیم، لودینگ دیتا رو نشون بده
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">مدیریت ادمین‌ها</h1>
          <p className="text-gray-600 mt-1">مدیریت و نظارت بر ادمین‌های سیستم</p>
        </div>
        <Button onClick={handleAddUser} className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          افزودن ادمین جدید
        </Button>
      </div>

      {/* Filters and Search */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="جستجو بر اساس نام یا ایمیل..."
            value={globalFilter ?? ''}
            onChange={(event: React.ChangeEvent<HTMLInputElement>) => setGlobalFilter(String(event.target.value))}
            className="pl-10"
          />
        </div>

        <Select
          value={(table.getColumn('role')?.getFilterValue() as string) ?? 'all'}
          onValueChange={(value: string) =>
            table.getColumn('role')?.setFilterValue(value === 'all' ? '' : value)
          }
        >
          <SelectTrigger className="w-48">
            <SelectValue>
              {getRoleDisplayText((table.getColumn('role')?.getFilterValue() as string) ?? 'all')}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">همه نقش‌ها</SelectItem>
            {roles.map((role) => (
              <SelectItem key={role} value={role}>
                {getRoleDisplayText(role)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={String(table.getColumn('is_active')?.getFilterValue() ?? 'all')}
          onValueChange={(value: string) =>
            table.getColumn('is_active')?.setFilterValue(value === 'all' ? '' : value === 'true')
          }
        >
          <SelectTrigger className="w-48">
            <SelectValue>
              {getStatusDisplayText(String(table.getColumn('is_active')?.getFilterValue() ?? 'all'))}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">همه وضعیت‌ها</SelectItem>
            <SelectItem value="true">فعال</SelectItem>
            <SelectItem value="false">غیرفعال</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* مودال افزودن ادمین جدید */}
      <AdminUserModal
        isOpen={showForm}
        onClose={handleFormCancel}
        onSuccess={handleFormSuccess}
      />

      {/* Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center text-gray-500"
                >
                  هیچ ادمینی یافت نشد.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-700">
          نمایش {table.getFilteredSelectedRowModel().rows.length} از{' '}
          {table.getFilteredRowModel().rows.length} ادمین
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            قبلی
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            بعدی
          </Button>
        </div>
      </div>
    </div>
  )
}

export default AdminUsersPage