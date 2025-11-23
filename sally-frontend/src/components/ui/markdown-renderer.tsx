import React from 'react'
import ReactMarkdown from 'react-markdown'
import { cn } from '../../lib/utils'

interface MarkdownRendererProps {
  content: string
  className?: string
  variant?: 'default' | 'compact' | 'chat'
}

/**
 * یک کامپوننت مشترک برای نمایش محتوای Markdown
 * با پشتیبانی از RTL و استایل‌های مختلف
 */
export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  className,
  variant = 'default'
}) => {
  // استایل‌های پایه برای prose
  const baseStyles = "prose max-w-none text-right"

  // استایل‌های مختلف بر اساس variant
  const variantStyles = {
    default: "prose-lg prose-headings:text-gray-900 prose-p:text-gray-700 prose-a:text-blue-600 prose-strong:font-bold prose-strong:text-gray-900 prose-em:italic prose-code:text-sm prose-code:bg-gray-100 prose-code:text-gray-800 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-gray-100 prose-pre:text-gray-800 prose-ul:list-disc prose-ol:list-decimal prose-li:text-gray-700 prose-blockquote:border-r-4 prose-blockquote:border-blue-500 prose-blockquote:pr-4 prose-blockquote:italic prose-blockquote:text-gray-600 prose-table:border-collapse prose-th:border prose-th:border-gray-300 prose-th:bg-gray-100 prose-th:p-2 prose-td:border prose-td:border-gray-300 prose-td:p-2 prose-td:text-gray-700",
    compact: "prose-sm prose-headings:text-gray-900 prose-p:text-gray-800 prose-a:text-blue-600 prose-strong:text-gray-900 prose-code:text-xs prose-code:bg-gray-100 prose-code:text-gray-800 prose-code:px-1 prose-code:rounded prose-li:text-gray-800 prose-blockquote:text-gray-700",
    chat: "prose-sm prose-headings:text-inherit prose-p:text-inherit prose-a:text-blue-300 prose-a:underline prose-strong:font-bold prose-strong:text-inherit prose-em:italic prose-code:bg-white/10 prose-code:text-inherit prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-white/10 prose-pre:text-inherit prose-ul:list-disc prose-ol:list-decimal prose-li:text-inherit"
  }

  return (
    <div
      className={cn(baseStyles, variantStyles[variant], className)}
      dir="rtl"
      style={{ direction: 'rtl', textAlign: 'right' }}
    >
      <ReactMarkdown
        components={{
          // Custom components for better RTL support with proper spacing
          p: ({ children }) => (
            <p className="mb-3 leading-7 text-right" style={{ wordSpacing: '0.05em' }}>{children}</p>
          ),
          h1: ({ children }) => (
            <h1 className="text-2xl font-bold mb-3 mt-5 text-right">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-xl font-bold mb-3 mt-4 text-right">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-lg font-bold mb-2 mt-3 text-right">{children}</h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-base font-bold mb-2 mt-3 text-right">{children}</h4>
          ),
          ul: ({ children }) => (
            <ul className="list-disc list-inside mb-4 mr-4 text-right">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside mb-4 mr-4 text-right">{children}</ol>
          ),
          li: ({ children }) => (
            <li className="mb-1 text-right">{children}</li>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-r-4 border-blue-500 pr-4 py-2 my-4 italic text-gray-600 bg-blue-50 rounded">
              {children}
            </blockquote>
          ),
          code: ({ inline, children, ...props }: any) => {
            return inline ? (
              <code className="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
                {children}
              </code>
            ) : (
              <code className="block bg-gray-100 text-gray-800 p-4 rounded text-sm font-mono overflow-x-auto" {...props}>
                {children}
              </code>
            )
          },
          a: ({ href, children }) => (
            <a
              href={href}
              className="text-blue-600 hover:text-blue-800 underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              {children}
            </a>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto my-4">
              <table className="min-w-full border-collapse border border-gray-300">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-gray-300 bg-gray-100 px-4 py-2 text-right font-bold">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-gray-300 px-4 py-2 text-right">
              {children}
            </td>
          ),
          hr: () => (
            <hr className="my-6 border-t-2 border-gray-200" />
          ),
          strong: ({ children }) => (
            <strong className="font-bold text-gray-900">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic">{children}</em>
          )
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

export default MarkdownRenderer
