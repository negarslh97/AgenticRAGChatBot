"use client"

import React, { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { knowledgeBaseService } from "../services/knowledgeBaseService"
import { Button } from "../components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table"
import toast from "react-hot-toast"
import { ArrowRight, Database, RefreshCw, ChevronDown, ChevronRight } from "lucide-react"

interface WeaviateNode {
  uuid: string
  article_id: string
  title: string
  level: number
  content: string
  path: string
  order: number
}

interface WeaviateArticle {
  article_id: string
  nodes_count: number
  titles: string[]
}

interface WeaviateContents {
  total_nodes: number
  returned_nodes: number
  articles_count: number
  articles: WeaviateArticle[]
  nodes: WeaviateNode[]
}

interface NodeDetails {
  uuid: string
  properties: any
  vector: number[] | null
  vector_length: number
  metadata: {
    creation_time: string | null
    last_update_time: string | null
  }
}

const WeaviateContentsPage: React.FC = () => {
  const navigate = useNavigate()
  const { user, isSuperAdmin, loading: authLoading} = useAuth()
  const [contents, setContents] = useState<WeaviateContents | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedArticles, setExpandedArticles] = useState<Set<string>>(new Set())
  const [limit, setLimit] = useState(100)
  const [selectedNode, setSelectedNode] = useState<NodeDetails | null>(null)
  const [nodeDetailsLoading, setNodeDetailsLoading] = useState(false)

  const loadContents = async () => {
    setLoading(true)
    try {
      const data = await knowledgeBaseService.getWeaviateContents(limit)
      setContents(data)
    } catch (error: any) {
      toast.error("خطا در بارگذاری محتویات Weaviate")
      console.error("Error loading Weaviate contents:", error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!authLoading && isSuperAdmin && user) {
      loadContents()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, isSuperAdmin, user, limit])

  const toggleArticleExpand = (articleId: string) => {
    const newExpanded = new Set(expandedArticles)
    if (newExpanded.has(articleId)) {
      newExpanded.delete(articleId)
    } else {
      newExpanded.add(articleId)
    }
    setExpandedArticles(newExpanded)
  }

  const getNodesForArticle = (articleId: string): WeaviateNode[] => {
    if (!contents) return []
    return contents.nodes
      .filter(node => node.article_id === articleId)
      .sort((a, b) => a.order - b.order)
  }

  const handleNodeClick = async (nodeUuid: string) => {
    setNodeDetailsLoading(true)
    try {
      const details = await knowledgeBaseService.getWeaviateNodeDetails(nodeUuid)
      setSelectedNode(details)
    } catch (error: any) {
      toast.error("خطا در بارگذاری جزئیات گره")
      console.error("Error loading node details:", error)
    } finally {
      setNodeDetailsLoading(false)
    }
  }

  const closeNodeDetails = () => {
    setSelectedNode(null)
  }

  if (!isSuperAdmin) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">دسترسی غیرمجاز</h2>
        <p className="text-gray-600">فقط سوپر ادمین‌ها می‌توانند به این صفحه دسترسی داشته باشند.</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8" dir="rtl">
      <div className="max-w-7xl mx-auto px-4">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-4">
            <Button
              variant="outline"
              onClick={() => navigate("/super-admin/knowledge-base")}
              className="flex items-center gap-2"
            >
              <ArrowRight className="h-4 w-4" />
              بازگشت
            </Button>
            <div className="flex items-center gap-3">
              <Database className="h-8 w-8 text-blue-600" />
              <div>
                <h1 className="text-3xl font-bold text-gray-900">محتویات Weaviate</h1>
                <p className="text-gray-600">مشاهده و بررسی داده‌های ذخیره شده در دیتابیس وکتوری</p>
              </div>
            </div>
          </div>
        </div>

        {/* Statistics Cards */}
        {contents && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <Card>
              <CardContent className="p-4">
                <div className="text-center">
                  <p className="text-sm text-gray-600 mb-1">کل گره‌ها</p>
                  <p className="text-2xl font-bold text-blue-600">{contents.total_nodes}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="text-center">
                  <p className="text-sm text-gray-600 mb-1">مقالات</p>
                  <p className="text-2xl font-bold text-green-600">{contents.articles_count}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="text-center">
                  <p className="text-sm text-gray-600 mb-1">گره‌های نمایش داده شده</p>
                  <p className="text-2xl font-bold text-purple-600">{contents.returned_nodes}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="text-center">
                  <p className="text-sm text-gray-600 mb-1">میانگین گره به ازای مقاله</p>
                  <p className="text-2xl font-bold text-orange-600">
                    {contents.articles_count > 0 
                      ? (contents.total_nodes / contents.articles_count).toFixed(1)
                      : 0
                    }
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Controls */}
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">تعداد نمایش:</label>
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="border rounded px-3 py-1 text-sm"
            >
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
              <option value={500}>500</option>
            </select>
          </div>
          <Button
            onClick={loadContents}
            disabled={loading}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            {loading ? "در حال بارگذاری..." : "بروزرسانی"}
          </Button>
        </div>

        {/* Contents */}
        <Card>
          <CardHeader>
            <CardTitle>مقالات ذخیره شده در Weaviate</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">در حال بارگذاری محتویات...</p>
              </div>
            ) : !contents || contents.articles.length === 0 ? (
              <div className="text-center py-12">
                <Database className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">هیچ داده‌ای یافت نشد</h3>
                <p className="text-gray-500">هنوز هیچ مقاله‌ای در Weaviate ذخیره نشده است</p>
              </div>
            ) : (
              <div className="space-y-4">
                {contents.articles.map((article) => (
                  <div key={article.article_id} className="border rounded-lg overflow-hidden">
                    {/* Article Header */}
                    <button
                      onClick={() => toggleArticleExpand(article.article_id)}
                      className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 flex items-center justify-between transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        {expandedArticles.has(article.article_id) ? (
                          <ChevronDown className="h-5 w-5 text-gray-600" />
                        ) : (
                          <ChevronRight className="h-5 w-5 text-gray-600" />
                        )}
                        <div className="text-right">
                          <p className="font-medium text-gray-900">
                            {article.titles[0] || "بدون عنوان"}
                          </p>
                          <p className="text-sm text-gray-600">
                            شناسه: {article.article_id}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium">
                          {article.nodes_count} گره
                        </span>
                      </div>
                    </button>

                    {/* Article Nodes (Expandable) */}
                    {expandedArticles.has(article.article_id) && (
                      <div className="p-4 bg-white">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>سطح</TableHead>
                              <TableHead>عنوان</TableHead>
                              <TableHead>محتوا</TableHead>
                              <TableHead>مسیر</TableHead>
                              <TableHead>ترتیب</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {getNodesForArticle(article.article_id).map((node) => (
                              <TableRow 
                                key={node.uuid}
                                className="cursor-pointer hover:bg-blue-50 transition-colors"
                                onClick={() => handleNodeClick(node.uuid)}
                              >
                                <TableCell>
                                  <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-gray-800 text-sm font-medium">
                                    {node.level}
                                  </span>
                                </TableCell>
                                <TableCell className="font-medium">{node.title}</TableCell>
                                <TableCell className="text-sm text-gray-600 max-w-md truncate">
                                  {node.content}
                                </TableCell>
                                <TableCell className="text-xs text-gray-500">{node.path}</TableCell>
                                <TableCell className="text-center">{node.order}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Node Details Modal */}
        {selectedNode && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={closeNodeDetails}>
            <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
              <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
                <h2 className="text-xl font-bold">جزئیات گره</h2>
                <button
                  onClick={closeNodeDetails}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>

              <div className="p-6 space-y-4">
                {nodeDetailsLoading ? (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">در حال بارگذاری...</p>
                  </div>
                ) : (
                  <>
                    {/* UUID */}
                    <div className="border-b pb-3">
                      <h3 className="text-sm font-semibold text-gray-700 mb-1">شناسه UUID</h3>
                      <p className="font-mono text-sm bg-gray-100 p-2 rounded">{selectedNode.uuid}</p>
                    </div>

                    {/* Properties */}
                    <div className="border-b pb-3">
                      <h3 className="text-sm font-semibold text-gray-700 mb-2">ویژگی‌ها</h3>
                      <div className="bg-gray-50 p-4 rounded space-y-2">
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <span className="text-xs text-gray-600">عنوان:</span>
                            <p className="font-medium">{selectedNode.properties.title}</p>
                          </div>
                          <div>
                            <span className="text-xs text-gray-600">سطح:</span>
                            <p className="font-medium">
                              {selectedNode.properties.level}
                              {selectedNode.properties.level === 0 && " (Root Node)"}
                            </p>
                          </div>
                          <div>
                            <span className="text-xs text-gray-600">شناسه مقاله:</span>
                            <p className="font-mono text-xs">{selectedNode.properties.article_id}</p>
                          </div>
                          <div>
                            <span className="text-xs text-gray-600">مسیر:</span>
                            <p className="font-medium">{selectedNode.properties.path}</p>
                          </div>
                          <div>
                            <span className="text-xs text-gray-600">شناسه والد (Parent ID):</span>
                            <p className="font-mono text-xs">
                              {selectedNode.properties.parent_id === "-1" 
                                ? <span className="text-red-600 font-semibold">-1 (ریشه)</span>
                                : selectedNode.properties.parent_id
                              }
                            </p>
                          </div>
                          <div>
                            <span className="text-xs text-gray-600">ترتیب:</span>
                            <p className="font-medium">{selectedNode.properties.order}</p>
                          </div>
                          <div>
                            <span className="text-xs text-gray-600">شناسه گره:</span>
                            <p className="font-mono text-xs">{selectedNode.properties.node_id}</p>
                          </div>
                        </div>
                        <div className="mt-3">
                          <span className="text-xs text-gray-600">محتوا:</span>
                          <p className="text-sm mt-1 bg-white p-3 rounded border max-h-32 overflow-auto">
                            {selectedNode.properties.content || "بدون محتوا"}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Vector Information */}
                    <div className="border-b pb-3">
                      <h3 className="text-sm font-semibold text-gray-700 mb-2">اطلاعات Vector</h3>
                      <div className="bg-blue-50 p-4 rounded">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm text-gray-700">طول Vector:</span>
                          <span className="font-bold text-blue-600">{selectedNode.vector_length} بعد</span>
                        </div>
                        {selectedNode.vector && selectedNode.vector.length > 0 && (
                          <div className="mt-3">
                            <details className="cursor-pointer">
                              <summary className="text-sm text-blue-600 hover:text-blue-800">
                                نمایش {selectedNode.vector_length} مقدار vector
                              </summary>
                              <div className="mt-2 bg-white p-3 rounded border max-h-48 overflow-auto">
                                <pre className="text-xs font-mono whitespace-pre-wrap">
                                  {JSON.stringify(selectedNode.vector.slice(0, 50), null, 2)}
                                  {selectedNode.vector.length > 50 && <div className="text-gray-500 mt-2">... و {selectedNode.vector.length - 50} مقدار دیگر</div>}
                                </pre>
                              </div>
                            </details>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Metadata */}
                    <div>
                      <h3 className="text-sm font-semibold text-gray-700 mb-2">متادیتا</h3>
                      <div className="bg-gray-50 p-4 rounded space-y-2">
                        <div>
                          <span className="text-xs text-gray-600">زمان ایجاد:</span>
                          <p className="text-sm">{selectedNode.metadata.creation_time ? new Date(selectedNode.metadata.creation_time).toLocaleString('fa-IR') : 'نامشخص'}</p>
                        </div>
                        <div>
                          <span className="text-xs text-gray-600">آخرین بروزرسانی:</span>
                          <p className="text-sm">{selectedNode.metadata.last_update_time ? new Date(selectedNode.metadata.last_update_time).toLocaleString('fa-IR') : 'نامشخص'}</p>
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </div>

              <div className="sticky bottom-0 bg-gray-50 border-t px-6 py-4">
                <Button onClick={closeNodeDetails} className="w-full">
                  بستن
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default WeaviateContentsPage

