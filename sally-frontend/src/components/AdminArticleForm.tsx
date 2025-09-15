"use client"

import { useState } from "react"
import { useAuth } from "../context/AuthContext"
import { toast } from "react-hot-toast"

interface AdminArticleFormProps {
  onArticleCreated?: () => void
}

const AdminArticleForm: React.FC<AdminArticleFormProps> = ({ onArticleCreated }) => {
  const { user } = useAuth()
  const [formData, setFormData] = useState({
    title: "",
    content: "",
    summary: "",
    tags: ""
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!user || (user.role !== "SuperAdmin" && user.role !== "Admin")) {
      toast.error("فقط ادمین‌ها می‌توانند مقاله ایجاد کنند")
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/knowledge-base/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("token")}`
        },
        body: JSON.stringify({
          ...formData,
          tags: formData.tags.split(",").map(tag => tag.trim()).filter(Boolean)
        })
      })

      if (!response.ok) {
        throw new Error("خطا در ایجاد مقاله")
      }

      const article = await response.json()
      toast.success("مقاله با موفقیت ایجاد شد!")
      
      // Reset form
      setFormData({
        title: "",
        content: "",
        summary: "",
        tags: ""
      })

      onArticleCreated?.()
    } catch (error: any) {
      toast.error(error.message || "خطا در ایجاد مقاله")
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }))
  }

  if (!user || (user.role !== "SuperAdmin" && user.role !== "Admin")) {
    return (
      <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
        <p className="text-destructive text-center">فقط ادمین‌ها می‌توانند به این بخش دسترسی داشته باشند</p>
      </div>
    )
  }

  return (
    <div className="card p-6">
      <h2 className="text-xl font-bold mb-4 text-foreground">ایجاد مقاله جدید</h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            عنوان مقاله *
          </label>
          <input
            type="text"
            name="title"
            value={formData.title}
            onChange={handleChange}
            required
            className="input-field"
            placeholder="عنوان مقاله را وارد کنید"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            خلاصه مقاله
          </label>
          <textarea
            name="summary"
            value={formData.summary}
            onChange={handleChange}
            rows={3}
            className="input-field"
            placeholder="خلاصه مقاله را وارد کنید"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            محتوای مقاله *
          </label>
          <textarea
            name="content"
            value={formData.content}
            onChange={handleChange}
            rows={10}
            required
            className="input-field"
            placeholder="محتوای markdown مقاله را وارد کنید"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            برچسب‌ها (با کاما جدا شوند)
          </label>
          <input
            type="text"
            name="tags"
            value={formData.tags}
            onChange={handleChange}
            className="input-field"
            placeholder="برچسب1, برچسب2, برچسب3"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full"
        >
          {loading ? "در حال ایجاد..." : "ایجاد مقاله"}
        </button>
      </form>
    </div>
  )
}

export default AdminArticleForm