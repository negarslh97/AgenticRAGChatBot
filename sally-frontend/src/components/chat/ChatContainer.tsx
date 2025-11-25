import React, { useEffect, useCallback, useMemo, memo, useRef } from 'react'
import { Button } from '../ui/button'
import { Textarea } from '../ui/textarea'
import { VoiceInput } from '../ui/voice-input'
import { Send, Settings } from 'lucide-react'
import MessageBubble from './MessageBubble'
import { WelcomeMessage } from './WelcomeMessage'
import { Conversation as BaseConversation } from '../../types/chat'

// Environment-based logging
const isDevelopment = process.env.NODE_ENV === 'development'

interface ExtendedConversation extends BaseConversation {
  rag_type?: 'simple' | 'agentic'
  model_name?: string
  temperature?: number
  type?: string
}

interface ChatContainerProps {
  selectedConversation: ExtendedConversation | null
  newMessage: string
  setNewMessage: (message: string | ((prev: string) => string)) => void
  isLoading: boolean
  isThinking: boolean
  ragType: 'simple' | 'agentic'
  selectedModel: string
  temperature: number
  availableModels: any[]
  handleSendMessage: () => void
  handleKeyPress: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void
  messagesContainerRef: React.RefObject<HTMLDivElement>
  messagesEndRef: React.RefObject<HTMLDivElement>
  handleScroll: () => void
  handleGoToBottom: () => void
  showGoToBottomBtn: boolean
  showSettingsModal: boolean
  setShowSettingsModal: (show: boolean) => void
  textareaRef: React.RefObject<HTMLTextAreaElement>
  formatTime: (date: Date) => string
  getRagTypeIcon: (type: 'simple' | 'agentic') => string
  getRagTypeLabel: (type: 'simple' | 'agentic') => string
  SkeletonLoader: () => JSX.Element
  TypewriterCursor: () => JSX.Element
  copiedMessageId: string | null
  copyMessage: (messageId: string, content: string) => void
  retryMessage: (messageId: string) => void
  regenerateMessage: (messageId: string) => void
  handleSourceClick: (sourceId: string, messageId: string) => void
  FEATURE_FLAGS: {
    SHOW_SETTINGS: boolean
    SHOW_VOICE_INPUT: boolean
  }
}

