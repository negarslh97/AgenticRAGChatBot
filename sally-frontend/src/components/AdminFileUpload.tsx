"use client"

import { useState, useRef } from "react"
import { toast } from "react-hot-toast"
import api from "../services/authService"
import { useAuth } from "../context/AuthContext"

interface FileUploadProps {
  onUploadSuccess?: (data: any) => void
  onClose?: () => void
  disabled?: boolean
}

const AdminFileUpload: React.FC<FileUploadProps> = ({
  onUploadSuccess,
  onClose,
  disabled = false
}) => {
  const { user, loading: authLoading, isAuthenticated } = useAuth()
  const [isUploading, setIsUploading] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const supportedTypes = [
    { type: "application/pdf", ext: "PDF", icon: "📄" },
    { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ext: "XLSX", icon: "📊" },
    { type: "application/vnd.ms-excel", ext: "XLS", icon: "📈" },
    { type: "text/csv", ext: "CSV", icon: "📋" },
    { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ext: "DOCX", icon: "📝" },
    { type: "application/msword", ext: "DOC", icon: "📄" },
    { type: "text/plain", ext: "TXT", icon: "📄" }
  ]

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
    
    if (disabled) return
    
    const files = e.dataTransfer.files
    if (files && files[0]) {
      handleFile(files[0])
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (disabled) return
    const files = e.target.files
    if (files && files[0]) {
      handleFile(files[0])
    }
  }

  const handleFile = async (file: File) => {
    console.log("AdminFileUpload: handleFile called", {
      authLoading,
      isAuthenticated,
      user: user?.email,
      hasToken: !!localStorage.getItem('token')
    });
    
    // بررسی اینکه احراز هویت کامل شده یا نه
    if (authLoading || !isAuthenticated || !user) {
      console.log("❌ AdminFileUpload: Auth not ready, preventing upload");
      toast.error("لطفاً صبر کنید تا سیستم کاملاً بارگذاری شود")
      return
    }

    // Check file type
    const fileTypeInfo = supportedTypes.find(ft =>
      file.type === ft.type || file.name.toLowerCase().endsWith(`.${ft.ext.toLowerCase()}`)
    )

    if (!fileTypeInfo) {
      toast.error(`فایل پشتیبانی نشده! فقط فایل‌های PDF, Excel, CSV, Word, TXT مجاز هستند`)
      return
    }

    // Check file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      toast.error("حجم فایل نباید بیشتر از 10 مگابایت باشد")
      return
    }

    setIsUploading(true)

    try {
      // بررسی نهایی توکن قبل از ارسال درخواست
      const token = localStorage.getItem('token')
      if (!token) {
        console.log("❌ AdminFileUpload: No token found before upload");
        throw new Error('احراز هویت انجام نشده است')
      }
      
      console.log("✅ AdminFileUpload: All checks passed, starting upload...");
      
      // Create FormData for file upload
      const formData = new FormData()
      formData.append("file", file)

      // Upload to backend
      console.log("AdminFileUpload: Sending request to /admin/kb/articles/upload");
      const response = await api.post("/admin/kb/articles/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      })
      
      console.log("✅ AdminFileUpload: Upload successful", response.data);

      toast.success("فایل با موفقیت آپلود شد!")

      // Call success callback with response data
      if (onUploadSuccess) {
        onUploadSuccess(response.data)
      }

      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
    } catch (error: any) {
      console.error("❌ AdminFileUpload: Upload error:", error)
      
      // بررسی نوع خطا برای پیام مناسب
      if (error.response?.status === 401) {
        toast.error("خطای احراز هویت - لطفاً دوباره وارد شوید")
      } else if (error.response?.status === 403) {
        toast.error("دسترسی غیرمجاز - شما اجازه آپلود فایل را ندارید")
      } else if (error.message === 'احراز هویت انجام نشده است') {
        toast.error(error.message)
      } else {
        toast.error(error.response?.data?.detail || error.message || "خطا در آپلود فایل")
      }
    } finally {
      setIsUploading(false)
    }
  }

  const openFileDialog = () => {
    if (disabled) return
    
    // بررسی اینکه احراز هویت کامل شده یا نه
    if (authLoading || !isAuthenticated || !user) {
      console.log("❌ AdminFileUpload: Auth not ready, preventing file dialog");
      toast.error("لطفاً صبر کنید تا سیستم کاملاً بارگذاری شود")
      return
    }
    
    console.log("✅ AdminFileUpload: Opening file dialog");
    fileInputRef.current?.click()
  }

  return (
    <div className="w-full">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInput}
        accept=".pdf,.xlsx,.xls,.csv,.docx,.doc,.txt"
        className="hidden"
        disabled={disabled}
      />
      
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragActive
            ? "border-primary bg-primary/10"
            : disabled
            ? "border-input bg-secondary cursor-not-allowed"
            : "border-input hover:border-primary bg-secondary/50 cursor-pointer"
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={openFileDialog}
      >
        {isUploading ? (
          <div className="flex flex-col items-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-2"></div>
            <p className="text-sm text-muted-foreground">در حال آپلود فایل...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <div className="text-4xl mb-4">📁</div>
            <h3 className="text-lg font-semibold text-foreground mb-2">
              آپلود فایل
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              فایل خود را اینجا بکشید یا کلیک کنید تا فایل را انتخاب کنید
            </p>
            
            <div className="text-xs text-muted-foreground mb-4">
              <p>فرمت‌های مجاز: PDF, Excel (XLS/XLSX), CSV, Word (DOC/DOCX), TXT</p>
              <p>حداکثر حجم: 10 مگابایت</p>
            </div>
            
            <button
              type="button"
              disabled={disabled || authLoading || !isAuthenticated || !user}
              className={`px-4 py-2 rounded-md text-sm font-medium ${
                disabled || authLoading || !isAuthenticated || !user
                  ? "bg-secondary text-muted-foreground cursor-not-allowed"
                  : "btn-primary"
              }`}
              title={authLoading || !isAuthenticated || !user ? "لطفاً صبر کنید تا سیستم بارگذاری شود" : "انتخاب فایل"}
            >
              {authLoading ? "در حال بارگذاری..." : !isAuthenticated || !user ? "در حال ورود..." : "انتخاب فایل"}
            </button>
          </div>
        )}
      </div>
      
      {/* Close button */}
      {onClose && (
        <div className="mt-4 text-right">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-500 text-white rounded-md text-sm font-medium hover:bg-gray-600"
          >
            بستن
          </button>
        </div>
      )}
      
      {/* Supported file types */}
      <div className="mt-4">
        <p className="text-xs text-muted-foreground mb-2">فرمت‌های پشتیبانی شده:</p>
        <div className="flex flex-wrap gap-2">
          {supportedTypes.map((fileType) => (
            <span
              key={fileType.ext}
              className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-secondary text-secondary-foreground"
            >
              <span className="mr-1">{fileType.icon}</span>
              {fileType.ext}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

export default AdminFileUpload