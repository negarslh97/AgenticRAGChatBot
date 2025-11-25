import React, { useState, useEffect, useMemo, useRef } from 'react'
import { User, Copy, Check, RotateCcw, ChevronDown, ChevronUp, Brain, CheckCircle } from 'lucide-react'
import { Button } from '../ui/button'
import { MarkdownRenderer } from '../ui/markdown-renderer'
import { Message } from '../../types/chat'
import blackCatImage from '../../assets/Black-Cat.png'
import { useAudio } from '../../hooks/useAudio'
import meowSound from '../../assets/meow.mp3'

interface MessageBubbleProps {
  message: Message
  isTyping?: boolean
  isLastMessage?: boolean
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
  isLastMessage = false,
  onRegenerate,
  onCopy,
  onSourceClick,
  onGetMoreDetails,
  copiedMessageId,
  isLoading = false
}) => {
  const { play } = useAudio(meowSound)

  // Refs for tracking processed messages to reduce console logging
  const processedMessagesRef = useRef<Set<string>>(new Set())
  const thinkingStateLoggedRef = useRef<Set<string>>(new Set())

  // Environment-based logging
  const isDevelopment = process.env.NODE_ENV === 'development'

  // --- 1. پردازش متن و جدا کردن تفکر ---
  const { thinkContent, mainContent } = useMemo(() => {
    const content = message.content || '';

    // دیباگ: چک کردن محتوای پیام (فقط یک بار برای هر پیام)
    const contentKey = `content_${message.id}_${content.length}`;
    if (isDevelopment && !processedMessagesRef.current.has(contentKey)) {
      console.log('🧠 Processing message:', message.id, '| has <think>:', content.includes('<think>'), '| has ```thinking:', content.includes('```thinking'));
      processedMessagesRef.current.add(contentKey);
    }

    // الگوی استاندارد برای پیدا کردن تگ think یا کد بلاک thinking
    let thinkMatch = content.match(/<think>([\s\S]*?)(?:<\/think>|$)/i);

    // اگر تگ think پیدا نشد، کد بلاک thinking رو چک کن
    if (!thinkMatch) {
      thinkMatch = content.match(/```thinking\s*([\s\S]*?)```/i);
    }

    if (thinkMatch) {
      const rawThink = thinkMatch[1].trim();
      const cleanedThink = rawThink
          .replace(/```[a-z]*\n?/gi, '')
          .replace(/```/g, '')
          .trim();

      // حذف بخش تفکر از محتوای اصلی و حذف فاصله‌های خالی ابتدای متن
      const main = content
        .replace(/<think>[\s\S]*?(?:<\/think>|$)/i, '')
        .replace(/```thinking[\s\S]*?```/i, '')
        .trimEnd(); // تغییر: استفاده از trimEnd() برای اطمینان از نچسبیدن اینتر اضافه به ته متن

      const extractedKey = `extracted_${message.id}_${cleanedThink.length}`;
      if (isDevelopment && !processedMessagesRef.current.has(extractedKey)) {
        console.log('🧠 Extracted thinking content for message:', message.id, '| length:', cleanedThink.length);
        processedMessagesRef.current.add(extractedKey);
      }

      return { thinkContent: cleanedThink, mainContent: main };
    }

    return { thinkContent: null, mainContent: content.trim() }; // تغییر: trim() کامل برای حالتی که تفکر وجود ندارد
  }, [message.content, message.id, isDevelopment]);

  // --- 2. مدیریت وضعیت ---
  const [isThinkingOpen, setIsThinkingOpen] = useState(false);
  const [userHasToggled, setUserHasToggled] = useState(false);

  // ریست وضعیت با تغییر پیام
  useEffect(() => {
    const resetKey = `reset_${message.id}`;
    if (isDevelopment && !processedMessagesRef.current.has(resetKey)) {
      console.log('🧠 Reset thinking state for new message:', message.id);
      processedMessagesRef.current.add(resetKey);
    }
    setIsThinkingOpen(false);
    setUserHasToggled(false);
  }, [message.id, isDevelopment]);

  // منطق هوشمند باز/بسته شدن - وقتی مدل تفکر تمام کرد، thinking بسته شود
  useEffect(() => {
    if (thinkContent && !userHasToggled) {
      // اگر هنوز در حال تایپ هستیم و محتوای اصلی وجود ندارد: تفکر را باز نشان بده
      if (isTyping && !mainContent) {
        const openingKey = `opening_${message.id}`;
        if (isDevelopment && !thinkingStateLoggedRef.current.has(openingKey)) {
          console.log('🧠 Opening thinking (typing, no main content) for message:', message.id);
          thinkingStateLoggedRef.current.add(openingKey);
        }
        setIsThinkingOpen(true);
      }
      // اگر محتوای اصلی وجود دارد (یعنی مدل تفکر را تمام کرده): تفکر را ببند
      else if (mainContent) {
        const closingKey = `closing_${message.id}`;
        if (isDevelopment && !thinkingStateLoggedRef.current.has(closingKey)) {
          console.log('🧠 Closing thinking (main content exists) for message:', message.id);
          thinkingStateLoggedRef.current.add(closingKey);
        }
        setIsThinkingOpen(false);
      }
      // اگر تایپ تمام شده اما محتوای اصلی وجود ندارد: تفکر را بسته نگه دار
      else if (!isTyping && !mainContent) {
        setIsThinkingOpen(false);
      }
    }
  }, [isTyping, mainContent, thinkContent, userHasToggled, message.id, isDevelopment]);

  const toggleThinking = () => {
    if (isDevelopment) {
      console.log('🧠 User toggled thinking for message:', message.id, '->', !isThinkingOpen);
    }
    setIsThinkingOpen(!isThinkingOpen);
    setUserHasToggled(true);
  };

  const handleAvatarClick = () => { if (!isUser) play() }
  const handleCopy = () => { if (onCopy) onCopy(message.id, message.content) }
  const handleRegenerate = () => { if (onRegenerate) onRegenerate(message.id) }

  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat('fa-IR', { hour: '2-digit', minute: '2-digit' }).format(date)
  }

  const isUser = message.role === 'user'
  const isFailed = message.is_failed

  // تغییر: اضافه کردن .trim() برای اینکه فاصله‌های خالی باعث حذف زودهنگام سه نقطه نشوند
  const showLoadingDots = isTyping && !thinkContent && (!mainContent || mainContent.trim().length === 0);
  

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
            <div className="flex items-center gap-2">
              <span className={`text-xs font-bold ${isUser ? 'text-white' : 'text-gray-700'}`}>
                {isUser ? 'شما' : 'دستیار هوشمند'}
              </span>
              {isLastMessage && (
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                  <span className={`text-[10px] ${isUser ? 'text-blue-200' : 'text-blue-600'} font-medium`}>
                    آخرین پیام
                  </span>
                </div>
              )}
            </div>
            <span className={`text-[10px] ${isUser ? 'text-white/80' : 'text-gray-400'}`}>
              {formatTime(message.timestamp)}
            </span>
          </div>

          {/* محتوا */}
          <div className="w-full px-4 pb-4">
            
            {/* 1. لودینگ */}
            {/* {showLoadingDots && (
               <div className="flex items-center gap-1 h-8 py-2 px-2">
                 <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                 <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                 <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
               </div>
            )} */}

            {/* 2. بخش تفکر (آبی آسمانی) */}
            {thinkContent && (
              <div className="mt-2 mb-4 border border-sky-200 rounded-lg bg-sky-50 overflow-hidden transition-all duration-300">
                {/* هدر باز/بستن */}
                <div
                  onClick={toggleThinking}
                  className="flex items-center justify-between gap-2 px-3 py-2 cursor-pointer bg-sky-100 hover:bg-sky-200 transition-colors select-none"
                >
                  <div className="flex items-center gap-2">
                    <Brain className="w-4 h-4 text-sky-700" />
                    <span className="text-xs font-semibold text-sky-800">فرآیند تفکر</span>
                    {isTyping && !mainContent && (
                      <span className="flex h-2 w-2 relative mr-1">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-500"></span>
                      </span>
                    )}
                    {!isTyping && mainContent && <CheckCircle className="w-4 h-4 text-green-500" />}
                  </div>
                  {isThinkingOpen ? (
                    <ChevronUp className="w-4 h-4 text-sky-700" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-sky-700" />
                  )}
                </div>

                {/* محتوای جمع‌شونده */}
                <div
                  className={`transition-all duration-500 ease-in-out ${
                    isThinkingOpen ? 'max-h-[600px] opacity-100' : 'max-h-0 opacity-0'
                  } overflow-hidden`}
                >
                  <div className="p-3 text-xs text-sky-900 leading-6 border-t border-sky-200">
                    <div className="whitespace-pre-wrap break-words">{thinkContent}</div>
                  </div>
                </div>
              </div>
            )}

            {/* 3. متن پاسخ اصلی */}
            {/* {mainContent && (
              <div className={`prose prose-sm max-w-full break-words whitespace-normal leading-7 ${isUser ? 'prose-invert text-white [&_*]:text-white' : ''}`} style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                <MarkdownRenderer content={mainContent} variant={isUser ? 'chat' : 'default'} />
                {isTyping && <span className="inline-block w-1.5 h-4 bg-purple-600 animate-pulse align-middle mr-1" />}
              </div>
            )} */}

            {/* 3. متن پاسخ اصلی */}
            {/* تغییر: اگر تفکر داریم، پایینش رو نشون نده مگر اینکه متن واقعی اومده باشه */}
            {((mainContent && mainContent.trim().length > 0) || (showLoadingDots && !thinkContent)) && (
              <div
                className={`prose prose-sm max-w-full break-words whitespace-normal leading-7 min-h-[1.75rem]
                  ${isUser ? 'prose-invert text-white [&_*]:text-white' : 'text-gray-900'}
                  
                  [&_*:first-child]:mt-0 
                  [&_p:first-of-type]:mt-0
                  [&_p]:mb-0
                  [&_p:empty]:hidden

                  ${isTyping ? `
                    [&>*:last-child]:after:content-['▋'] 
                    [&>*:last-child]:after:ml-1 
                    [&>*:last-child]:after:animate-pulse 
                    [&>*:last-child]:after:text-purple-600 
                    [&>*:last-child]:after:align-middle
                    [&>*:last-child]:after:inline-block` : ''}
                `}
                dir="rtl"
              >
                {showLoadingDots ? (
                  <div className="flex items-center gap-1 h-7">
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
                  </div>
                ) : (
                  <MarkdownRenderer
                    content={mainContent}
                    variant={isUser ? 'chat' : 'default'}
                  />
                )}
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