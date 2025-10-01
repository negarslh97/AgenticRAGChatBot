"use client"

import { useState, useEffect } from "react"
import { knowledgeBaseService, SyncStatusResponse } from "../services/knowledgeBaseService"
import toast from "react-hot-toast"
import { RefreshCw, CheckCircle, AlertCircle, Clock } from "lucide-react"

const SyncStatusWidget: React.FC = () => {
  const [status, setStatus] = useState<SyncStatusResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [syncCheckLoading, setSyncCheckLoading] = useState(false)
  const [syncStatus, setSyncStatus] = useState<{
    total_published: number
    synced: number
    not_synced: number
    sync_percentage: number
  } | null>(null)
  const [isSyncing, setIsSyncing] = useState(false)

  useEffect(() => {
    if (autoRefresh) {
      loadStatus()
      checkSyncStatus()
      const interval = setInterval(() => {
        loadStatus()
        if (!isSyncing) {
          checkSyncStatus()
        }
      }, 30000) // Refresh every 30 seconds
      return () => clearInterval(interval)
    }
  }, [autoRefresh, isSyncing])

  const loadStatus = async () => {
    setLoading(true)
    try {
      const statusData = await knowledgeBaseService.getSyncStatus()
      setStatus(statusData)
    } catch (error: any) {
      console.error("Error loading sync status:", error)
    } finally {
      setLoading(false)
    }
  }

  const checkSyncStatus = async () => {
    setSyncCheckLoading(true)
    try {
      const syncData = await knowledgeBaseService.checkArticlesSyncStatus()
      setSyncStatus(syncData)
    } catch (error: any) {
      console.error("Error checking sync status:", error)
    } finally {
      setSyncCheckLoading(false)
    }
  }

  const handleSyncAll = async (force: boolean = false) => {
    if (!force && syncStatus && syncStatus.not_synced === 0) {
      toast.success("همه مقالات از قبل همگام‌سازی شده‌اند!")
      return
    }

    setIsSyncing(true)
    try {
      const result = await knowledgeBaseService.syncAllArticlesToWeaviate(force)
      
      if (result.jobs_scheduled === 0) {
        toast.success(`همه مقالات قبلاً همگام‌سازی شده‌اند (${result.skipped} مقاله رد شد)`)
        setIsSyncing(false)
        return
      }
      
      toast.success(
        `${result.jobs_scheduled} عملیات در صف قرار گرفت` +
        (result.skipped > 0 ? ` (${result.skipped} مقاله قبلاً sync شده بود)` : '')
      )
      
      // Start monitoring progress
      monitorSyncProgress()
    } catch (error: any) {
      toast.error("خطا در شروع همگام‌سازی")
      setIsSyncing(false)
    }
  }

  const monitorSyncProgress = () => {
    const interval = setInterval(async () => {
      try {
        const statusData = await knowledgeBaseService.getSyncStatus()
        const syncData = await knowledgeBaseService.checkArticlesSyncStatus()
        
        setStatus(statusData)
        setSyncStatus(syncData)

        // If no pending operations and all synced, stop monitoring
        if (statusData.pending_operations === 0 && syncData.not_synced === 0) {
          clearInterval(interval)
          setIsSyncing(false)
          toast.success("✅ همگام‌سازی با موفقیت تکمیل شد!")
        }
      } catch (error) {
        console.error("Error monitoring sync progress:", error)
      }
    }, 3000) // Check every 3 seconds

    // Auto-stop after 5 minutes
    setTimeout(() => {
      clearInterval(interval)
      if (isSyncing) {
        setIsSyncing(false)
        toast("همگام‌سازی در حال انجام است...")
      }
    }, 300000)
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

  const getSyncPercentage = () => {
    if (!syncStatus || syncStatus.total_published === 0) return 100
    return syncStatus.sync_percentage
  }

  return (
    <div className="card p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-lg font-bold">وضعیت Weaviate</h3>
        <div className="flex items-center space-x-2 gap-2">
          <button
            onClick={() => {
              loadStatus()
              checkSyncStatus()
            }}
            disabled={loading || syncCheckLoading}
            className="btn-secondary text-sm px-3 py-1 flex items-center gap-1"
          >
            <RefreshCw className={`h-3 w-3 ${(loading || syncCheckLoading) ? 'animate-spin' : ''}`} />
            {loading || syncCheckLoading ? "..." : "بروزرسانی"}
          </button>
          <label className="flex items-center text-sm">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="mr-1"
            />
            خودکار
          </label>
        </div>
      </div>

      {status ? (
        <div className="space-y-3">
          {/* System Health Status */}
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">وضعیت سیستم:</span>
            <span className={`px-2 py-1 rounded-full text-xs border ${getStatusColor(status.health_status)}`}>
              {getStatusText(status.health_status)}
            </span>
          </div>

          {/* Sync Percentage */}
          {syncStatus && (
            <>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">وضعیت همگام‌سازی:</span>
                  <span className={`text-sm font-bold ${getSyncPercentage() === 100 ? 'text-green-600' : 'text-yellow-600'}`}>
                    {getSyncPercentage().toFixed(0)}%
                  </span>
                </div>
                
                {/* Progress Bar */}
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${
                      getSyncPercentage() === 100 ? 'bg-green-500' : 'bg-yellow-500'
                    }`}
                    style={{ width: `${getSyncPercentage()}%` }}
                  />
                </div>

                <div className="text-xs text-gray-600 flex justify-between">
                  <span>{syncStatus.synced} همگام‌سازی شده</span>
                  <span>{syncStatus.total_published} مقاله منتشر شده</span>
                </div>
              </div>

              {/* Sync Button */}
              {syncStatus.not_synced > 0 && (
                <button
                  onClick={() => handleSyncAll(false)}
                  disabled={isSyncing}
                  className={`w-full py-2 px-4 rounded-lg text-sm font-medium transition-all ${
                    isSyncing
                      ? 'bg-yellow-100 text-yellow-800 cursor-wait'
                      : 'bg-blue-500 text-white hover:bg-blue-600'
                  }`}
                >
                  {isSyncing ? (
                    <span className="flex items-center justify-center gap-2">
                      <Clock className="h-4 w-4 animate-spin" />
                      در حال همگام‌سازی... ({syncStatus.not_synced} مقاله)
                    </span>
                  ) : (
                    <span className="flex items-center justify-center gap-2">
                      <RefreshCw className="h-4 w-4" />
                      همگام‌سازی {syncStatus.not_synced} مقاله
                    </span>
                  )}
                </button>
              )}

              {syncStatus.not_synced === 0 && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                  <p className="text-green-800 text-sm flex items-center gap-2">
                    <CheckCircle className="h-4 w-4" />
                    همه مقالات با موفقیت در Weaviate ذخیره شده‌اند
                  </p>
                </div>
              )}
            </>
          )}

          {/* Pending Operations */}
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">عملیات در صف:</span>
            <span className={`text-sm font-semibold ${status.pending_operations > 0 ? 'text-yellow-600' : 'text-green-600'}`}>
              {status.pending_operations} مورد
            </span>
          </div>

          {status.pending_operations > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              <p className="text-yellow-800 text-sm flex items-center gap-2">
                <Clock className="h-4 w-4 animate-pulse" />
                {status.pending_operations} عملیات در حال پردازش
              </p>
            </div>
          )}

          {status.health_status === "error" && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-red-800 text-sm flex items-center gap-2">
                <AlertCircle className="h-4 w-4" />
                خطا در سیستم - لطفاً وضعیت را بررسی کنید
              </p>
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto"></div>
          <p className="text-sm text-gray-600 mt-2">در حال بارگذاری...</p>
        </div>
      )}

      <div className="mt-4 pt-3 border-t border-gray-200">
        <p className="text-xs text-gray-500">
          💡 مقالات منتشر شده به صورت خودکار در Weaviate ذخیره می‌شوند
        </p>
      </div>
    </div>
  )
}

export default SyncStatusWidget
