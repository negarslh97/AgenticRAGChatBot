"use client"

import React, { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { knowledgeBaseService, type FileUploadResponse } from "../services/knowledgeBaseService"
import { Button } from "../components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card"
import { Input } from "../components/ui/input"
import toast from "react-hot-toast"
import { ArrowRight, Upload, FileText, FileImage, File, CheckCircle, AlertCircle, Loader2 } from "lucide-react"

const SuperAdminUploadPage: React.FC = () => {
  const navigate = useNavigate()
  const { user, isSuperAdmin, loading: authLoading } = useAuth()

  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<FileUploadResponse | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [hasNavigated, setHasNavigated] = useState(false)
  const [creatingArticle, setCreatingArticle] = useState(false)

  // AuthGuard authentication را چک می‌کند، نیازی به چک مجدد نیست

  const handleFileSelect = (file: File) => {
    // Check file type
    const allowedTypes = [
      'text/plain',
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'text/csv',
      'text/html',
      'text/htm'
    ]

    if (!allowedTypes.includes(file.type)) {
      toast.error("فرمت فایل پشتیبانی نمی‌شود. لطفاً از فرمت‌های متنی، PDF، Word، Excel یا CSV استفاده کنید.")
      return
    }

    // Check file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      toast.error("حجم فایل نباید بیشتر از ۱۰ مگابایت باشد.")
      return
    }

    setSelectedFile(file)
    setUploadResult(null)
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      toast.error("لطفاً ابتدا یک فایل انتخاب کنید.")
      return
    }

    setUploading(true)
    try {
      const result = await knowledgeBaseService.uploadAndConvertFile(selectedFile)
      setUploadResult(result)

      if (result.success) {
        toast.success(`فایل ${result.title} با موفقیت تبدیل شد و متادیتای هوش مصنوعی تولید گردید! ✨`)
      } else {
        toast.error(result.error || "خطا در آپلود فایل")
      }
    } catch (error: any) {
      console.error("Upload error:", error)
      toast.error(error.message || "خطا در آپلود فایل")
      setUploadResult({
        success: false,
        title: selectedFile.name,
        markdown_content: "",
        summary: "",
        suggested_tags: [],
        error: error.message || "خطا در آپلود فایل"
      })
    } finally {
      setUploading(false)
    }
  }

  const handleCreateArticle = async () => {
    if (!uploadResult || !uploadResult.success) {
      toast.error("نتیجه آپلود یافت نشد.")
      return
    }

    setCreatingArticle(true)
    try {
      const articleData = {
        title: uploadResult.title,
        content_markdown: uploadResult.markdown_content,
        summary: uploadResult.summary || `محتوای استخراج شده از فایل: ${uploadResult.title}`,
        tag_names: uploadResult.suggested_tags || [],
        status: "draft" as const
      }

      const createdArticle = await knowledgeBaseService.createArticle(articleData)
      toast.success(`مقاله "${createdArticle.title}" با موفقیت ایجاد شد!`)

      // Reset the upload result and navigate to knowledge base
      setUploadResult(null)
      setSelectedFile(null)
      navigate("/super-admin/knowledge-base")

    } catch (error: any) {
      console.error("Create article error:", error)
      toast.error(error.message || "خطا در ایجاد مقاله")
    } finally {
      setCreatingArticle(false)
    }
  }

  const getFileIcon = (fileType: string) => {
    if (fileType.includes('pdf')) return <FileText className="h-12 w-12 text-red-500" />
    if (fileType.includes('word') || fileType.includes('document')) return <FileText className="h-12 w-12 text-blue-500" />
    if (fileType.includes('excel') || fileType.includes('spreadsheet')) return <FileText className="h-12 w-12 text-green-500" />
    if (fileType.includes('image')) return <FileImage className="h-12 w-12 text-purple-500" />
    return <File className="h-12 w-12 text-gray-500" />
  }

  const getFileTypeName = (fileType: string) => {
    if (fileType.includes('pdf')) return 'PDF'
    if (fileType.includes('word') || fileType.includes('document')) return 'Word'
    if (fileType.includes('excel') || fileType.includes('spreadsheet')) return 'Excel'
    if (fileType.includes('csv')) return 'CSV'
    if (fileType.includes('text')) return 'متن'
    return 'نامشخص'
  }

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!isSuperAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">دسترسی غیرمجاز</h2>
          <p className="text-gray-600">فقط سوپر ادمین‌ها می‌توانند به این صفحه دسترسی داشته باشند.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8" dir="rtl">
      <div className="max-w-4xl mx-auto px-4">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-4">
            <Button
              variant="outline"
              onClick={() => navigate("/super-admin/knowledge-base")}
              className="flex items-center gap-2"
            >
              <ArrowRight className="h-4 w-4" />
              بازگشت به لیست مقالات
            </Button>
            <h1 className="text-3xl font-bold text-gray-900">آپلود فایل</h1>
          </div>
          <p className="text-gray-600">فایل‌های خود را آپلود کنید تا به صورت خودکار به مقاله تبدیل شوند.</p>
        </div>

        {/* Upload Area */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              آپلود فایل
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!selectedFile ? (
              <div
                className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
                  dragActive
                    ? 'border-blue-400 bg-blue-50'
                    : 'border-gray-300 hover:border-gray-400'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <Upload className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  فایل خود را بکشید و رها کنید
                </h3>
                <p className="text-gray-500 mb-4">
                  یا روی دکمه زیر کلیک کنید
                </p>
                <Input
                  type="file"
                  onChange={handleFileInputChange}
                  accept=".txt,.pdf,.docx,.doc,.xlsx,.xls,.csv,.html,.htm"
                  className="hidden"
                  id="file-upload"
                />
                <Button
                  onClick={() => document.getElementById('file-upload')?.click()}
                  className="flex items-center gap-2"
                >
                  <Upload className="h-4 w-4" />
                  انتخاب فایل
                </Button>
                <p className="text-xs text-gray-400 mt-4">
                  فرمت‌های پشتیبانی شده: TXT, PDF, Word, Excel, CSV (حداکثر ۱۰ مگابایت)
                </p>
              </div>
            ) : (
              <div className="text-center">
                <div className="flex justify-center mb-4">
                  {getFileIcon(selectedFile.type)}
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  {selectedFile.name}
                </h3>
                <p className="text-gray-500 mb-2">
                  {getFileTypeName(selectedFile.type)} • {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
                <div className="flex gap-2 justify-center">
                  <Button
                    onClick={handleUpload}
                    disabled={uploading}
                    className="flex items-center gap-2"
                  >
                    {uploading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        در حال آپلود...
                      </>
                    ) : (
                      <>
                        <Upload className="h-4 w-4" />
                        تبدیل فایل
                      </>
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => setSelectedFile(null)}
                    disabled={uploading}
                  >
                    انتخاب مجدد
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Upload Result */}
        {uploadResult && (
          <Card className={`mb-6 ${uploadResult.success ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {uploadResult.success ? (
                  <CheckCircle className="h-5 w-5 text-green-600" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-600" />
                )}
                {uploadResult.success ? 'تبدیل موفق' : 'خطا در تبدیل'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-gray-900 mb-1">عنوان:</h4>
                  <p className="text-gray-700">{uploadResult.title}</p>
                </div>

                {uploadResult.summary && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-1">خلاصه:</h4>
                    <p className="text-gray-700">{uploadResult.summary}</p>
                  </div>
                )}

                {uploadResult.suggested_tags && uploadResult.suggested_tags.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-1">برچسب‌های پیشنهادی:</h4>
                    <div className="flex flex-wrap gap-2">
                      {uploadResult.suggested_tags.map((tag, index) => (
                        <span key={index} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {uploadResult.success && (
                  <div className="flex gap-2 justify-end">
                    <Button
                      onClick={handleCreateArticle}
                      disabled={creatingArticle}
                      className="flex items-center gap-2"
                    >
                      {creatingArticle ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          در حال ایجاد مقاله...
                        </>
                      ) : (
                        <>
                          ایجاد مقاله
                          <ArrowRight className="h-4 w-4" />
                        </>
                      )}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => navigate("/super-admin/knowledge-base")}
                      className="flex items-center gap-2"
                    >
                      مشاهده مقالات
                    </Button>
                  </div>
                )}

                {uploadResult.error && (
                  <div className="bg-red-100 border border-red-300 rounded p-3">
                    <h4 className="font-medium text-red-900 mb-1">خطا:</h4>
                    <p className="text-red-800">{uploadResult.error}</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Supported Formats */}
        <Card>
          <CardHeader>
            <CardTitle>فرمت‌های پشتیبانی شده</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 border rounded">
                <FileText className="h-8 w-8 text-red-500 mx-auto mb-2" />
                <p className="text-sm">PDF</p>
              </div>
              <div className="text-center p-4 border rounded">
                <FileText className="h-8 w-8 text-blue-500 mx-auto mb-2" />
                <p className="text-sm">Word</p>
              </div>
              <div className="text-center p-4 border rounded">
                <FileText className="h-8 w-8 text-green-500 mx-auto mb-2" />
                <p className="text-sm">Excel</p>
              </div>
              <div className="text-center p-4 border rounded">
                <File className="h-8 w-8 text-gray-500 mx-auto mb-2" />
                <p className="text-sm">Text/CSV</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default SuperAdminUploadPage
