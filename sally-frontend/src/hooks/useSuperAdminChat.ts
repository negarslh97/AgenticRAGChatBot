import { useState, useRef, useEffect, useCallback } from 'react'
import { useAudio } from './useAudio'
import { toast } from 'react-hot-toast'
import { chatService } from '../services/chatService'
import { useAuth } from '../context/AuthContext'
import { MODELS_CONFIG, getDefaultModel, getModelById } from '../config/models'
import ArticleHighlightModal from '../components/ArticleHighlightModal'
import BlackCatImage from '../assets/Black-Cat.png'
import meowSound from '../assets/meow.mp3'

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
    token_usage?: {
      prompt_tokens?: number
      completion_tokens?: number
      total_tokens?: number
    }
    rag_type?: 'simple' | 'agentic'
    complexity?: string
    complexity_fa?: string
    model?: string
    can_get_more_details?: boolean
  }
  sources?: Array<{ title: string; id: string }>
  confidence?: number
  suggested_actions?: string[]
  complexity_fa?: string
  model?: string
  ragType?: 'simple' | 'agentic'
}

interface Conversation {
  id: string
  title: string
  messages: Message[]
  created_at?: string
  updated_at?: string
  rag_type?: 'simple' | 'agentic'
  tags?: string[]
  model_name?: string
  temperature?: number
  type?: string
}

type RAGType = 'simple' | 'agentic'
type AdminRAGType = 'simple' | 'agentic'

interface ModelInfo {
  id: string
  name: string
  provider: string
  description: string
  detailed_description?: string
  category?: string
  speed?: string
  empty_chunks?: string
}

interface UseSuperAdminChatProps {
  user: any
  FEATURE_FLAGS: {
    SHOW_SETTINGS: boolean
    SHOW_VOICE_INPUT: boolean
  }
  MODELS_CONFIG: any
  getDefaultModel: (type: 'rag' | 'chat' | 'intent' | 'embedder') => string
  getModelById: (id: string) => any
  toast: any
  chatService: any
}

