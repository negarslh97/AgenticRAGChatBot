import React, { useState, useRef, useEffect, KeyboardEvent, useCallback } from 'react'
import {
  Plus,
  Send,
  Bot,
  User,
  ChevronLeft,
  ChevronRight,
  Lightbulb,
  HelpCircle,
  Trash2,
  Search,
  Brain,
  Target,
  ExternalLink,
  ThumbsUp,
  ThumbsDown,
  Menu,
  X
} from 'lucide-react'
import { Button } from '../components/ui/button'
import { Textarea } from '../components/ui/textarea'
import { MarkdownRenderer } from '../components/ui/markdown-renderer'
import { chatService, Conversation as ApiConversation } from '../services/chatService'
import { useAuth } from '../context/AuthContext'
import { toast } from 'react-hot-toast'
import ArticleHighlightModal from '../components/ArticleHighlightModal'

interface Source {
  id: string
  title: string
  score?: number
  snippet?: string
  category?: string
  tags?: string[]
}

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
  sender_type?: 'Customer' | 'Admin' | 'SuperAdmin' | 'Guest' | 'AI'
  is_failed?: boolean
  failure_reason?: string
  rating?: {
    rating: number
    comment?: string
    rated_by?: string
    rated_at?: string
  }
  metadata?: {
    model_name?: string
    provider?: string
    confidence?: number
    rag_type?: string
    token_usage?: {
      prompt_tokens?: number
      completion_tokens?: number
      total_tokens?: number
    }
    response_time?: number
  }
  sources?: Source[]
  confidence?: number
  suggested_actions?: string[]
}

interface Conversation {
  id: string
  title: string
  messages: Message[]
  created_at?: string
  updated_at?: string
}

type RAGType = 'simple' | 'agentic'

