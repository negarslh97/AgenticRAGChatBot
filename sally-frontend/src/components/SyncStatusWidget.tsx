"use client"

import { useState, useEffect } from "react"
import { knowledgeBaseService, SyncStatusResponse } from "../services/knowledgeBaseService"
import { Button } from "./ui/button"
import toast from "react-hot-toast"
import {
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Clock,
  FileText,
  FilePlus,
  FileEdit,
  Archive,
  AlertTriangle,
  Sparkles
} from "lucide-react"

interface DetailedSyncStatus {
  total_published: number
  new_articles: {
    count: number
    articles: Array<{
      id: string
      title: string
      created_at: string | null
      published_at: string | null
    }>
  }
  modified_articles: {
    count: number
    articles: Array<{
      id: string
      title: string
      updated_at: string
      last_synced_at: string
    }>
  }
  synced_articles: {
    count: number
  }
  archived_in_weaviate: {
    count: number
    articles: Array<{
      id: string
      title: string
      archived_at: string | null
    }>
  }
  needs_action: boolean
}

const SyncStatusWidget: React.FC = () => {
  const [status, setStatus] = useState<SyncStatusResponse | null>(null)
  const [detailedStatus, setDetailedStatus] = useState<DetailedSyncStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [isSyncing, setIsSyncing] = useState(false)
  const [showDetails, setShowDetails] = useState(false)

  useEffect(() => {
    loadStatus()
    
    if (autoRefresh) {
      const interval = setInterval(() => {
        loadStatus()
      }, 30000) // Refresh every 30 seconds
      return () => clearInterval(interval)
    }
  }, [autoRefresh])

  const loadStatus = async () => {
    setLoading(true)
    try {
      const [statusData, detailedData] = await Promise.all([
        knowledgeBaseService.getSyncStatus(),
        knowledgeBaseService.getDetailedSyncStatus()
      ])
      
      // Debug log
      console.log('📊 Sync Status Response:', {
        embedder_model: statusData.embedder_model,
        embedder_api_key_set: statusData.embedder_api_key_set,
        health_status: statusData.health_status
      })
      
      setStatus(statusData)
      setDetailedStatus(detailedData)
    } catch (error: any) {
      console.error("Error loading sync status:", error)
    } finally {
      setLoading(false)
    }
  }

  const handleSyncAll = async (force: boolean = false) => {
    if (!detailedStatus?.needs_action && !force) {
      toast.success("همه مقالات همگام‌سازی شده‌اند!")
      return
    }

    setIsSyncing(true)
    try {
      const result = await knowledgeBaseService.syncAllArticlesToWeaviate(force)
      
      if (result.jobs_scheduled === 0) {
        toast.success(`همه مقالات قبلاً همگام‌سازی شده‌اند`)
        setIsSyncing(false)
        return
      }
      
      toast.success(`${result.jobs_scheduled} عملیات در صف قرار گرفت`)
      
      // Monitor progress
      monitorSyncProgress()
    } catch (error: any) {
      toast.error("خطا در شروع همگام‌سازی")
      setIsSyncing(false)
    }
  }

  const handleRemoveArchived = async () => {
    if (!detailedStatus?.archived_in_weaviate.count) {
      toast.error("هیچ مقاله آرشیو شده‌ای برای حذف وجود ندارد")
      return
    }

    const confirmRemove = window.confirm(
      `آیا مطمئن هستید که می‌خواهید ${detailedStatus.archived_in_weaviate.count} مقاله آرشیو شده را از Weaviate حذف کنید؟`
    )

    if (!confirmRemove) return

    setIsSyncing(true)
    try {
      const result = await knowledgeBaseService.removeArchivedFromWeaviate()
      toast.success(result.message)
      // Reload status
      await loadStatus()
    } catch (error: any) {
      toast.error("خطا در حذف مقالات آرشیو شده")
    } finally {
      setIsSyncing(false)
    }
  }

  const monitorSyncProgress = () => {
    const interval = setInterval(async () => {
      try {
        const [statusData, detailedData] = await Promise.all([
          knowledgeBaseService.getSyncStatus(),
          knowledgeBaseService.getDetailedSyncStatus()
        ])
        
        setStatus(statusData)
        setDetailedStatus(detailedData)

        // If no pending operations and no actions needed, stop monitoring
        if (statusData.pending_operations === 0 && !detailedData.needs_action) {
          clearInterval(interval)
          setIsSyncing(false)
          toast.success("✅ همگام‌سازی تکمیل شد!")
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
      }
    }, 300000)
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
    <div className="card p-4 border-2 border-gray-200 rounded-lg shadow-sm">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-lg font-bold">وضعیت Weaviate</h3>
        <div className="flex items-center space-x-2 gap-2">
          <Button
            onClick={loadStatus}
            disabled={loading}
            variant="secondary"
            size="sm"
            className="text-sm px-3 py-1 flex items-center gap-1"
          >
            <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
            {loading ? "..." : "بروزرسانی"}
          </Button>
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

      {status && detailedStatus ? (
        <div className="space-y-3">
          {/* System Health Status */}
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">وضعیت سیستم:</span>
            <span className={`px-2 py-1 rounded-full text-xs border ${getStatusColor(status.health_status)}`}>
              {getStatusText(status.health_status)}
            </span>
          </div>

          {/* Embedder Model Info */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-blue-900 flex items-center gap-1">
                <Sparkles className="h-3 w-3" />
                مدل Embedding:
              </span>
              <span className={`px-2 py-0.5 rounded-full text-xs font-mono ${status.embedder_api_key_set ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                {status.embedder_api_key_set ? '🔑 متصل' : '❌ قطع'}
              </span>
            </div>
            <div className="text-xs text-blue-800 font-mono bg-white px-2 py-1 rounded border border-blue-200">
              {status.embedder_model}
            </div>
            {!status.embedder_api_key_set && (
              <p className="text-xs text-red-600 mt-2 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                API Key تنظیم نشده است
              </p>
            )}
          </div>

          {/* Sync Summary */}
          <div className="space-y-2 bg-gray-50 p-3 rounded-lg">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">همگام‌سازی:</span>
              <span className={`text-sm font-bold ${detailedStatus.needs_action ? 'text-yellow-600' : 'text-green-600'}`}>
                {detailedStatus.synced_articles.count} / {detailedStatus.total_published}
              </span>
            </div>
            
            {/* Progress Bar */}
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-500 ${
                  detailedStatus.needs_action ? 'bg-yellow-500' : 'bg-green-500'
                }`}
                style={{ 
                  width: `${(detailedStatus.synced_articles.count / (detailedStatus.total_published || 1)) * 100}%` 
                }}
              />
            </div>
          </div>

          {/* Alerts - New Articles */}
          {detailedStatus.new_articles.count > 0 && (
            <div className="bg-blue-50 border-l-4 border-blue-500 p-3 rounded">
              <div className="flex items-start gap-2">
                <FilePlus className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-semibold text-blue-900">
                    {detailedStatus.new_articles.count} مقاله جدید اضافه شده
                  </p>
                  <p className="text-xs text-blue-700 mt-1">
                    این مقالات هنوز به Weaviate اضافه نشده‌اند
                  </p>
                  {showDetails && detailedStatus.new_articles.articles.length > 0 && (
                    <ul className="mt-2 space-y-1 text-xs text-blue-800">
                      {detailedStatus.new_articles.articles.map((article) => (
                        <li key={article.id} className="flex items-center gap-1">
                          <FileText className="h-3 w-3" />
                          {article.title}
                        </li>
                      ))}
                      {detailedStatus.new_articles.count > detailedStatus.new_articles.articles.length && (
                        <li className="text-blue-600 italic">
                          و {detailedStatus.new_articles.count - detailedStatus.new_articles.articles.length} مقاله دیگر...
                        </li>
                      )}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Alerts - Modified Articles */}
          {detailedStatus.modified_articles.count > 0 && (
            <div className="bg-orange-50 border-l-4 border-orange-500 p-3 rounded">
              <div className="flex items-start gap-2">
                <FileEdit className="h-5 w-5 text-orange-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-semibold text-orange-900">
                    {detailedStatus.modified_articles.count} مقاله ویرایش شده
                  </p>
                  <p className="text-xs text-orange-700 mt-1">
                    این مقالات بعد از آخرین همگام‌سازی تغییر کرده‌اند
                  </p>
                  {showDetails && detailedStatus.modified_articles.articles.length > 0 && (
                    <ul className="mt-2 space-y-1 text-xs text-orange-800">
                      {detailedStatus.modified_articles.articles.map((article) => (
                        <li key={article.id} className="flex items-center gap-1">
                          <FileText className="h-3 w-3" />
                          {article.title}
                        </li>
                      ))}
                      {detailedStatus.modified_articles.count > detailedStatus.modified_articles.articles.length && (
                        <li className="text-orange-600 italic">
                          و {detailedStatus.modified_articles.count - detailedStatus.modified_articles.articles.length} مقاله دیگر...
                        </li>
                      )}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Alerts - Archived Articles */}
          {detailedStatus.archived_in_weaviate.count > 0 && (
            <div className="bg-purple-50 border-l-4 border-purple-500 p-3 rounded">
              <div className="flex items-start gap-2">
                <Archive className="h-5 w-5 text-purple-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-semibold text-purple-900">
                    {detailedStatus.archived_in_weaviate.count} مقاله آرشیو شده
                  </p>
                  <p className="text-xs text-purple-700 mt-1">
                    این مقالات باید از Weaviate حذف شوند
                  </p>
                  {showDetails && detailedStatus.archived_in_weaviate.articles.length > 0 && (
                    <ul className="mt-2 space-y-1 text-xs text-purple-800">
                      {detailedStatus.archived_in_weaviate.articles.map((article) => (
                        <li key={article.id} className="flex items-center gap-1">
                          <FileText className="h-3 w-3" />
                          {article.title}
                        </li>
                      ))}
                      {detailedStatus.archived_in_weaviate.count > detailedStatus.archived_in_weaviate.articles.length && (
                        <li className="text-purple-600 italic">
                          و {detailedStatus.archived_in_weaviate.count - detailedStatus.archived_in_weaviate.articles.length} مقاله دیگر...
                        </li>
                      )}
                    </ul>
                  )}
                  <button
                    onClick={handleRemoveArchived}
                    disabled={isSyncing}
                    className="mt-2 px-3 py-1 bg-purple-600 text-white text-xs rounded hover:bg-purple-700 disabled:opacity-50 transition-all"
                  >
                    حذف از Weaviate
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Show Details Toggle */}
          {(detailedStatus.new_articles.count > 0 || detailedStatus.modified_articles.count > 0 || detailedStatus.archived_in_weaviate.count > 0) && (
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="text-xs text-blue-600 hover:text-blue-800 underline"
            >
              {showDetails ? "پنهان کردن جزئیات" : "نمایش جزئیات"}
            </button>
          )}

          {/* Sync Button */}
          {detailedStatus.needs_action && (
            <button
              onClick={() => handleSyncAll(false)}
              disabled={isSyncing}
              className={`w-full py-2 px-4 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
                isSyncing
                  ? 'bg-yellow-100 text-yellow-800 cursor-wait'
                  : 'bg-blue-500 text-white hover:bg-blue-600'
              }`}
            >
              {isSyncing ? (
                <>
                  <Clock className="h-4 w-4 animate-spin" />
                  در حال همگام‌سازی...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4" />
                  همگام‌سازی {detailedStatus.new_articles.count + detailedStatus.modified_articles.count} مقاله
                </>
              )}
            </button>
          )}

          {/* Success Message */}
          {!detailedStatus.needs_action && status.pending_operations === 0 && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <p className="text-green-800 text-sm flex items-center gap-2">
                <CheckCircle className="h-4 w-4" />
                همه مقالات با موفقیت همگام‌سازی شده‌اند
              </p>
            </div>
          )}

          {/* Pending Operations */}
          {status.pending_operations > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              <p className="text-yellow-800 text-sm flex items-center gap-2">
                <Clock className="h-4 w-4 animate-pulse" />
                {status.pending_operations} عملیات در حال پردازش
              </p>
            </div>
          )}

          {/* Error Status */}
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
        <p className="text-xs text-gray-500 flex items-center gap-1">
          <AlertTriangle className="h-3 w-3" />
          مقالات منتشر شده به صورت خودکار در Weaviate ذخیره می‌شوند
        </p>
      </div>
    </div>
  )
}

export default SyncStatusWidget
