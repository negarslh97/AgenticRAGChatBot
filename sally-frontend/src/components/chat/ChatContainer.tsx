import React, { useRef, useEffect, useCallback } from 'react'
import { Button } from '../ui/button'
import { Textarea } from '../ui/textarea'
import { VoiceInput } from '../ui/voice-input'
import { toast } from 'react-hot-toast'
import { Send, HelpCircle, Settings } from 'lucide-react'
import MessageBubble from './MessageBubble'
import { WelcomeMessage } from './WelcomeMessage'
import { Conversation as BaseConversation } from '../../types/chat'

// Extended conversation type that includes API properties
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
  streamContentGradually: (messageId: string, content: string, delay?: number) => void
  typewriterMessages: { [key: string]: string }
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

const ChatContainer: React.FC<ChatContainerProps> = ({
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
  streamContentGradually,
  typewriterMessages,
  copiedMessageId,
  copyMessage,
  retryMessage,
  regenerateMessage,
  handleSourceClick,
  FEATURE_FLAGS
}) => {
  const scrollToBottom = useCallback(() => {
    if (messagesEndRef.current && messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: messagesContainerRef.current.scrollHeight,
        behavior: 'smooth'
      })
    }
  }, [messagesEndRef, messagesContainerRef])

  useEffect(() => {
    scrollToBottom()
  }, [selectedConversation?.messages, scrollToBottom])

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

  const renderMessage = (message: any) => {
    const isTyping = isThinking && message.role === 'assistant' && !message.content
    const displayContent = isTyping ? '' : (typewriterMessages[message.id] || message.content || '')

    return (
      <MessageBubble
        key={message.id}
        message={{
          ...message,
          content: displayContent
        }}
        isTyping={isTyping}
        onCopy={copyMessage}
        onRegenerate={regenerateMessage}
        onSourceClick={handleSourceClick}
        copiedMessageId={copiedMessageId}
        isLoading={isLoading}
      />
    )
  }

  const renderThinkingMessage = () => {
    // Create a temporary message for thinking state
    const thinkingMessage = {
      id: 'thinking-temp',
      content: '',
      role: 'assistant' as const,
      timestamp: new Date(),
      sender_type: 'AI' as const,
      metadata: {}
    }

    return (
      <MessageBubble
        key="thinking-temp"
        message={thinkingMessage}
        isTyping={true}
        onCopy={copyMessage}
        onRegenerate={regenerateMessage}
        onSourceClick={handleSourceClick}
        copiedMessageId={copiedMessageId}
        isLoading={isLoading}
      />
    )
  }

  return (
    <div className="flex-1 flex flex-col bg-gray-50">
      {/* Chat Header */}
      <div className="bg-gradient-to-r from-white to-purple-50/20 border-b border-purple-100 p-4 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-white/80 backdrop-blur-sm rounded-lg border border-purple-100 shadow-sm hover:shadow-md transition-shadow duration-200">
              <span className="text-xs text-gray-500 font-medium">مدل:</span>
              <span className="text-sm font-semibold text-purple-700">
                {selectedModel || 'پیش‌فرض'}
              </span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-white/80 backdrop-blur-sm rounded-lg border border-purple-100 shadow-sm hover:shadow-md transition-shadow duration-200">
              <span className="text-xs text-gray-500 font-medium">حالت:</span>
              <span className="text-sm font-semibold text-purple-700">
                {getRagTypeLabel(ragType)}
              </span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-white/80 backdrop-blur-sm rounded-lg border border-purple-100 shadow-sm hover:shadow-md transition-shadow duration-200">
              <span className="text-xs text-gray-500 font-medium">دما:</span>
              <span className="text-sm font-semibold text-purple-700">
                {temperature}
              </span>
            </div>
          </div>
          
          {FEATURE_FLAGS.SHOW_SETTINGS && (
            <button
              onClick={() => setShowSettingsModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-lg shadow-md hover:shadow-lg transition-all duration-200 transform hover:scale-105 group"
              title="تنظیمات پیشرفته"
            >
              <Settings className="w-4 h-4 group-hover:rotate-90 transition-transform duration-300" />
              <span className="text-sm font-medium hidden sm:inline">تنظیمات</span>
            </button>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div
        ref={messagesContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 space-y-4"
      >
        {selectedConversation ? (
          <>
            {console.log('🔍 Rendering conversation:', selectedConversation.id, 'with', selectedConversation.messages?.length, 'messages')}
            {selectedConversation.messages && selectedConversation.messages.length > 0 ? (
              selectedConversation.messages.map(renderMessage)
            ) : (
              <div className="text-center text-gray-500 py-8">
                <p className="text-sm">این گفتگو هنوز پیامی ندارد</p>
                <p className="text-xs mt-1">پیام خود را در کادر پایین بنویسید</p>
              </div>
            )}
            
            {/* Thinking Indicator - Show inside message bubble */}
            {isThinking && !selectedConversation.messages?.some((m: any) => m.role === 'assistant' && !m.content) && renderThinkingMessage()}
            
            <div ref={messagesEndRef} />
          </>
        ) : (
          <WelcomeMessage
            onExampleClick={(message) => {
              setNewMessage(message)
              // Focus on input after setting message
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
          className={`fixed left-20 bg-white border border-gray-300 rounded-full w-10 h-10 flex items-center justify-center cursor-pointer shadow-lg hover:shadow-xl transition-all duration-200 z-10 pointer-events-auto ${
            showGoToBottomBtn ? 'block' : 'hidden'
          }`}
          style={{ bottom: 'calc(130px + 1rem)' }}
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
            <path d="M12 15.586l-4.293-4.293-1.414 1.414L12 18.414l5.707-5.707-1.414-1.414L12 15.586z"/>
            <path d="M12 8.586l-4.293-4.293-1.414 1.414L12 11.414l5.707-5.707-1.414-1.414L12 8.586z"/>
          </svg>
        </button>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 p-3 md:p-4">
        <div className="flex items-end gap-2">
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
          
          <div className="flex-1">
            <Textarea
              ref={textareaRef}
              value={newMessage}
              onChange={(e) => {
                setNewMessage(e.target.value)
              }}
              onKeyPress={handleKeyPress}
              placeholder={selectedConversation ? "پیام خود را بنویسید..." : "برای شروع گفتگو، پیام خود را بنویسید..."}
              className="resize-none min-h-[40px] max-h-[200px] overflow-y-hidden text-sm md:text-base leading-relaxed"
              rows={1}
              disabled={isLoading}
              aria-label="ورودی پیام"
            />
          </div>
        </div>
        
        <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
          <div className="flex items-center gap-2">
            <span className="hidden md:inline">Enter برای ارسال، Shift+Enter برای خط جدید</span>
            {FEATURE_FLAGS.SHOW_SETTINGS && (
              <button
                onClick={() => setShowSettingsModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-purple-50 to-blue-50 hover:from-purple-100 hover:to-blue-100 text-purple-600 hover:text-purple-700 rounded-lg transition-all duration-200 border border-purple-200 hover:border-purple-300"
                aria-label="تنظیمات پیشرفته"
                title="تنظیمات پیشرفته"
              >
                <Settings className="w-3.5 h-3.5" />
                <span className="hidden lg:inline text-xs font-medium">تنظیمات</span>
              </button>
            )}
          </div>
          <div className="flex items-center gap-1">
            <span className="mr-1">حالت فعال: {getRagTypeLabel(ragType)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatContainer