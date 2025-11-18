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
import CategoryBadge from '../components/ui/category-badge'
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
import CategoryModal from '../components/CategoryModal'
import {
  Plus,
  Search,
  MoreHorizontal,
  Edit,
  Trash2,
  Eye,
  EyeOff,
  Folder,
  UserCheck,
  UserX
} from 'lucide-react'
import toast from 'react-hot-toast'
import categoryService, { Category, CategoryCreate, CategoryUpdate } from '../services/categoryService'

interface CategoryWithCounts extends Category {
  articles_count?: number
  children_count?: number
}

const columnHelper = createColumnHelper<CategoryWithCounts>()

const SuperAdminCategoriesPage: React.FC = () => {
  const { user, loading: authLoading, isAuthenticated } = useAuth()
  const [categories, setCategories] = useState<CategoryWithCounts[]>([])
  const [loading, setLoading] = useState(true)
  const [globalFilter, setGlobalFilter] = useState('')
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [dropdownOpen, setDropdownOpen] = useState<string | null>(null)
  const [showCategoryModal, setShowCategoryModal] = useState(false)
  const [categoryModalMode, setCategoryModalMode] = useState<'create' | 'edit'>('create')
  const [selectedCategory, setSelectedCategory] = useState<CategoryWithCounts | null>(null)

  const loadCategories = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem('token')
      if (!token) {
        throw new Error('No authentication token found')
      }

      const params = new URLSearchParams()
      if (globalFilter) params.append('search', globalFilter)
      
      // فیلتر وضعیت - تبدیل boolean به string
      const isActiveFilter = table.getColumn('is_public')?.getFilterValue()
      if (isActiveFilter !== undefined && isActiveFilter !== '') {
        params.append('is_public', String(isActiveFilter))
      }

      const response = await fetch(`/api/super-admin/categories?${params}`, {
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
      setCategories(data)
    } catch (error) {
      console.error('Error fetching categories:', error)
      toast.error('خطا در دریافت دسته‌بندی‌ها')
      setCategories([])
    } finally {
      setLoading(false)
    }
  }

  const columns = useMemo<ColumnDef<CategoryWithCounts, any>[]>(() => [
    columnHelper.accessor('name', {
      header: 'نام دسته‌بندی',
      cell: (info) => {
        const category = info.row.original
        return (
          <CategoryBadge color={category.color}>
            {info.getValue()}
          </CategoryBadge>
        )
      },
    }),
    columnHelper.accessor('slug', {
      header: 'Slug',
      cell: (info) => (
        <div className="text-sm text-gray-600">{info.getValue()}</div>
      ),
    }),
    columnHelper.accessor('parent_id', {
      header: 'دسته‌بندی والد',
      cell: (info) => {
        const parentId = info.getValue()
        if (!parentId) return '-'
        const parent = categories.find(c => c.id === parentId)
        return parent ? parent.name : 'نامشخص'
      },
    }),
    columnHelper.accessor('is_public', {
      header: 'وضعیت',
      cell: (info) => (
        <Badge variant={info.getValue() ? 'default' : 'secondary'}>
          {info.getValue() ? (
            <div className="flex items-center gap-1">
              <Eye className="h-3 w-3" />
              عمومی
            </div>
          ) : (
            <div className="flex items-center gap-1">
              <EyeOff className="h-3 w-3" />
              خصوصی
            </div>
          )}
        </Badge>
      ),
      filterFn: 'equals',
    }),
    columnHelper.accessor('articles_count', {
      header: 'تعداد مقالات',
      cell: (info) => (
        <div className="text-center">
          <Badge variant="outline">{info.getValue() || 0}</Badge>
        </div>
      ),
    }),
    columnHelper.accessor('children_count', {
      header: 'تعداد زیردسته',
      cell: (info) => (
        <div className="text-center">
          <Badge variant="outline">{info.getValue() || 0}</Badge>
        </div>
      ),
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
                handleEditCategory(info.row.original)
                setDropdownOpen(null)
              }}
              className="flex items-center gap-2"
            >
              <Edit className="h-4 w-4" />
              ویرایش
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => {
                handleDeleteCategory(info.row.original.id, info.row.original.name)
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
  ], [categories, dropdownOpen])

  const table = useReactTable({
    data: categories,
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
    if (!authLoading && isAuthenticated && user) {
      loadCategories()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [globalFilter, authLoading, isAuthenticated, user])

  const handleAddCategory = () => {
    setSelectedCategory(null)
    setCategoryModalMode('create')
    setShowCategoryModal(true)
  }

  const handleCategorySuccess = () => {
    setShowCategoryModal(false)
    loadCategories()
    toast.success(categoryModalMode === 'create' ? 'دسته‌بندی جدید با موفقیت ایجاد شد' : 'دسته‌بندی با موفقیت به‌روزرسانی شد')
  }

  const handleCategoryCancel = () => {
    setShowCategoryModal(false)
    setSelectedCategory(null)
  }

  const handleEditCategory = (category: CategoryWithCounts) => {
    setSelectedCategory(category)
    setCategoryModalMode('edit')
    setShowCategoryModal(true)
  }

  const handleDeleteCategory = (categoryId: string, categoryName: string) => {
    if (!window.confirm(`آیا از حذف دسته‌بندی "${categoryName}" اطمینان دارید؟\n\n⚠️ زیردسته‌ها به والد منتقل می‌شوند و دسته‌بندی از مقالات حذف می‌شود.`)) {
      return
    }
    
    // TODO: Implement delete functionality
    toast(`حذف دسته‌بندی با ID: ${categoryId} - این قابلیت به زودی پیاده‌سازی خواهد شد`)
  }

  // If auth is still loading, show loading spinner
  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  // If not authenticated, return null (ProtectedRoute handles this)
  if (!isAuthenticated || !user) {
    return null
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">مدیریت دسته‌بندی‌ها</h1>
          <p className="text-gray-600 mt-1">مدیریت دسته‌بندی‌های مقالات دانش‌بنیان</p>
        </div>
        <Button onClick={handleAddCategory} className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          دسته‌بندی جدید
        </Button>
      </div>

      {/* Filters and Search */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="جستجو بر اساس نام یا slug..."
            value={globalFilter ?? ''}
            onChange={(event: React.ChangeEvent<HTMLInputElement>) => setGlobalFilter(String(event.target.value))}
            className="pl-10"
          />
        </div>

        <Select
          value={String(table.getColumn('is_public')?.getFilterValue() ?? 'all')}
          onValueChange={(value: string) =>
            table.getColumn('is_public')?.setFilterValue(value === 'all' ? '' : value === 'true')
          }
        >
          <SelectTrigger className="w-48">
            <SelectValue>
              {String(table.getColumn('is_public')?.getFilterValue() ?? 'all') === 'all' 
                ? 'همه وضعیت‌ها' 
                : String(table.getColumn('is_public')?.getFilterValue() ?? 'all') === 'true' 
                  ? 'عمومی' 
                  : 'خصوصی'
              }
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">همه وضعیت‌ها</SelectItem>
            <SelectItem value="true">عمومی</SelectItem>
            <SelectItem value="false">خصوصی</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* مودال دسته‌بندی */}
      <CategoryModal
        isOpen={showCategoryModal}
        onClose={handleCategoryCancel}
        onSuccess={handleCategorySuccess}
        category={selectedCategory}
        mode={categoryModalMode}
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
                  هیچ دسته‌بندی‌ای یافت نشد.
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
          {table.getFilteredRowModel().rows.length} دسته‌بندی
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

export default SuperAdminCategoriesPage
