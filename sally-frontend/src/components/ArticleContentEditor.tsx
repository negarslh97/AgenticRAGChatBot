"use client"

import React, { useState, useEffect } from "react"
import ReactMarkdown from 'react-markdown'
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs"
import { Eye, Edit3 } from "lucide-react"

interface ArticleContentEditorProps {
  markdownContent: string
  htmlContent?: string
  onMarkdownChange: (content: string) => void
  placeholder?: string
  disabled?: boolean
}

const ArticleContentEditor: React.FC<ArticleContentEditorProps> = ({
  markdownContent,
  htmlContent,
  onMarkdownChange,
  placeholder = "محتوای مقاله را وارد کنید...",
  disabled = false
}) => {
  const [content, setContent] = useState(markdownContent)
  const [activeTab, setActiveTab] = useState("edit")

  // Auto-switch to preview tab if HTML content exists and we're currently on edit tab
  useEffect(() => {
    if (htmlContent && htmlContent.trim() && activeTab === "edit") {
      setActiveTab("preview")
    }
  }, [htmlContent, activeTab])

  // Update content when markdownContent prop changes
  useEffect(() => {
    setContent(markdownContent)
  }, [markdownContent])

  const handleContentChange = (value: string) => {
    setContent(value)
    onMarkdownChange(value)
  }

  // Preview uses htmlContent if available, otherwise falls back to markdown rendering

  return (
    <div className="w-full" dir="rtl">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        {/* <TabsList className="grid w-full grid-cols-2 mb-4">
          <TabsTrigger value="preview" className="flex items-center gap-2">
            <Eye className="h-4 w-4" />
            پیش‌نمایش
          </TabsTrigger>
          <TabsTrigger value="edit" className="flex items-center gap-2">
            <Edit3 className="h-4 w-4" />
            ویرایش
          </TabsTrigger>
        </TabsList> */}

        <TabsContent value="preview" className="mt-0">
          <div className="min-h-[400px] border border-gray-200 rounded-lg p-6 bg-white" dir="rtl">
            {content && content.trim() ? (
              <div className="prose prose-lg max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-a:text-blue-600 prose-strong:text-gray-900 prose-code:text-gray-800 prose-pre:bg-gray-100 text-right" style={{ direction: 'rtl', textAlign: 'right' }}>
                {htmlContent ? (
                  <div dangerouslySetInnerHTML={{ __html: htmlContent }} />
                ) : (
                  <ReactMarkdown>{content}</ReactMarkdown>
                )}
              </div>
            ) : (
              <div className="text-gray-500 text-center py-12">
                <Eye className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>محتوایی برای پیش‌نمایش وجود ندارد</p>
                <p className="text-sm mt-2">از تب "ویرایش" برای اضافه کردن محتوا استفاده کنید</p>
                {content && content.trim() && (
                  <p className="text-sm mt-2 text-blue-600">
                    💡 محتوای Markdown آماده است! به تب "ویرایش" بروید تا آن را ببینید
                  </p>
                )}
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="edit" className="mt-0">
          <div className="min-h-[400px]">
            <textarea
              value={content}
              onChange={(e) => handleContentChange(e.target.value)}
              placeholder={placeholder}
              disabled={disabled}
              rows={20}
              className="w-full min-h-[400px] p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-vertical font-mono text-sm text-right"
              dir="rtl"
              style={{ textAlign: 'right', direction: 'rtl' }}
            />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default ArticleContentEditor