const CustomerChatPage = () => {
  const { user } = useAuth()
  const [isSidebarOpen, setIsSidebarOpen] = useState(false) // ✅ Default: closed on mobile
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)
  const [newMessage, setNewMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isInitialLoading, setIsInitialLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [guestSessionId, setGuestSessionId] = useState<string | null>(null)
  const ragType = 'agentic' // ✅ همیشه Agentic برای مشتریان
  const [useStreaming, setUseStreaming] = useState(true) // 🌊 Streaming enabled by default
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  // 🔥 Article Highlight Modal state
  const [highlightModal, setHighlightModal] = useState<{
    isOpen: boolean
    articleId: string
    userQuery: string
  }>({ isOpen: false, articleId: '', userQuery: '' })

  // Auto-open sidebar on desktop
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setIsSidebarOpen(true)
      } else {
        setIsSidebarOpen(false)
      }
    }
    
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen)
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // Initialize guest session if user is not authenticated
  const initializeGuestSession = useCallback(() => {
    if (!user) {
      const sessionId = localStorage.getItem('guest_session_id') || `guest_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      localStorage.setItem('guest_session_id', sessionId)
      setGuestSessionId(sessionId)
      console.log('👤 Guest session initialized:', sessionId)
    }
  }, [user])

  // Load conversations from API
  const loadConversations = useCallback(async () => {
    try {
      console.log('🔄 Loading conversations from API...')
      console.log('👤 User:', user)
      const response = await chatService.getConversations()
      console.log('📦 Raw response:', response)

      if (response && Array.isArray(response)) {
        const formattedConversations: Conversation[] = response.map(conv => ({
          id: conv.id,
          title: conv.title,
          messages: [],
          created_at: conv.created_at,
          updated_at: conv.updated_at
        }))
        console.log('✅ Loaded conversations:', formattedConversations.length)
        console.log('📋 Conversations:', formattedConversations)
        setConversations(formattedConversations)
      } else {
        console.log('⚠️ Response is not an array:', response)
        setConversations([])
      }
    } catch (error: any) {
      console.error('❌ Error loading conversations:', error)
      console.error('❌ Error details:', error.response?.data)
      if (error.response?.status !== 401) {
        toast.error('خطا در بارگذاری مکالمات')
      }
    } finally {
      setIsInitialLoading(false)
    }
  }, [user])

  // Load messages for a conversation
  const loadMessages = useCallback(async (conversationId: string) => {
    try {
      console.log('📥 Loading messages for conversation:', conversationId)
      const response = await chatService.getConversationMessages(conversationId, guestSessionId ?? undefined)

      if (response && Array.isArray(response)) {
        const formattedMessages: Message[] = response.map((msg: any) => ({
          id: msg.id,
          content: msg.content,
          role: msg.sender_type === 'AI' || msg.sender_type === 'ai' ? 'assistant' : 'user',
          timestamp: new Date(msg.created_at),
          sender_type: msg.sender_type,
          is_failed: msg.is_failed,
          failure_reason: msg.failure_reason,
          metadata: msg.metadata,
          sources: msg.metadata?.sources || [],
          confidence: msg.metadata?.confidence,
          suggested_actions: msg.metadata?.suggested_actions || []
        }))

        setSelectedConversation(prev => ({
          ...prev!,
          messages: formattedMessages
        }))

        setTimeout(scrollToBottom, 100)
      }
    } catch (error) {
      console.error('❌ Error loading messages:', error)
      toast.error('خطا در بارگذاری پیام‌ها')
    }
  }, [guestSessionId])

  // Initialize
  useEffect(() => {
    initializeGuestSession()
    loadConversations()
  }, [initializeGuestSession, loadConversations])

  // Create new conversation
  const createNewConversation = () => {
    const newConv: Conversation = {
      id: `temp_${Date.now()}`,
      title: 'گفتگوی جدید',
      messages: []
    }
    setConversations(prev => [newConv, ...prev])
    setSelectedConversation(newConv)
    setNewMessage('')
  }

  // Send message with Streaming Support
  const sendMessage = async () => {
    if (!newMessage.trim() || isLoading) return

    const userMessageContent = newMessage.trim()
    setNewMessage('')
    setIsLoading(true)

    // Add user message to UI
    const tempUserMessage: Message = {
      id: `temp_${Date.now()}`,
      content: userMessageContent,
      role: 'user',
      timestamp: new Date(),
      sender_type: user ? 'Customer' : 'Guest'
    }

    if (!selectedConversation) {
      createNewConversation()
    }

    setSelectedConversation(prev => ({
      ...prev!,
      messages: [...(prev?.messages || []), tempUserMessage]
    }))

    try {
      // 🌊 Use streaming for better UX
      if (useStreaming) {
        let streamedContent = ''
        let conversationId = selectedConversation?.id?.startsWith('temp_') ? undefined : selectedConversation?.id
        let messageMetadata: any = {}
        
        // Create AI message placeholder
        const aiMessageId = `msg_${Date.now()}`
        const aiMessage: Message = {
          id: aiMessageId,
          content: '',
          role: 'assistant',
          timestamp: new Date(),
          sender_type: 'AI',
          sources: [],
          confidence: 0.5,
          suggested_actions: [],
          metadata: {
            rag_type: ragType
          }
        }

        setSelectedConversation(prev => ({
          ...prev!,
          messages: [...(prev?.messages || []), aiMessage]
        }))

        // Handle streaming events
        const handleEvent = (evt: any) => {
          console.log('📦 Stream event:', evt.type)
          
          if (evt.type === 'conversation_id') {
            conversationId = evt.conversation_id
          } else if (evt.type === 'chunk') {
            streamedContent += evt.content
            setSelectedConversation(prev => ({
              ...prev!,
              messages: prev!.messages.map(msg =>
                msg.id === aiMessageId
                  ? { ...msg, content: streamedContent }
                  : msg
              )
            }))
            setTimeout(scrollToBottom, 10)
          } else if (evt.type === 'metadata') {
            messageMetadata = evt
            setSelectedConversation(prev => ({
              ...prev!,
              id: conversationId || prev!.id,
              messages: prev!.messages.map(msg =>
                msg.id === aiMessageId
                  ? {
                      ...msg,
                      content: streamedContent,
                      sources: evt.sources || [],
                      confidence: evt.confidence,
                      suggested_actions: evt.actions_taken || [],
                      metadata: {
                        rag_type: ragType,
                        confidence: evt.confidence,
                        complexity: evt.complexity
                      }
                    }
                  : msg
              )
            }))
          } else if (evt.type === 'done') {
            setIsLoading(false)
            // Update conversation list if new conversation
            if (selectedConversation?.id?.startsWith('temp_') || !selectedConversation) {
              loadConversations()
            }
          } else if (evt.type === 'error') {
            console.error('Stream error:', evt.message)
            setSelectedConversation(prev => ({
              ...prev!,
              messages: prev!.messages.map(msg =>
                msg.id === aiMessageId
                  ? {
                      ...msg,
                      content: 'متأسفانه خطایی رخ داد. لطفاً دوباره تلاش کنید.',
                      is_failed: true,
                      failure_reason: evt.message
                    }
                  : msg
              )
            }))
            setIsLoading(false)
            toast.error('خطا در ارسال پیام')
          }
        }

        // Start streaming
        if (ragType === 'agentic' && user) {
          console.log('🌊 Using Agentic RAG Streaming...')
          await chatService.sendAdvancedAgenticMessageStream(
            userMessageContent,
            conversationId,
            handleEvent
          )
        } else {
          console.log('🌊 Using Simple RAG Streaming...')
          await chatService.sendMessageStream(
            userMessageContent,
            conversationId,
            guestSessionId || undefined,
            handleEvent
          )
        }
      } else {
        // Non-streaming (original behavior)
        let response: {
          conversation_id: string
          message: string
          sources: Source[]
          confidence: number
          suggested_actions: string[]
          message_id: string
        }

        if (ragType === 'agentic' && user) {
          console.log('🧠 Using Agentic RAG...')
          
          const apiResponse = await chatService.sendAdvancedAgenticMessage({
            query: userMessageContent,
            conversation_id: selectedConversation?.id?.startsWith('temp_') ? null : selectedConversation?.id
          })

          response = {
            conversation_id: apiResponse.conversation_id,
            message: apiResponse.response,
            sources: apiResponse.sources || [],
            confidence: apiResponse.confidence || 0.5,
            suggested_actions: apiResponse.suggested_actions || [],
            message_id: apiResponse.conversation_id
          }
        } else {
          console.log('💬 Using Simple RAG...')
          response = await chatService.sendMessage({
            content: userMessageContent,
            conversation_id: selectedConversation?.id?.startsWith('temp_') ? null : selectedConversation?.id,
            guest_session_id: guestSessionId
          })
        }

        // Add AI response to UI
        const aiMessage: Message = {
          id: response.message_id || `msg_${Date.now()}`,
          content: response.message,
          role: 'assistant',
          timestamp: new Date(),
          sender_type: 'AI',
          sources: response.sources || [],
          confidence: response.confidence,
          suggested_actions: response.suggested_actions || [],
          metadata: {
            rag_type: ragType,
            confidence: response.confidence
          }
        }

        setSelectedConversation(prev => ({
          ...prev!,
          id: response.conversation_id,
          messages: [...(prev?.messages || []), aiMessage]
        }))

        // Update conversation list
        if (selectedConversation?.id?.startsWith('temp_') || !selectedConversation) {
          loadConversations()
        }

        setTimeout(scrollToBottom, 100)
        setIsLoading(false)
      }
    } catch (error: any) {
      console.error('❌ Error sending message:', error)
      
      // Add error message
      const errorMessage: Message = {
        id: `error_${Date.now()}`,
        content: 'متأسفانه خطایی رخ داد. لطفاً دوباره تلاش کنید.',
        role: 'assistant',
        timestamp: new Date(),
        sender_type: 'AI',
        is_failed: true,
        failure_reason: error.response?.data?.detail || error.message
      }

      setSelectedConversation(prev => ({
        ...prev!,
        messages: [...(prev?.messages || []), errorMessage]
      }))

      toast.error(error.response?.data?.detail || 'خطا در ارسال پیام')
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // Delete conversation
  const deleteConversation = async (conversationId: string) => {
    try {
      await chatService.deleteConversation(conversationId)
      setConversations(prev => prev.filter(c => c.id !== conversationId))
      if (selectedConversation?.id === conversationId) {
        setSelectedConversation(null)
      }
      toast.success('مکالمه حذف شد')
    } catch (error) {
      console.error('Error deleting conversation:', error)
      toast.error('خطا در حذف مکالمه')
    }
  }

  // Filter conversations
  const filteredConversations = conversations.filter(conv =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Render source card
  const renderSource = (source: Source, index: number, userQuery: string = '') => (
    <div
      key={index}
      className="bg-gray-50 border border-gray-200 rounded-lg p-2 md:p-3 hover:bg-gray-100 transition-colors"
    >
      <div className="flex items-start justify-between mb-1 gap-2">
        <div className="flex items-center gap-1 md:gap-2 min-w-0 flex-1">
          <Target className="w-3 h-3 md:w-4 md:h-4 text-blue-600 flex-shrink-0" />
          <h4 className="font-medium text-xs md:text-sm text-gray-900 truncate">{source.title}</h4>
        </div>
        {source.score && (
          <span className="text-xs bg-blue-100 text-blue-700 px-1.5 md:px-2 py-0.5 md:py-1 rounded flex-shrink-0">
            {Math.round(source.score * 100)}%
          </span>
        )}
      </div>
      {source.snippet && (
        <p className="text-xs text-gray-600 mt-1 line-clamp-2">{source.snippet}</p>
      )}
      {source.tags && source.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {source.tags.slice(0, 3).map((tag, idx) => (
            <span key={idx} className="text-xs bg-gray-200 text-gray-700 px-1.5 md:px-2 py-0.5 rounded">
              {tag}
            </span>
          ))}
        </div>
      )}
      <Button
        size="sm"
        variant="ghost"
        className="mt-2 text-xs h-6 w-full md:w-auto"
        onClick={() => {
          setHighlightModal({
            isOpen: true,
            articleId: source.id,
            userQuery: userQuery
          })
        }}
      >
        <ExternalLink className="w-3 h-3 mr-1" />
        <span className="hidden md:inline">مشاهده مقاله</span>
        <span className="md:hidden">مشاهده</span>
      </Button>
    </div>
  )

  return (
    <div className="flex h-[calc(100vh-130px)] bg-gradient-to-br from-gray-50 to-gray-100 overflow-hidden">
      {/* Mobile Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={toggleSidebar}
        />
      )}

      {/* Sidebar */}
      <div className={`
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        lg:translate-x-0
        fixed lg:relative
        z-50 lg:z-auto
        w-80 max-w-[85vw]
        h-full
        transition-transform duration-300
        bg-white border-r border-gray-200 
        flex flex-col overflow-hidden
        ${!isSidebarOpen && 'lg:w-0'}
      `}>
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <Brain className="w-5 h-5 text-purple-600" />
              گفتگوها
            </h2>
          </div>

          {/* New Chat Button */}
          <Button
            onClick={createNewConversation}
            className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white shadow-md"
          >
            <Plus className="w-4 h-4 mr-2" />
            گفتگوی جدید
          </Button>

          {/* Search */}
          <div className="mt-3 relative">
            <Search className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="جستجو در مکالمات..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pr-10 pl-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
            />
          </div>
        </div>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto">
          {isInitialLoading ? (
            <div className="p-4 text-center text-gray-500">در حال بارگذاری...</div>
          ) : filteredConversations.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              <p>هنوز مکالمه‌ای ندارید</p>
              <p className="text-sm mt-1">یک گفتگوی جدید شروع کنید</p>
            </div>
          ) : (
            filteredConversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => {
                  setSelectedConversation(conv)
                  if (!conv.id.startsWith('temp_')) {
                    loadMessages(conv.id)
                  }
                }}
                className={`p-4 border-b border-gray-100 cursor-pointer transition-colors ${
                  selectedConversation?.id === conv.id
                    ? 'bg-gradient-to-r from-purple-50 to-blue-50 border-r-4 border-purple-600'
                    : 'hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-gray-900 truncate flex-1">{conv.title}</h3>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={(e) => {
                      e.stopPropagation()
                      deleteConversation(conv.id)
                    }}
                    className="opacity-0 group-hover:opacity-100"
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </Button>
                </div>
                {conv.updated_at && (
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(conv.updated_at).toLocaleDateString('fa-IR')}
                  </p>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Toggle Sidebar Button - Desktop Only */}
      <button
        onClick={toggleSidebar}
        className="hidden lg:block absolute left-full top-1/2 transform -translate-y-1/2 bg-white border border-gray-200 rounded-r-lg p-2 hover:bg-gray-50 shadow-md z-10"
      >
        {isSidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
      </button>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 p-3 md:p-4 shadow-sm z-20 flex-shrink-0">
          <div className="flex items-center justify-between gap-3">
            {/* Mobile Menu Button */}
            <button
              onClick={toggleSidebar}
              className="lg:hidden p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              {isSidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            
            <div className="flex-1 min-w-0">
              <h1 className="text-lg md:text-xl font-bold text-gray-900 truncate">
                {selectedConversation?.title || 'گفتگوی جدید'}
              </h1>
              <p className="text-xs md:text-sm text-gray-600 flex items-center gap-2 mt-1">
                <Brain className="w-3 h-3 md:w-4 md:h-4 text-purple-600 flex-shrink-0" />
                <span className="truncate">حالت پیشرفته - جستجوی هوشمند فعال</span>
              </p>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-3 md:p-6 space-y-4 md:space-y-6">
          {!selectedConversation || selectedConversation.messages.length === 0 ? (
            <div className="h-window flex flex-col items-center justify-center text-gray-500 space-y-4 px-4">
              <div className="w-12 h-12 md:w-16 md:h-16 bg-gradient-to-r from-purple-100 to-blue-100 rounded-full flex items-center justify-center">
                <Brain className="w-6 h-6 md:w-8 md:h-8 text-purple-600" />
              </div>
              <div className="text-center max-w-md">
                <h3 className="text-base md:text-lg font-semibold text-gray-700">
                  دستیار هوشمند پیشرفته
                </h3>
                <p className="text-xs md:text-sm mt-2 px-4">
                  سوالات پیچیده خود را بپرسید. من با جستجوی هوشمند و تحلیل عمیق پاسخ دقیقی به شما می‌دهم.
                </p>
              </div>
              
              {/* Suggested Questions */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 md:gap-3 mt-4 md:mt-6 w-full max-w-2xl px-2">
                {[
                  { icon: Lightbulb, text: 'چطور محصول را راه‌اندازی کنم؟' },
                  { icon: HelpCircle, text: 'مشکل خطای اتصال را چطور حل کنم؟' },
                  { icon: Target, text: 'بهترین روش برای پشتیبان‌گیری چیست؟' },
                  { icon: Brain, text: 'چطور عملکرد را بهبود دهم؟' }
                ].map((item, i) => (
                  <button
                    key={i}
                    onClick={() => setNewMessage(item.text)}
                    className="flex items-center gap-2 md:gap-3 p-2 md:p-3 bg-white border border-gray-200 rounded-lg hover:border-purple-300 hover:bg-purple-50 transition-all text-right group"
                  >
                    <item.icon className="w-4 h-4 md:w-5 md:h-5 text-gray-400 group-hover:text-purple-600 flex-shrink-0" />
                    <span className="text-xs md:text-sm text-gray-700 group-hover:text-purple-700">{item.text}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            selectedConversation.messages.map((message, messageIndex) => {
              // برای پیام‌های AI، آخرین پیام کاربر قبلی را پیدا کن
              let userQuery = ''
              if (message.role === 'assistant') {
                for (let i = messageIndex - 1; i >= 0; i--) {
                  if (selectedConversation.messages[i].role === 'user') {
                    userQuery = selectedConversation.messages[i].content
                    break
                  }
                }
              }
              
              return (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex gap-2 md:gap-3 max-w-full md:max-w-3xl ${message.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  {/* Avatar */}
                  <div className={`w-8 h-8 md:w-10 md:h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                    message.role === 'user'
                      ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white'
                      : message.is_failed
                      ? 'bg-red-100 text-red-600'
                      : 'bg-gradient-to-r from-green-100 to-blue-100 text-green-700'
                  }`}>
                    {message.role === 'user' ? (
                      <User className="w-4 h-4 md:w-5 md:h-5" />
                    ) : (
                      <Bot className="w-4 h-4 md:w-5 md:h-5" />
                    )}
                  </div>

                  {/* Message Content */}
                  <div className={`flex-1 min-w-0 ${message.role === 'user' ? 'text-right' : ''}`}>
                    <div className={`rounded-2xl px-3 py-2 md:px-5 md:py-3 ${
                      message.role === 'user'
                        ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white'
                        : message.is_failed
                        ? 'bg-red-50 border border-red-200 text-red-900'
                        : 'bg-white border border-gray-200 text-gray-900'
                    }`}>
                      {message.role === 'assistant' ? (
                        <div className="text-xs md:text-sm leading-relaxed">
                          <MarkdownRenderer 
                            content={message.content}
                            variant="compact"
                          />
                        </div>
                      ) : (
                        <p className="text-xs md:text-sm leading-relaxed whitespace-pre-wrap break-words">{message.content}</p>
                      )}
                      
                      {/* Confidence Score */}
                      {message.role === 'assistant' && message.confidence !== undefined && (
                        <div className="mt-3 flex items-center gap-2">
                          <div className="flex-1 bg-gray-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${
                                message.confidence > 0.7 ? 'bg-green-500' :
                                message.confidence > 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                              }`}
                              style={{ width: `${message.confidence * 100}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-600">
                            {Math.round(message.confidence * 100)}% اطمینان
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Sources */}
                    {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                      <div className="mt-2 md:mt-3 space-y-2">
                        <p className="text-xs text-gray-600 font-medium flex items-center gap-1">
                          <Target className="w-3 h-3" />
                          منابع ({message.sources.length}):
                        </p>
                        <div className="grid grid-cols-1 gap-1 md:gap-2">
                          {message.sources.slice(0, 3).map((source, idx) => renderSource(source, idx, userQuery))}
                        </div>
                      </div>
                    )}

                    {/* Suggested Actions */}
                    {message.role === 'assistant' && message.suggested_actions && message.suggested_actions.length > 0 && (
                      <div className="mt-3">
                        <p className="text-xs text-gray-600 font-medium mb-2">اقدامات پیشنهادی:</p>
                        <div className="flex flex-wrap gap-2">
                          {message.suggested_actions.map((action, idx) => (
                            <span
                              key={idx}
                              className="text-xs bg-blue-100 text-blue-700 px-3 py-1 rounded-full"
                            >
                              {action}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Metadata */}
                    {message.metadata && (
                      <div className="mt-2 text-xs text-gray-500 space-y-1">
                        {message.metadata.rag_type && (
                          <p>نوع: {message.metadata.rag_type === 'agentic' ? 'پیشرفته' : 'ساده'}</p>
                        )}
                        {message.metadata.response_time && (
                          <p>زمان پاسخ: {message.metadata.response_time.toFixed(2)}s</p>
                        )}
                      </div>
                    )}

                    <p className="text-xs text-gray-500 mt-2">
                      {message.timestamp.toLocaleTimeString('fa-IR')}
                    </p>
                  </div>
                </div>
              </div>
            )
            })
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area - Always at bottom */}
        <div className="bg-white border-t border-gray-200 p-2 md:p-4 z-20 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)] flex-shrink-0">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-2 md:gap-3 items-end">
              <Textarea
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder={
                  ragType === 'agentic'
                    ? 'سوال خود را بپرسید...'
                    : 'پیام خود را بنویسید...'
                }
                className="flex-1 min-h-[50px] md:min-h-[60px] max-h-[150px] md:max-h-[200px] resize-none border-2 border-gray-300 focus:border-purple-500 rounded-xl text-sm md:text-base"
                disabled={isLoading}
              />
              <Button
                onClick={sendMessage}
                disabled={!newMessage.trim() || isLoading}
                className={`h-[50px] md:h-[60px] px-4 md:px-6 rounded-xl shadow-md ${
                  ragType === 'agentic'
                    ? 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700'
                    : 'bg-blue-600 hover:bg-blue-700'
                } text-white disabled:opacity-50 flex-shrink-0`}
              >
                {isLoading ? (
                  <div className="animate-spin w-4 h-4 md:w-5 md:h-5 border-2 border-white border-t-transparent rounded-full" />
                ) : (
                  <Send className="w-4 h-4 md:w-5 md:h-5" />
                )}
              </Button>
            </div>
            <p className="text-xs text-gray-500 mt-2 text-center hidden md:block">
              Enter برای ارسال • Shift+Enter برای خط جدید
            </p>
          </div>
        </div>
      </div>

      {/* 🔥 Article Highlight Modal */}
      {highlightModal.isOpen && (
        <ArticleHighlightModal
          articleId={highlightModal.articleId}
          userQuery={highlightModal.userQuery}
          onClose={() => setHighlightModal({ isOpen: false, articleId: '', userQuery: '' })}
        />
      )}
    </div>
  )
}

export default CustomerChatPage