const ChatContainer = memo<ChatContainerProps>(({
  selectedConversation,
  newMessage,
  setNewMessage,
  isLoading,
  isThinking,
  ragType,
  selectedModel,
  temperature,
  availableModels,
  handleSendMessage,
  handleKeyPress,
  messagesContainerRef,
  messagesEndRef,
  handleScroll,
  handleGoToBottom,
  showGoToBottomBtn,
  showSettingsModal,
  setShowSettingsModal,
  textareaRef,
  formatTime,
  getRagTypeIcon,
  getRagTypeLabel,
  SkeletonLoader,
  TypewriterCursor,
  copiedMessageId,
  copyMessage,
  retryMessage,
  regenerateMessage,
  handleSourceClick,
  FEATURE_FLAGS
}) => {

  // --- تغییر جدید: Smart Auto-Scroll Logic ---
  // این رفرنس نگه می‌دارد که آیا کاربر قبل از آپدیت پیام در پایین صفحه بوده یا خیر
  const isAtBottomRef = useRef(true);

  // تابع چک کردن موقعیت اسکرول
  const checkScrollPosition = useCallback(() => {
    if (messagesContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = messagesContainerRef.current;
      // اگر فاصله از پایین کمتر از 50 پیکسل باشد، یعنی کاربر پایین است
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
      isAtBottomRef.current = isAtBottom;
      
      // فراخوانی هندلر اسکرول اصلی برای دکمه GoToBottom
      handleScroll();
    }
  }, [messagesContainerRef, handleScroll]);

  const scrollToBottom = useCallback((force = false) => {
    // فقط اگر فورس باشد (مثلاً ارسال پیام جدید توسط کاربر) 
    // یا اگر کاربر قبلاً پایین صفحه بوده است، اسکرول کن.
    if (messagesEndRef.current && messagesContainerRef.current) {
      if (force || isAtBottomRef.current) {
        messagesContainerRef.current.scrollTo({
          top: messagesContainerRef.current.scrollHeight,
          behavior: 'smooth'
        })
      }
    }
  }, [messagesEndRef, messagesContainerRef]);

  // وقتی پیامی ارسال می‌شود، فورس اسکرول کن
  useEffect(() => {
    if(isLoading) {
        // وقتی لودینگ شروع می‌شود یعنی پیام کاربر ارسال شده، پس برو پایین
        scrollToBottom(true); 
    }
  }, [isLoading, scrollToBottom]);

  // وقتی محتوا آپدیت می‌شود (استریم)، اسمارت اسکرول کن
  useEffect(() => {
    scrollToBottom(false);
  }, [selectedConversation?.messages, scrollToBottom]);


  useEffect(() => {
    const handleResize = () => {
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
        textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px'
      }
    }

    const textarea = textareaRef.current
    if (textarea) {
      textarea.addEventListener('input', handleResize)
      handleResize()
    }

    return () => {
      if (textarea) {
        textarea.removeEventListener('input', handleResize)
      }
    }
  }, [newMessage, textareaRef])


  const optimizedMessages = useMemo(() => {
    if (!selectedConversation?.messages) return null

    const messagesLength = selectedConversation.messages.length;

    return selectedConversation.messages.map((message: any, index: number) => {
      const isLastMessage = index === messagesLength - 1;
      const isTyping = isLoading && message.role === 'assistant' && isLastMessage;

      const displayContent = isTyping && !message.content ? '' : (message.content || '')

      const processedContent = displayContent
        .replace(/([a-zA-Z0-9])([آ-ی])/g, '$1 $2')
        .replace(/([آ-ی])([a-zA-Z0-9])/g, '$1 $2');

      return {
        ...message,
        content: processedContent,
        isTyping,
        displayContent: processedContent
      }
    })
  }, [selectedConversation?.messages, isLoading])

  const renderedMessages = useMemo(() => {
    if (!optimizedMessages) return null

    return optimizedMessages.map((message: any, index: number) => {
      const isLastMessage = index === optimizedMessages.length - 1;

      return (
        <MessageBubble
          key={message.id}
          message={message}
          isTyping={message.isTyping}
          isLastMessage={isLastMessage}
          onCopy={copyMessage}
          onRegenerate={regenerateMessage}
          onSourceClick={handleSourceClick}
          copiedMessageId={copiedMessageId}
          isLoading={isLoading}
        />
      )
    })
  }, [optimizedMessages, copyMessage, regenerateMessage, handleSourceClick, copiedMessageId, isLoading])


  // --- تغییر جدید: Global Typography (Vazir + 1rem) ---
  // اضافه کردن استایل مستقیم یا کلاس به دیو اصلی
  return (
    <div 
        className="flex-1 flex flex-col bg-gray-50 overflow-x-hidden"
        style={{ fontFamily: '"Vazir", sans-serif', fontSize: '1rem' }}
    >
      {/* Chat Header */}
      <div className="bg-gradient-to-r from-white to-purple-50/20 border-b border-purple-100 p-4 backdrop-blur-sm">
        <div className="flex items-center justify-between min-w-0">
          <div className="flex items-center gap-2 md:gap-4 flex-wrap min-w-0">
            <div className="flex items-center gap-1 md:gap-2 px-2 md:px-3 py-1.5 bg-white/80 backdrop-blur-sm rounded-lg border border-purple-100 shadow-sm hover:shadow-md transition-shadow duration-200 min-w-0">
              <span className="text-xs text-gray-500 font-medium whitespace-nowrap">مدل:</span>
              <span className="text-xs md:text-sm font-semibold text-purple-700 truncate">
                {selectedModel || 'پیش‌فرض'}
              </span>
            </div>
            <div className="flex items-center gap-1 md:gap-2 px-2 md:px-3 py-1.5 bg-white/80 backdrop-blur-sm rounded-lg border border-purple-100 shadow-sm hover:shadow-md transition-shadow duration-200 min-w-0">
              <span className="text-xs text-gray-500 font-medium whitespace-nowrap">حالت:</span>
              <span className="text-xs md:text-sm font-semibold text-purple-700 truncate">
                {getRagTypeLabel(ragType)}
              </span>
            </div>
            <div className="flex items-center gap-1 md:gap-2 px-2 md:px-3 py-1.5 bg-white/80 backdrop-blur-sm rounded-lg border border-purple-100 shadow-sm hover:shadow-md transition-shadow duration-200 min-w-0">
              <span className="text-xs text-gray-500 font-medium whitespace-nowrap">دما:</span>
              <span className="text-xs md:text-sm font-semibold text-purple-700 truncate">
                {temperature}
              </span>
            </div>
          </div>
          
          {FEATURE_FLAGS.SHOW_SETTINGS && (
            <button
              onClick={() => setShowSettingsModal(true)}
              className="flex items-center gap-1 md:gap-2 px-2 md:px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-lg shadow-md hover:shadow-lg transition-all duration-200 transform hover:scale-105 group flex-shrink-0"
              title="تنظیمات پیشرفته"
            >
              <Settings className="w-4 h-4 group-hover:rotate-90 transition-transform duration-300" />
              <span className="text-xs md:text-sm font-medium hidden sm:inline">تنظیمات</span>
            </button>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div
        ref={messagesContainerRef}
        onScroll={checkScrollPosition}
        data-messages-container
        className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth"
      >
        {selectedConversation ? (
          <>
            {selectedConversation.messages && selectedConversation.messages.length > 0 ? (
              renderedMessages
            ) : (
              <div className="text-center text-gray-500 py-8">
                <p className="text-sm">این گفتگو هنوز پیامی ندارد</p>
                <p className="text-xs mt-1">پیام خود را در کادر پایین بنویسید</p>
              </div>
            )}
            
            {/* حذف شد: پیام thinking اضافی که باعث نمایش دو حباب میشد */}
            
            <div ref={messagesEndRef} />
          </>
        ) : (
          <WelcomeMessage
            onExampleClick={(message) => {
              setNewMessage(message)
              setTimeout(() => {
                if (textareaRef.current) {
                  textareaRef.current.focus()
                }
              }, 100)
            }}
          />
        )}

        {/* Go to bottom button */}
        <button
          id="go-to-bottom-btn"
          onClick={handleGoToBottom}
          title="برو به آخرین پیام"
          aria-label="برو به آخرین پیام"
          className={`fixed left-4 bottom-36 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 border-2 border-purple-100 rounded-full w-12 h-12 flex items-center justify-center cursor-pointer shadow-xl hover:shadow-2xl transition-all duration-200 z-[9999] ring-2 ring-purple-50 ${
            showGoToBottomBtn ? 'opacity-100 visible' : 'opacity-0 invisible'
          }`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" width="20" height="20">
            <path d="M12 15.586l-4.293-4.293-1.414 1.414L12 18.414l5.707-5.707-1.414-1.414L12 15.586z"/>
            <path d="M12 8.586l-4.293-4.293-1.414 1.414L12 11.414l5.707-5.707-1.414-1.414L12 8.586z"/>
          </svg>
        </button>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 p-3 md:p-4">
        <div className="flex items-end gap-2 min-w-0">
          <Button
            onClick={handleSendMessage}
            disabled={!newMessage.trim() || isLoading}
            className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 h-10 w-10 md:h-12 md:w-12 rounded-xl flex items-center justify-center flex-shrink-0"
            aria-label="ارسال پیام"
          >
            {isLoading ? (
              <div className="animate-spin rounded-full h-4 w-4 md:h-5 md:w-5 border-2 border-white border-t-transparent"></div>
            ) : (
              <Send className="h-4 w-4 md:h-5 md:w-5" />
            )}
          </Button>
          
          {FEATURE_FLAGS.SHOW_VOICE_INPUT && (
            <VoiceInput
              onTranscriptionComplete={(text) => {
                setNewMessage((prev: string) => prev ? `${prev}\n${text}` : text)
              }}
              disabled={isLoading}
            />
          )}
          
          <div className="flex-1 min-w-0">
            <Textarea
              ref={textareaRef}
              value={newMessage}
              onChange={(e) => {
                setNewMessage(e.target.value)
              }}
              onKeyPress={handleKeyPress}
              placeholder={selectedConversation ? "پیام خود را بنویسید..." : "برای شروع گفتگو، پیام خود را بنویسید..."}
              className="resize-none min-h-[40px] max-h-[200px] overflow-y-hidden text-sm md:text-base leading-relaxed text-gray-900 w-full"
              rows={1}
              disabled={isLoading}
              aria-label="ورودی پیام"
            />
          </div>
        </div>
        
        <div className="flex items-center justify-between mt-2 text-xs text-gray-500 min-w-0">
          <div className="flex items-center gap-1 md:gap-2 min-w-0">
            <span className="hidden md:inline whitespace-nowrap">Enter برای ارسال، Shift+Enter برای خط جدید</span>
            {FEATURE_FLAGS.SHOW_SETTINGS && (
              <button
                onClick={() => setShowSettingsModal(true)}
                className="flex items-center gap-1 px-2 md:px-3 py-1.5 bg-gradient-to-r from-purple-50 to-blue-50 hover:from-purple-100 hover:to-blue-100 text-purple-600 hover:text-purple-700 rounded-lg transition-all duration-200 border border-purple-200 hover:border-purple-300 flex-shrink-0"
                aria-label="تنظیمات پیشرفته"
                title="تنظیمات پیشرفته"
              >
                <Settings className="w-3.5 h-3.5" />
                <span className="hidden lg:inline text-xs font-medium">تنظیمات</span>
              </button>
            )}
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            <span className="whitespace-nowrap">حالت فعال: {getRagTypeLabel(ragType)}</span>
          </div>
        </div>
      </div>
    </div>
  )
})

ChatContainer.displayName = 'ChatContainer'

export default ChatContainer