"use client"

import { useState, useEffect } from "react"
import { knowledgeBaseService, ArticleHistoryItem } from "../services/knowledgeBaseService"
import { Button } from "./ui/button"
import { toast } from "react-hot-toast"

interface ArticleHistoryProps {
  articleId: string
}

const ArticleHistory: React.FC<ArticleHistoryProps> = ({ articleId }) => {
  const [history, setHistory] = useState<ArticleHistoryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [expandedCommit, setExpandedCommit] = useState<string | null>(null)

  useEffect(() => {
    loadHistory()
  }, [articleId])

  const loadHistory = async () => {
    setLoading(true)
    try {
      const historyData = await knowledgeBaseService.getArticleHistory(articleId)
      setHistory(historyData)
    } catch (error: any) {
      toast.error("خطا در بارگذاری تاریخچه مقاله")
      console.error("Error loading article history:", error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('fa-IR')
  }

  const toggleExpand = (commitHash: string) => {
    setExpandedCommit(expandedCommit === commitHash ? null : commitHash)
  }

  if (loading) {
    return (
      <div className="card p-6">
        <h3 className="text-lg font-bold mb-4">تاریخچه مقاله</h3>
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="text-sm text-gray-600 mt-2">در حال بارگذاری تاریخچه...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="card p-6">
      <h3 className="text-lg font-bold mb-4">تاریخچه مقاله</h3>
      
      {history.length === 0 ? (
        <div className="text-center py-4">
          <p className="text-gray-600">تاریخچه‌ای برای این مقاله موجود نیست</p>
        </div>
      ) : (
        <div className="space-y-3">
          {history.map((item) => (
            <div key={item.commit_hash} className="border border-gray-200 rounded-lg p-4">
              <div 
                className="flex justify-between items-center cursor-pointer"
                onClick={() => toggleExpand(item.commit_hash)}
              >
                <div className="flex-1">
                  <h4 className="font-medium text-sm">{item.message}</h4>
                  <p className="text-xs text-gray-600 mt-1">
                    توسط {item.author_name} ({item.author_email})
                  </p>
                  <p className="text-xs text-gray-500">{formatDate(item.timestamp)}</p>
                </div>
                <div className="text-xs text-gray-400">
                  {item.commit_hash.substring(0, 7)}
                </div>
              </div>
              
              {expandedCommit === item.commit_hash && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                  {item.changes && item.changes.length > 0 ? (
                    <div>
                      <h5 className="text-sm font-medium mb-2">تغییرات:</h5>
                      <ul className="text-xs space-y-1">
                        {item.changes.map((change, index) => (
                          <li key={index} className="text-gray-600">• {change}</li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <p className="text-xs text-gray-600">هیچ تغییر خاصی ثبت نشده است</p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      
      <Button
        onClick={loadHistory}
        variant="secondary"
        className="w-full mt-4"
      >
        بارگذاری مجدد تاریخچه
      </Button>
    </div>
  )
}

export default ArticleHistory