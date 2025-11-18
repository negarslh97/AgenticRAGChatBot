'use client'

import React, { useState, useEffect, useMemo } from 'react'
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
import {
  Plus,
  Search,
  MoreHorizontal,
  Edit,
  Trash2,
  UserCheck,
  UserX
} from 'lucide-react'

interface User {
  id: string
  email: string
  full_name: string
  role: 'SuperAdmin' | 'Admin' | 'Customer' | 'Guest'
  is_active: boolean
  created_at: string
}

const columnHelper = createColumnHelper<User>()

const UserManagementPage: React.FC = () => {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [globalFilter, setGlobalFilter] = useState('')
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [dropdownOpen, setDropdownOpen] = useState<string | null>(null)

  // Helper functions for displaying selected values
  const getRoleDisplayText = (value: string) => {
    const roleLabels = {
      all: 'همه نقش‌ها',
      SuperAdmin: 'ادمین ارشد',
      Admin: 'ادمین',
      Customer: 'مشتری',
      Guest: 'مهمان'
    }
    return roleLabels[value as keyof typeof roleLabels] || 'همه نقش‌ها'
  }

  // Mock data for demonstration
  useEffect(() => {
    const mockUsers: User[] = [
      {
        id: '1',
        email: 'admin@sally.com',
        full_name: 'ادمین ارشد',
        role: 'SuperAdmin',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z'
      },
      {
        id: '2',
        email: 'manager@sally.com',
        full_name: 'مدیر سیستم',
        role: 'Admin',
        is_active: true,
        created_at: '2024-01-02T00:00:00Z'
      },
      {
        id: '3',
        email: 'customer@example.com',
        full_name: 'مشتری نمونه',
        role: 'Customer',
        is_active: true,
        created_at: '2024-01-03T00:00:00Z'
      },
      {
        id: '4',
        email: 'inactive@example.com',
        full_name: 'کاربر غیرفعال',
        role: 'Customer',
        is_active: false,
        created_at: '2024-01-04T00:00:00Z'
      }
    ]

    // Simulate API call
    setTimeout(() => {
      setUsers(mockUsers)
      setLoading(false)
    }, 1000)
  }, [])

  const columns = useMemo<ColumnDef<User, any>[]>(
    () => [
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

          return (
            <Badge className={roleColors[role as keyof typeof roleColors]}>
              {roleLabels[role as keyof typeof roleLabels]}
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
    ],
    [dropdownOpen]
  )

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

  const handleAddUser = () => {
    alert('افزودن کاربر جدید - این قابلیت به زودی پیاده‌سازی خواهد شد')
  }

  const handleEditUser = (user: User) => {
    alert(`ویرایش کاربر: ${user.full_name} - این قابلیت به زودی پیاده‌سازی خواهد شد`)
  }

  const handleDeleteUser = (userId: string) => {
    // eslint-disable-next-line no-restricted-globals
    if (confirm('آیا از حذف این کاربر اطمینان دارید؟')) {
      alert(`حذف کاربر با ID: ${userId} - این قابلیت به زودی پیاده‌سازی خواهد شد`)
    }
  }

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
          <h1 className="text-2xl font-bold text-gray-900">مدیریت کاربران</h1>
          <p className="text-gray-600 mt-1">مدیریت و نظارت بر کاربران سیستم</p>
        </div>
        <Button onClick={handleAddUser} className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          افزودن کاربر جدید
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
            <SelectItem value="SuperAdmin">ادمین ارشد</SelectItem>
            <SelectItem value="Admin">ادمین</SelectItem>
            <SelectItem value="Customer">مشتری</SelectItem>
            <SelectItem value="Guest">مهمان</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={(table.getColumn('is_active')?.getFilterValue() as string) ?? 'all'}
          onValueChange={(value: string) =>
            table.getColumn('is_active')?.setFilterValue(value === 'all' ? '' : value === 'true')
          }
        >
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">همه وضعیت‌ها</SelectItem>
            <SelectItem value="true">فعال</SelectItem>
            <SelectItem value="false">غیرفعال</SelectItem>
          </SelectContent>
        </Select>
      </div>

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
                  هیچ کاربری یافت نشد.
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
          {table.getFilteredRowModel().rows.length} کاربر
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

export default UserManagementPage