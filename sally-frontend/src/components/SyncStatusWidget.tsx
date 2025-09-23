"use client"

import { useState, useEffect } from "react"
import { knowledgeBaseService, SyncStatusResponse } from "../services/knowledgeBaseService"
import { toast } from "react-hot-toast"

const SyncStatusWidget: React.FC = () => {
  const [status, setStatus] = useState<SyncStatusResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)

  useEffect(() => {
    if (autoRefresh) {
      loadStatus()
      const interval = setInterval(loadStatus, 30000) // Refresh every 30 seconds
      return () => clearInterval(interval)
    }
  }, [autoRefresh])

  const loadStatus = async () => {
    setLoading(true)
    try {
      const statusData = await knowledgeBaseService.getSyncStatus()
      setStatus(statusData)
    } catch (error: any) {
      toast.error("خطا در بارگذاری وضعیت همگام‌سازی")
      console.error("Error loading sync status:", error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return "هرگز"
    return new Date(dateString).toLocaleString('fa-IR')
  }

  const getStatusColor = (healthStatus: string) => {
    switch (healthStatus) {
      case "healthy":
        return "bg-green-100 text-green-800 border-green-200"
      case "warning":
        return "bg-yellow-100 text-yellow-800 border-yellow-200"
      case "error":
        return "bg-red-100 text-red-800 border-red-200"
      default:
        return "bg-gray-100 text-gray-800 border-gray-200"
    }
  }

  const getStatusText = (healthStatus: string) => {
    switch (healthStatus) {
      case "healthy":
        return "سالم"
      case "warning":
        return "هشدار"
      case "error":
        return "خطا"
      default:
        return "نامشخص"
    }
  }

  return (
    <div className="card p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-lg font-bold">وضعیت همگام‌سازی</h3>
        <div className="flex items-center space-x-2">
          <button
            onClick={loadStatus}
            disabled={loading}
            className="btn-secondary text-sm px-3 py-1"
          >
            {loading ? "..." : "بروزرسانی"}
          </button>
          <label className="flex items-center text-sm">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="mr-1"
            />
            بروزرسانی خودکار
          </label>
        </div>
      </div>

      {status ? (
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">وضعیت:</span>
            <span className={`px-2 py-1 rounded-full text-xs border ${getStatusColor(status.health_status)}`}>
              {getStatusText(status.health_status)}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">آخرین همگام‌سازی:</span>
            <span className="text-sm text-gray-600">{formatDate(status.last_sync)}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">عملیات در انتظار:</span>
            <span className="text-sm text-gray-600">{status.pending_operations} مورد</span>
          </div>

          {status.pending_operations > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded p-2">
              <p className="text-yellow-800 text-sm">
                {status.pending_operations} عملیات همگام‌سازی در صف انتظار هستند.
              </p>
            </div>
          )}

          {status.health_status === "error" && (
            <div className="bg-red-50 border border-red-200 rounded p-2">
              <p className="text-red-800 text-sm">
                خطا در همگام‌سازی. لطفاً وضعیت را بررسی کنید.
              </p>
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto"></div>
          <p className="text-sm text-gray-600 mt-2">در حال بارگذاری وضعیت...</p>
        </div>
      )}

      <div className="mt-4 pt-3 border-t border-gray-200">
        <p className="text-xs text-gray-500">
          سیستم Docs-as-Code به طور خودکار تغییرات را با مخزن Git همگام می‌کند.
        </p>
      </div>
    </div>
  )
}

export default SyncStatusWidget