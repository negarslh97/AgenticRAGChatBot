import React, { useState, useEffect, useMemo } from 'react'
import { User, Copy, Check, RotateCcw, Sparkles, ChevronDown, ChevronUp, Brain } from 'lucide-react'
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

  // --- 1. پردازش متن و جدا کردن تفکر ---
  const { thinkContent, mainContent } = useMemo(() => {
    const content = message.content || '';
    
    // الگوی استاندارد برای پیدا کردن تگ think
    const thinkMatch = content.match(/<think>([\s\S]*?)(?:<\/think>|$)/i);

    if (thinkMatch) {
      const rawThink = thinkMatch[1].trim();
      const cleanedThink = rawThink
          .replace(/```[a-z]*\n?/gi, '') 
          .replace(/```/g, '')
          .trim();

      const main = content.replace(/<think>[\s\S]*?(?:<\/think>|$)/i, '').trim();
      return { thinkContent: cleanedThink, mainContent: main };
    }
    return { thinkContent: null, mainContent: content };
  }, [message.content]);

  // --- 2. مدیریت وضعیت ---
  const [isThinkingOpen, setIsThinkingOpen] = useState(false);
  const [userHasToggled, setUserHasToggled] = useState(false);

  // ریست وضعیت با تغییر پیام
  useEffect(() => {
    setIsThinkingOpen(false);
    setUserHasToggled(false);
  }, [message.id]);

  // منطق هوشمند باز/بسته شدن
  useEffect(() => {
    if (thinkContent && !userHasToggled) {
      if (isTyping && !mainContent) {
        setIsThinkingOpen(true);
      } else if (mainContent) {
        setIsThinkingOpen(false);
      }
    }
  }, [isTyping, mainContent, thinkContent, userHasToggled]);

  const toggleThinking = () => {
    setIsThinkingOpen(!isThinkingOpen);
    setUserHasToggled(true);
  };

  const handleAvatarClick = () => { if (!isUser) play() }
  const handleCopy = () => { if (onCopy) onCopy(message.id, message.content) }
  const handleRegenerate = () => { if (onRegenerate) onRegenerate(message.id) }
  const handleGetMoreDetails = () => { if (onGetMoreDetails) onGetMoreDetails(message.id) }

  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat('fa-IR', { hour: '2-digit', minute: '2-digit' }).format(date)
  }

  const isUser = message.role === 'user'
  const isFailed = message.is_failed

  // نمایش سه نقطه فقط وقتی هیچ دیتایی نیست
  const showLoadingDots = isTyping && !thinkContent && !mainContent;

  return (
    <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'} w-full p-1 mb-2`}>
      {/* آواتار */}
      <div className="flex-shrink-0 mt-1">
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

      {/* باکس پیام */}
      <div className={`flex flex-col min-w-0 max-w-[85%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`rounded-2xl shadow-sm w-full overflow-hidden transition-all duration-200 ${
          isUser
          ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white'
          : isFailed
              ? 'bg-red-50 border border-red-200 text-red-800'
              : 'bg-white border border-gray-200 text-gray-900'
        }`}>
          
          {/* هدر */}
          <div className={`flex items-center justify-between gap-4 px-4 pt-3 pb-2 ${isUser ? 'border-b border-white/20' : ''}`}>
            <span className={`text-xs font-bold ${isUser ? 'text-white' : 'text-gray-700'}`}>
              {isUser ? 'شما' : 'دستیار هوشمند'}
            </span>
            <span className={`text-[10px] ${isUser ? 'text-white/80' : 'text-gray-400'}`}>
              {formatTime(message.timestamp)}
            </span>
          </div>

          {/* محتوا */}
          <div className="w-full px-4 pb-4">
            
            {/* 1. لودینگ */}
            {showLoadingDots && (
               <div className="flex items-center gap-1 h-8 py-2 px-2">
                 <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                 <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                 <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
               </div>
            )}

            {/* 2. بخش تفکر (آبی آسمانی) */}
            {thinkContent && (
              <div className="mt-1 mb-4 rounded-lg border border-sky-200 bg-sky-50 overflow-hidden w-full min-w-0">
                <button
                  onClick={toggleThinking}
                  className="w-full flex items-center justify-between px-3 py-2 bg-sky-100 hover:bg-sky-200 transition-colors cursor-pointer select-none border-b border-sky-200/50 min-w-0"
                  title={isThinkingOpen ? "بستن جزئیات تفکر" : "مشاهده جزئیات تفکر"}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <Brain className="w-4 h-4 text-sky-700 flex-shrink-0" />
                    <span className="text-xs font-bold text-sky-800 whitespace-nowrap">فرآیند تفکر</span>
                    {isTyping && !mainContent && (
                      <span className="flex h-2 w-2 relative mr-1 flex-shrink-0">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-500"></span>
                      </span>
                    )}
                  </div>
                  {isThinkingOpen ? (
                    <ChevronUp className="w-4 h-4 text-sky-600 flex-shrink-0" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-sky-600 flex-shrink-0" />
                  )}
                </button>

                <div
                  className={`transition-all duration-500 ease-in-out overflow-hidden bg-sky-50 ${
                    isThinkingOpen ? 'max-h-[5000px] opacity-100' : 'max-h-0 opacity-0'
                  }`}
                >
                  <div className="p-3 text-xs text-sky-900 leading-7 font-sans border-t border-sky-100 w-full overflow-hidden min-w-0">
                    <div className="whitespace-normal break-words thinking-content" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                      {thinkContent}
                    </div>
                  </div>
                </div>
                
                {!isThinkingOpen && (
                  <div
                    onClick={toggleThinking}
                    className="px-3 py-1.5 text-[10px] text-sky-500 truncate cursor-pointer hover:text-sky-700 hover:bg-sky-100 transition-colors select-none w-full min-w-0"
                  >
                    {thinkContent.slice(0, 60)}...
                  </div>
                )}
              </div>
            )}

            {/* 3. متن پاسخ اصلی */}
            {mainContent && (
              <div className={`prose prose-sm max-w-full break-words whitespace-normal leading-7 ${isUser ? 'prose-invert text-white [&_*]:text-white' : ''}`} style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                <MarkdownRenderer content={mainContent} variant={isUser ? 'chat' : 'default'} />
                {isTyping && <span className="inline-block w-1.5 h-4 bg-purple-600 animate-pulse align-middle mr-1" />}
              </div>
            )}

            {/* فوتر */}
            <div className={`flex items-center justify-end gap-1 mt-3 pt-2 ${isUser ? 'border-white/10' : 'border-t border-gray-50'} ${isUser ? 'text-white/70' : 'text-gray-400'}`}>
               {onCopy && (
                <Button variant="ghost" size="sm" onClick={handleCopy} disabled={copiedMessageId === message.id} className={`h-7 w-7 p-0 rounded-full ${isUser ? 'hover:bg-white/20 text-white' : 'hover:bg-gray-100'}`}>
                  {copiedMessageId === message.id ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                </Button>
              )}
              {!isUser && onRegenerate && (
                <Button variant="ghost" size="sm" onClick={handleRegenerate} disabled={isLoading} className="h-7 w-7 p-0 rounded-full hover:bg-gray-100">
                  <RotateCcw className="w-3.5 h-3.5" />
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