export const useSuperAdminChat = ({
  user,
  FEATURE_FLAGS,
  MODELS_CONFIG,
  getDefaultModel,
  getModelById,
  toast,
  chatService
}: UseSuperAdminChatProps) => {
  const { play } = useAudio(meowSound)

  // State management
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)
  const [newMessage, setNewMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isInitialLoading, setIsInitialLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [modelSearchQuery, setModelSearchQuery] = useState('')
  const [ragType, setRagType] = useState<AdminRAGType>(() => {
    const saved = localStorage.getItem('superAdmin_ragType')
    return (saved as AdminRAGType) || 'simple'
  })
  const [selectedArticle, setSelectedArticle] = useState<{id: string, title: string, content: string} | null>(null)
  const [showSettingsModal, setShowSettingsModal] = useState(false)
  const [selectedModel, setSelectedModel] = useState<string>(() => {
    const saved = localStorage.getItem('superAdmin_selectedModel')
    return saved || getDefaultModel('chat')
  })
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([])
  const [temperature, setTemperature] = useState<number>(() => {
    const saved = localStorage.getItem('superAdmin_temperature')
    return saved ? parseFloat(saved) : 0.7
  })
  const [isThinking, setIsThinking] = useState(false)
  const [typewriterMessages, setTypewriterMessages] = useState<{[key: string]: string}>({})
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const [showKeyboardShortcuts, setShowKeyboardShortcuts] = useState(false)
  const [regeneratingMessageId, setRegeneratingMessageId] = useState<string | null>(null)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  
  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const initializationRef = useRef(false)
  const settingsModalRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const conversationIdRef = useRef<string | undefined>(undefined)
  const refreshInProgressRef = useRef<Set<string>>(new Set())
  const assistantTempIdRef = useRef<string>('')
  const streamingTimeoutsRef = useRef<{[key: string]: NodeJS.Timeout}>({})

  // Smart scroll state
  const userHasScrolledUp = useRef(false)
  const [showGoToBottomBtn, setShowGoToBottomBtn] = useState(false)

  // Article Highlight Modal state
  const [highlightModal, setHighlightModal] = useState<{
    isOpen: boolean
    articleId: string
    userQuery: string
  }>({ isOpen: false, articleId: '', userQuery: '' })

  // Save settings to localStorage
  useEffect(() => {
    localStorage.setItem('superAdmin_ragType', ragType)
  }, [ragType])

  useEffect(() => {
    localStorage.setItem('superAdmin_selectedModel', selectedModel)
  }, [selectedModel])

  useEffect(() => {
    localStorage.setItem('superAdmin_temperature', temperature.toString())
  }, [temperature])

  // Load conversations
  const loadConversations = useCallback(async () => {
    if (!user?.id || initializationRef.current) return

    try {
      setIsInitialLoading(true)
      const data = await chatService.getConversations()
      
      const formattedConversations: Conversation[] = data.map((conv: any) => ({
        id: conv.id,
        title: conv.title || 'گفتگوی جدید',
        messages: [],
        created_at: conv.created_at,
        updated_at: conv.updated_at,
        rag_type: conv.type === 'Agentic' ? 'agentic' : 'simple',
        model_name: conv.model_name,
        temperature: conv.temperature
      }))

      setConversations(formattedConversations)
      initializationRef.current = true
    } catch (error: any) {
      console.error('Failed to load conversations:', error)
      if (process.env.NODE_ENV !== 'development') {
        toast.error('خطا در بارگذاری گفتگوها')
      }
    } finally {
      setIsInitialLoading(false)
    }
  }, [user?.id, chatService, toast])

  // Load available models
  const loadAvailableModels = useCallback(async () => {
    try {
      const modelData = await chatService.getAvailableModels()
      
      const formattedModels: ModelInfo[] = modelData.models.map((model: any) => {
        const configModel = getModelById(model.id)
        
        let provider = model.provider
        if (model.id.startsWith('ollama:')) {
          provider = 'Ollama'
        } else if (model.id.startsWith('google/') || model.id.includes('gemini')) {
          provider = 'OpenRouter'
        } else if (model.id.startsWith('deepseek/') || model.id.includes('deepseek')) {
          provider = 'OpenRouter'
        } else if (model.id.startsWith('x-ai/') || model.id.includes('grok')) {
          provider = 'OpenRouter'
        } else if (model.id.startsWith('qwen/') || model.id.includes('qwen')) {
          provider = 'OpenRouter'
        } else if (model.id.startsWith('minimax/') || model.id.includes('minimax')) {
          provider = 'OpenRouter'
        } else if (model.id.startsWith('gpt-') || model.id.includes('gpt')) {
          provider = 'OpenAI'
        }
        
        return {
          id: model.id,
          name: model.name,
          provider: provider,
          description: model.description,
          detailed_description: model.description,
          category: model.category,
          speed: model.speed || configModel?.speed,
          empty_chunks: model.empty_chunks || configModel?.empty_chunks
        }
      })
      
      setAvailableModels(formattedModels)
      
      const defaultModel = modelData.default_model || getDefaultModel('chat')
      if (!formattedModels.find(m => m.id === selectedModel)) {
        setSelectedModel(defaultModel)
      }
    } catch (error: any) {
      console.error('Failed to load models from API, using config fallback:', error)
      const configModels: ModelInfo[] = MODELS_CONFIG.models.map((model: any) => ({
        id: model.id,
        name: model.name,
        provider: model.provider,
        description: model.description,
        detailed_description: model.description,
        category: model.category,
        speed: model.speed,
        empty_chunks: model.empty_chunks
      }))
      setAvailableModels(configModels)
      
      const defaultModel = getDefaultModel('chat')
      if (!configModels.find(m => m.id === selectedModel)) {
        setSelectedModel(defaultModel)
      }
    }
  }, [selectedModel, chatService, getModelById, getDefaultModel, MODELS_CONFIG])

  // Send message handler
  const handleSendMessage = async () => {
    if (newMessage.trim() === '') return

    let currentConversation = selectedConversation
    if (!currentConversation) {
      const newConv: Conversation = {
        id: `new-${Date.now()}`,
        title: newMessage.trim().slice(0, 30) + (newMessage.trim().length > 30 ? '...' : ''),
        messages: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        tags: [],
        rag_type: ragType
      }
      setConversations(prev => [newConv, ...prev])
      setSelectedConversation(newConv)
      currentConversation = newConv
    }

    setIsLoading(true)
    setIsThinking(true)
    const messageContent = newMessage.trim()

    try {
      const userMessage: Message = {
        id: `temp-${Date.now()}`,
        content: messageContent,
        role: 'user',
        timestamp: new Date()
      }

      const tempConversation = {
        ...currentConversation,
        messages: [...currentConversation.messages, userMessage],
        title: currentConversation.messages.length === 0
          ? messageContent.slice(0, 30) + (messageContent.length > 30 ? '...' : '')
          : currentConversation.title,
        rag_type: ragType
      }

      setSelectedConversation(tempConversation)
      setNewMessage('')

      const assistantTempId = `ai-temp-${Date.now()}`
      assistantTempIdRef.current = assistantTempId

      const addAssistantPlaceholder = () => setSelectedConversation(prev => ({
        ...prev!,
        messages: [...(prev?.messages || []), {
          id: assistantTempId,
          content: '',
          role: 'assistant',
          timestamp: new Date(),
          metadata: { rag_type: ragType }
        } as Message]
      }))

      addAssistantPlaceholder()

      const currentConvId = currentConversation.id.startsWith('new-') ? undefined : currentConversation.id
      const currentConvTempId = currentConversation.id
      conversationIdRef.current = undefined
      
      setTypewriterMessages(prev => ({
        ...prev,
        [assistantTempId]: ''
      }))

      await chatService.sendAdminMessageStream(
        currentConvId,
        messageContent,
        ragType,
        (evt: any) => {
          if (!evt) return

          if (evt.type === 'init') {
            if (evt.conversation_id) {
              conversationIdRef.current = evt.conversation_id
              if (!currentConvId) {
                setConversations(prev =>
                  prev.map(conv =>
                    conv.id === currentConvTempId
                      ? { ...conv, id: evt.conversation_id }
                      : conv
                  )
                )
                setSelectedConversation(prev => prev ? ({ ...prev, id: evt.conversation_id }) : prev)
              }
            }
          }

          if (evt.type === 'sources') {
            console.log('📚 Admin sources:', evt.sources)
            setSelectedConversation(prev => {
              if (!prev) return prev
              const updated = { ...prev }
              updated.messages = updated.messages.map(m =>
                m.id === assistantTempId
                  ? { ...m, sources: evt.sources, confidence: evt.confidence }
                  : m
              )
              return updated
            })
          }

          if (evt.type === 'chunk') {
            setIsThinking(false)
            
            setSelectedConversation(prev => {
              if (!prev) return prev
              const updated = { ...prev }
              const currentMessage = updated.messages.find(m => m.id === assistantTempId)
              
              if (currentMessage) {
                const newContent = (currentMessage.content || '') + (evt.content || '')
                
                if (evt.content) {
                  streamContentGradually(assistantTempId, newContent)
                }
                
                updated.messages = updated.messages.map(m =>
                  m.id === assistantTempId
                    ? { ...m, content: newContent }
                    : m
                )
              }
              return updated
            })
            
            setTimeout(() => scrollToBottom(), 50)
          }

          if (evt.type === 'complete') {
            setSelectedConversation(prev => {
              if (!prev) return prev
              const updated = { ...prev }
              const finalContent = evt.full_response || updated.messages.find(m => m.id === assistantTempId)?.content || ''
              
              setTypewriterMessages(prev => {
                const currentContent = prev[assistantTempId] || ''
                if (currentContent.length < finalContent.length) {
                  return {
                    ...prev,
                    [assistantTempId]: finalContent
                  }
                }
                return prev
              })
              
              updated.messages = updated.messages.map(m =>
                m.id === assistantTempId
                  ? {
                      ...m,
                      id: evt.message_id || assistantTempId,
                      content: finalContent,
                      complexity_fa: evt.complexity_fa,
                      model: evt.model,
                      metadata: {
                        ...(m.metadata || {}),
                        rag_type: evt.rag_type,
                        can_get_more_details: evt.can_get_more_details || false
                      }
                    }
                  : m
              )
              return updated
            })
            setIsLoading(false)
            
            const finalConvId = evt.conversation_id || conversationIdRef.current || currentConvId
            
            if (finalConvId) {
              if (refreshInProgressRef.current.has(finalConvId)) {
                return
              }
              
              refreshInProgressRef.current.add(finalConvId)
              
              setTimeout(async () => {
                try {
                  const updatedConv = await chatService.getConversation(finalConvId)
                  
                  setConversations((prev: Conversation[]) => {
                    const exists = prev.some(c => c.id === finalConvId)
                    
                    if (exists) {
                      const updated = prev.map(c =>
                        c.id === finalConvId
                          ? {
                              ...c,
                              title: updatedConv.title || c.title,
                              rag_type: updatedConv.rag_type || evt.rag_type,
                              updated_at: updatedConv.updated_at
                            }
                          : c
                      )
                      return updated
                    } else {
                      return [...prev, {
                        id: finalConvId,
                        title: updatedConv.title || 'مکالمه جدید',
                        rag_type: evt.rag_type,
                        created_at: updatedConv.created_at,
                        updated_at: updatedConv.updated_at,
                        tags: updatedConv.tags || [],
                        messages: []
                      }]
                    }
                  })
                  
                  setSelectedConversation(prev => {
                    if (!prev) return prev
                    if (prev.id === finalConvId || prev.id === currentConvTempId) {
                      const updated = {
                        ...prev,
                        id: finalConvId,
                        title: updatedConv.title || prev.title,
                        rag_type: updatedConv.rag_type || evt.rag_type
                      }
                      return updated
                    }
                    return prev
                  })
                  
                  refreshInProgressRef.current.delete(finalConvId)
                } catch (error) {
                  console.error('❌ Failed to refresh conversation:', error)
                  refreshInProgressRef.current.delete(finalConvId)
                }
              }, 500)
            } else {
              console.warn('⚠️ No finalConvId available for refresh')
            }
          }

          if (evt.type === 'error') {
            toast.error(`خطا: ${evt.message}`)
            setSelectedConversation(prev => {
              if (!prev) return prev
              const updated = { ...prev }
              updated.messages = updated.messages.map(m =>
                m.id === assistantTempId
                  ? { ...m, is_failed: true, failure_reason: evt.message }
                  : m
              )
              return updated
            })
            setIsLoading(false)
          }
        },
        selectedModel,
        temperature
      )

    } catch (error: any) {
      console.error('Failed to send message (streaming):', error)
      toast.error('خطا در ارسال پیام')
    } finally {
      setIsLoading(false)
      setIsThinking(false)
    }
  }

  // Keyboard handler
  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  // Delete conversation
  const deleteConversation = async (convId: string) => {
    if (deleteConfirmId !== convId) {
      setDeleteConfirmId(convId)
      return
    }

    setDeleteConfirmId(null)

    if (convId.startsWith('new-')) {
      setConversations(prev => prev.filter(c => c.id !== convId))
      if (selectedConversation?.id === convId) {
        setSelectedConversation(null)
      }
      toast.success('گفتگو حذف شد')
      return
    }

    try {
      try {
        await chatService.deleteConversation(convId)
      } catch (apiError: any) {
        if (apiError.response?.status === 405) {
          console.warn('Delete conversation endpoint not available, deleting locally only')
        } else {
          throw apiError
        }
      }
      
      setConversations(prev => prev.filter(c => c.id !== convId))
      if (selectedConversation?.id === convId) {
        setSelectedConversation(null)
      }
      toast.success('گفتگو حذف شد')
    } catch (error: any) {
      console.error('Failed to delete conversation:', error)
      toast.error('خطا در حذف گفتگو')
    }
  }

  // Utility functions
  const copyMessage = (messageId: string, content: string) => {
    navigator.clipboard.writeText(content)
    setCopiedMessageId(messageId)
    setTimeout(() => setCopiedMessageId(null), 2000)
    toast.success('پیام کپی شد')
  }

  const retryMessage = async (messageId: string) => {
    // Implementation for retry message
    toast.success('در حال تلاش مجدد...')
  }

  const regenerateMessage = async (messageId: string) => {
    // Implementation for regenerate message
    toast.success('در حال بازسازی پیام...')
  }

  const createNewConversation = useCallback(() => {
    const newConv: Conversation = {
      id: `new-${Date.now()}`,
      title: 'گفتگوی جدید',
      messages: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      tags: [],
      rag_type: ragType
    }
    setConversations(prev => [newConv, ...prev])
    setSelectedConversation(newConv)
  }, [ragType])

  const toggleSidebar = useCallback(() => {
    setIsSidebarOpen(prev => !prev)
  }, [])

  const toggleSidebarCollapse = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed)
  }

  const scrollToBottom = useCallback(() => {
    if (!userHasScrolledUp.current && messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: messagesContainerRef.current.scrollHeight,
        behavior: 'smooth'
      })
    }
  }, [userHasScrolledUp, messagesContainerRef])

  const handleScroll = useCallback(() => {
    if (!messagesContainerRef.current) return

    const container = messagesContainerRef.current
    const isAtBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 10

    if (isAtBottom) {
      userHasScrolledUp.current = false
      setShowGoToBottomBtn(false)
    } else {
      userHasScrolledUp.current = true
      setShowGoToBottomBtn(true)
    }
  }, [])

  const handleGoToBottom = () => {
    userHasScrolledUp.current = false
    setShowGoToBottomBtn(false)
    scrollToBottom()
  }

  const handleSourceClick = (sourceId: string, messageId: string) => {
    // Implementation for source click
    console.log('Source clicked:', sourceId)
  }

  const streamContentGradually = useCallback((messageId: string, content: string, delay: number = 30) => {
    if (streamingTimeoutsRef.current[messageId]) {
      clearTimeout(streamingTimeoutsRef.current[messageId])
    }

    let currentIndex = 0
    const streamNext = () => {
      if (currentIndex < content.length) {
        setTypewriterMessages(prev => ({
          ...prev,
          [messageId]: content.substring(0, currentIndex + 1)
        }))
        currentIndex++
        
        const nextDelay = Math.random() * 20 + 20
        streamingTimeoutsRef.current[messageId] = setTimeout(streamNext, nextDelay)
      } else {
        delete streamingTimeoutsRef.current[messageId]
      }
    }
    
    streamNext()
  }, [])

  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat('fa-IR', {
      hour: '2-digit',
      minute: '2-digit'
    }).format(date)
  }

  const getRagTypeIcon = (type: RAGType) => {
    switch (type) {
      case 'simple':
        return 'BookOpen'
      case 'agentic':
        return 'Brain'
      default:
        return 'BookOpen'
    }
  }

  const getRagTypeLabel = (type: RAGType) => {
    switch (type) {
      case 'simple':
        return 'ساده'
      case 'agentic':
        return 'عامل'
      default:
        return type
    }
  }

  // Cleanup streaming timeouts
  useEffect(() => {
    return () => {
      Object.values(streamingTimeoutsRef.current).forEach(timeout => {
        clearTimeout(timeout)
      })
      streamingTimeoutsRef.current = {}
    }
  }, [])

  return {
    // State
    conversations,
    selectedConversation,
    newMessage,
    isLoading,
    isInitialLoading,
    searchQuery,
    modelSearchQuery,
    ragType,
    selectedArticle,
    showSettingsModal,
    selectedModel,
    availableModels,
    temperature,
    isThinking,
    typewriterMessages,
    copiedMessageId,
    deleteConfirmId,
    showKeyboardShortcuts,
    regeneratingMessageId,
    isSidebarOpen,
    isSidebarCollapsed,
    messagesEndRef,
    messagesContainerRef,
    textareaRef,
    highlightModal,
    showGoToBottomBtn,
    userHasScrolledUp,
    
    // Actions
    handleSendMessage,
    handleKeyPress,
    deleteConversation,
    copyMessage,
    retryMessage,
    regenerateMessage,
    createNewConversation,
    toggleSidebar,
    toggleSidebarCollapse,
    handleScroll,
    handleGoToBottom,
    loadConversations,
    loadAvailableModels,
    formatTime,
    getRagTypeIcon,
    getRagTypeLabel,
    handleSourceClick,
    streamContentGradually,
    setNewMessage,
    setSearchQuery,
    setSelectedConversation,
    setDeleteConfirmId,
    setShowSettingsModal,
    setSelectedArticle,
    setIsSidebarOpen,
    setSelectedModel,
    setTemperature,
    setRagType
  }
}