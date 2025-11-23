import React from 'react'
import { User, Copy, Check, RotateCcw, AlertCircle, Sparkles } from 'lucide-react'
import { Button } from '../ui/button'
import { MarkdownRenderer } from '../ui/markdown-renderer'
import { Message } from '../../types/chat'
import blackCatImage from '../../assets/Black-Cat.png'
import { useAudio } from '../../hooks/useAudio'
import meowSound from '../../assets/meow.mp3'

interface MessageBubbleProps {
  message: Message
  isTyping?: boolean
  onRegenerate?: (messageId: string) => void
  onCopy?: (messageId: string, content: string) => void
  onSourceClick?: (sourceId: string, messageId: string) => void
  onGetMoreDetails?: (messageId: string) => void
  copiedMessageId?: string | null
  isLoading?: boolean
}

const MessageBubble: React.FC<MessageBubbleProps> = React.memo(({
  message,
  isTyping = false,
  onRegenerate,
  onCopy,
  onSourceClick,
  onGetMoreDetails,
  copiedMessageId,
  isLoading = false
}) => {
  const { play } = useAudio(meowSound)

  // متغیرهای state مربوط به نمایش بیشتر حذف شدند

  const handleAvatarClick = () => {
    if (!isUser) {
      play()
    }
  }

  const handleCopy = () => {
    if (onCopy) {
      onCopy(message.id, message.content)
    }
  }

  const handleRegenerate = () => {
    if (onRegenerate) {
      onRegenerate(message.id)
    }
  }

  const handleSourceClick = (sourceId: string) => {
    if (onSourceClick) {
      onSourceClick(sourceId, message.id)
    }
  }

  const handleGetMoreDetails = () => {
    if (onGetMoreDetails) {
      onGetMoreDetails(message.id)
    }
  }

  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat('fa-IR', {
      hour: '2-digit',
      minute: '2-digit'
    }).format(date)
  }

  const getRagTypeLabel = (type?: string) => {
    switch (type) {
      case 'simple':
        return 'ساده'
      case 'agentic':
        return 'عامل'
      default:
        return type || 'ساده'
    }
  }

  const isUser = message.role === 'user'
  const isFailed = message.is_failed

  // تغییر مهم: همیشه کل محتوا نمایش داده می‌شود و برشی (slice) وجود ندارد
  const displayContent = message.content

  return (
    <div className={`flex items-start space-x-2 space-x-reverse ${isUser ? 'justify-end' : 'justify-start'}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 ${isUser ? 'order-2' : 'order-1'}`}>
        {isUser ? (
          <div className="w-8 h-8 md:w-10 md:h-10 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 flex items-center justify-center text-white">
            <User className="w-4 h-4" />
          </div>
        ) : (
          <img
            src={blackCatImage}
            alt="سالی"
            className="w-8 h-8 md:w-10 md:h-10 rounded-full cursor-pointer object-cover hover:scale-105 transition-transform duration-200"
            onClick={handleAvatarClick}
          />
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 max-w-[80%] ${isUser ? 'order-1' : 'order-2'}`}>
        <div className={`rounded-lg p-3 ${isUser
          ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white'
          : isFailed
            ? 'bg-red-50 border border-red-200 text-red-800'
            : 'bg-white border border-gray-200 text-gray-900'
          }`}>
          {/* Message Header */}
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className={`text-xs font-medium ${isUser ? 'text-purple-100' : 'text-gray-600'
                }`}>
                {isUser ? 'شما' : 'دستیار هوشمند'}
              </span>
              {message.metadata?.rag_type && (
                <span className={`text-xs px-2 py-1 rounded-full ${isUser ? 'bg-purple-800 text-purple-100' : 'bg-gray-100 text-gray-600'
                  }`}>
                  {getRagTypeLabel(message.metadata.rag_type)}
                </span>
              )}
            </div>
            <span className={`text-xs ${isUser ? 'text-purple-100' : 'text-gray-500'
              }`}>
              {formatTime(message.timestamp)}
            </span>
          </div>

          {/* Message Body */}
          <div className="text-sm leading-relaxed">
            {/* Show thinking animation when isThinking flag is set or when typing with no content */}
            {(message.isThinking || (isTyping && !displayContent)) ? (
              <div className="flex items-center gap-2 text-gray-500 py-2">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
                <span className="text-sm">در حال فکر کردن...</span>
              </div>
            ) : isTyping && displayContent ? (
              <div className="flex items-center gap-2">
                <MarkdownRenderer content={displayContent} variant={isUser ? 'chat' : 'default'} />
                <div className="inline-block w-2 h-4 bg-current animate-pulse ml-0.5"></div>
              </div>
            ) : (
              <MarkdownRenderer content={displayContent} variant={isUser ? 'chat' : 'default'} />
            )}
          </div>

          {/* Error Message */}
          {isFailed && (
            <div className="mt-2 p-2 bg-red-100 border border-red-300 rounded-md">
              <div className="flex items-center gap-2 text-red-700">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm font-medium">خطا در پردازش</span>
              </div>
              <p className="text-xs text-red-600 mt-1">{message.failure_reason}</p>
            </div>
          )}

          {/* Sources */}
          {message.sources && message.sources.length > 0 && (
            <div className="mt-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-medium text-gray-600">منابع:</span>
                <span className="text-xs text-gray-500">({message.sources.length})</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {message.sources.map((source, index) => (
                  <button
                    key={source.id || index}
                    onClick={() => handleSourceClick(source.id || String(index))}
                    className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md transition-colors"
                  >
                    {source.title}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Confidence Score */}
          {message.confidence && (
            <div className="mt-2">
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-600">اطمینان:</span>
                <div className="flex-1 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-gradient-to-r from-green-500 to-green-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${Math.min(message.confidence * 100, 100)}%` }}
                  ></div>
                </div>
                <span className="text-xs text-gray-600 font-medium">
                  {Math.round(message.confidence * 100)}%
                </span>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-1 mt-3">
            {onCopy && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopy}
                disabled={copiedMessageId === message.id}
                className="text-xs p-1 h-6 w-6"
                title={copiedMessageId === message.id ? 'کپی شد' : 'کپی'}
              >
                {copiedMessageId === message.id ? (
                  <Check className="w-3 h-3 text-green-600" />
                ) : (
                  <Copy className="w-3 h-3" />
                )}
              </Button>
            )}

            {!isUser && onRegenerate && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRegenerate}
                disabled={isLoading}
                className="text-xs p-1 h-6 w-6"
                title="بازسازی پاسخ"
              >
                <RotateCcw className="w-3 h-3" />
              </Button>
            )}

            {!isUser && message.metadata?.can_get_more_details && onGetMoreDetails && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleGetMoreDetails}
                disabled={isLoading}
                className="text-xs p-1 h-6 w-6"
                title="توضیحات کامل"
              >
                <Sparkles className="w-3 h-3" />
              </Button>
            )}
          </div>
        </div>

        {/* دکمه نمایش بیشتر از اینجا حذف شد */}
        
      </div>
    </div>
  )
})

MessageBubble.displayName = 'MessageBubble'

export default MessageBubble