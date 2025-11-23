import React, { useState, useEffect, useMemo } from 'react'
import { User, Copy, Check, RotateCcw, AlertCircle, Sparkles, Brain, ChevronDown, ChevronUp } from 'lucide-react'
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

const MessageBubble: React.FC<MessageBubbleProps> = ({
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

  const { thinkContent, mainContent } = useMemo(() => {
    const content = message.content || '';
    const thinkMatch = content.match(/<think>([\s\S]*?)(?:<\/think>|$)/i);

    if (thinkMatch) {
      const rawThink = thinkMatch[1].trim();
      const cleanedThink = rawThink
          .replace(/```[a-z]*\n?/gi, '')
          .replace(/```/g, '')
          .trim();

      return {
        thinkContent: cleanedThink,
        mainContent: content.replace(/<think>[\s\S]*?(?:<\/think>|$)/i, '').trim()
      };
    }
    return { thinkContent: null, mainContent: content };
  }, [message.content]);

  const [isThinkingOpen, setIsThinkingOpen] = useState(false);
  const [hasUserClosedThinking, setHasUserClosedThinking] = useState(false);

  useEffect(() => {
    setIsThinkingOpen(false);
    setHasUserClosedThinking(false);
  }, [message.id]);

  useEffect(() => {
    if (isTyping && thinkContent && thinkContent.length > 0) {
      setIsThinkingOpen(true);
      setHasUserClosedThinking(false);
    }
    else if (!isTyping && thinkContent && thinkContent.length > 0 && !hasUserClosedThinking) {
      setIsThinkingOpen(true);
    }
  }, [isTyping, thinkContent, hasUserClosedThinking, message.id]);

  const toggleThinking = () => {
    setIsThinkingOpen(!isThinkingOpen);
    if (isThinkingOpen) {
      setHasUserClosedThinking(true);
    } else {
      setHasUserClosedThinking(false);
    }
  };

  const handleAvatarClick = () => {
    if (!isUser) play()
  }

  const handleCopy = () => {
    if (onCopy) onCopy(message.id, message.content)
  }

  const handleRegenerate = () => {
    if (onRegenerate) onRegenerate(message.id)
  }

  const handleSourceClick = (sourceId: string) => {
    if (onSourceClick) onSourceClick(sourceId, message.id)
  }

  const handleGetMoreDetails = () => {
    if (onGetMoreDetails) onGetMoreDetails(message.id)
  }

  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat('fa-IR', {
      hour: '2-digit',
      minute: '2-digit'
    }).format(date)
  }

  const getRagTypeLabel = (type?: string) => {
    switch (type) {
      case 'simple': return 'ساده'
      case 'agentic': return 'عامل'
      default: return type || 'ساده'
    }
  }

  const isUser = message.role === 'user'
  const isFailed = message.is_failed

  return (
    <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'} w-full max-w-full overflow-hidden p-1`}>
      <div className="flex-shrink-0">
        {isUser ? (
          <div className="w-8 h-8 md:w-10 md:h-10 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 flex items-center justify-center text-white shadow-sm">
            <User className="w-4 h-4" />
          </div>
        ) : (
          <img
            src={blackCatImage}
            alt="AI"
            className="w-8 h-8 md:w-10 md:h-10 rounded-full cursor-pointer object-cover hover:scale-105 transition-transform duration-200 shadow-sm border border-gray-100"
            onClick={handleAvatarClick}
          />
        )}
      </div>

      <div className={`flex flex-col min-w-0 max-w-[85%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`rounded-2xl shadow-sm w-full ${
          isUser
          ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white'
          : isFailed
              ? 'bg-red-50 border border-red-200 text-red-800'
              : 'bg-white border border-gray-100 text-gray-900'
        }`} style={isUser ? { color: '#ffffff' } : {}}>
          <div className={`flex items-center justify-between gap-4 mb-3 pb-2 border-b px-4 pt-4 ${isUser ? 'border-white/20' : 'border-gray-100'}`}>
            <div className="flex items-center gap-2">
              <span className={`text-xs font-bold ${isUser ? 'text-white' : 'text-gray-700'}`}>
                {isUser ? 'شما' : 'دستیار هوشمند'}
              </span>
              {message.metadata?.rag_type && (
                <span className={`text-[10px] px-2 py-0.5 rounded-full border ${isUser ? 'bg-white/20 border-white/30 text-white' : 'bg-gray-100 border-gray-200 text-gray-600'}`}>
                  {getRagTypeLabel(message.metadata.rag_type)}
                </span>
              )}
            </div>
            <span className={`text-[10px] ${isUser ? 'text-white/80' : 'text-gray-400'}`}>
              {formatTime(message.timestamp)}
            </span>
          </div>

          <div className={`text-sm leading-7 w-full grid grid-cols-1 overflow-hidden px-4 ${isUser ? '[&_*]:text-white' : ''}`} style={{ overflowWrap: 'anywhere', wordBreak: 'break-word' }}>
            {thinkContent && (
              <div className="mb-4 rounded-xl border w-full overflow-hidden" style={{ backgroundColor: '#eff6ff', borderColor: '#bfdbfe' }}>
                <button onClick={toggleThinking} className="w-full flex items-center gap-2 px-3 py-2.5 transition-colors cursor-pointer" style={{ backgroundColor: '#eff6ff' }}>
                  <Brain className="w-4 h-4 text-blue-600 flex-shrink-0" />
                  <span className="text-xs font-bold text-blue-800 truncate">
                    {isTyping ? 'در حال تحلیل و فکر کردن...' : 'فرآیند تفکر مدل'}
                  </span>
                  <div className="mr-auto flex items-center gap-1 flex-shrink-0">
                    {isThinkingOpen ? <ChevronUp className="w-4 h-4 text-blue-600" /> : <ChevronDown className="w-4 h-4 text-blue-600" />}
                  </div>
                </button>
                {isThinkingOpen && (
                  <div className="p-3 border-t text-xs leading-relaxed w-full markdown-thinking" style={{
                    borderColor: '#bfdbfe',
                    backgroundColor: '#f0f6ff',
                    color: '#334155',
                    height: 'auto',
                    overflowX: 'hidden',
                    overflowY: 'auto',
                    maxHeight: '300px',
                    overflowWrap: 'anywhere',
                    wordBreak: 'break-word'
                  }}>
                    <div className="whitespace-pre-wrap font-mono text-xs">
                      <MarkdownRenderer content={thinkContent} variant="default" />
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="w-full max-w-full overflow-x-auto pb-4">
              {mainContent ? (
                <div className={`prose prose-sm max-w-none break-words ${isUser ? 'prose-invert text-white [&_*]:text-white' : ''}`}>
                  <MarkdownRenderer content={mainContent} variant={isUser ? 'chat' : 'default'} />
                </div>
              ) : (
                (isTyping && !thinkContent) && (
                  <div className="flex items-center gap-2 text-gray-400 py-1 animate-pulse">
                    <span className="text-xs">در حال نوشتن پاسخ...</span>
                  </div>
                )
              )}
              {isTyping && mainContent && <span className="inline-block w-1.5 h-4 bg-current animate-pulse align-middle mr-1" />}
            </div>

            <div className={`flex items-center justify-end gap-1 mt-2 px-4 pb-4 ${isUser ? 'text-white/70' : 'text-gray-400'}`}>
              {onCopy && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCopy}
                  disabled={copiedMessageId === message.id}
                  className={`h-7 w-7 p-0 rounded-full hover:bg-black/5 ${isUser ? 'hover:bg-white/20 text-white' : ''}`}
                >
                  {copiedMessageId === message.id ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                </Button>
              )}
              {!isUser && onRegenerate && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleRegenerate}
                  disabled={isLoading}
                  className="h-7 w-7 p-0 rounded-full hover:bg-black/5"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </Button>
              )}
              {!isUser && message.metadata?.can_get_more_details && onGetMoreDetails && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleGetMoreDetails}
                  disabled={isLoading}
                  className="h-7 w-7 p-0 rounded-full hover:bg-black/5 text-purple-500"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

MessageBubble.displayName = 'MessageBubble'

export default MessageBubble