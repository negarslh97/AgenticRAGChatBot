import { useState, useRef, useEffect, useCallback, useReducer } from 'react'
import { useAudio } from './useAudio'
import { chatService } from '../services/chatService'
import { User } from '../types/user'
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

// Streaming event types
interface StreamingEvent {
  type: 'init' | 'sources' | 'chunk' | 'complete' | 'error'
  conversation_id?: string
  sources?: Array<{ title: string; id: string }>
  confidence?: number
  content?: string
  message_id?: string
  complexity_fa?: string
  model?: string
  rag_type?: RAGType
  can_get_more_details?: boolean
  message?: string
}

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

// State interface for the reducer
interface ChatState {
  // Conversation management
  conversations: Conversation[]
  selectedConversation: Conversation | null
  conversationIdMap: Map<string, string> // tempId -> realId

  // Message input
  newMessage: string

  // Loading states
  isLoading: boolean
  isInitialLoading: boolean
  isThinking: boolean
  regeneratingMessageId: string | null

  // UI states
  searchQuery: string
  modelSearchQuery: string
  showSettingsModal: boolean
  showKeyboardShortcuts: boolean
  isSidebarOpen: boolean
  isSidebarCollapsed: boolean
  copiedMessageId: string | null
  deleteConfirmId: string | null
  showGoToBottomBtn: boolean

  // Settings
  ragType: AdminRAGType
  selectedModel: string
  availableModels: ModelInfo[]
  temperature: number

  // Article highlight modal
  highlightModal: {
    isOpen: boolean
    articleId: string
    userQuery: string
  }

  // Streaming state
  activeStreams: Map<string, {
    controller: AbortController
    tempMessageId: string
    conversationId?: string
  }>
}

// Action types for the reducer
type ChatAction =
  // Conversation management
  | { type: 'SET_CONVERSATIONS'; payload: Conversation[] }
  | { type: 'ADD_CONVERSATION'; payload: Conversation }
  | { type: 'UPDATE_CONVERSATION'; payload: { id: string; updates: Partial<Conversation> } }
  | { type: 'DELETE_CONVERSATION'; payload: string }
  | { type: 'SELECT_CONVERSATION'; payload: Conversation | null }
  | { type: 'SET_CONVERSATION_MESSAGES'; payload: { conversationId: string; messages: Message[] } }
  | { type: 'MAP_CONVERSATION_ID'; payload: { tempId: string; realId: string } }

  // Message input
  | { type: 'SET_NEW_MESSAGE'; payload: string }

  // Loading states
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_INITIAL_LOADING'; payload: boolean }
  | { type: 'SET_THINKING'; payload: boolean }
  | { type: 'SET_REGENERATING_MESSAGE'; payload: string | null }

  // UI states
  | { type: 'SET_SEARCH_QUERY'; payload: string }
  | { type: 'SET_MODEL_SEARCH_QUERY'; payload: string }
  | { type: 'SET_SHOW_SETTINGS_MODAL'; payload: boolean }
  | { type: 'SET_SHOW_KEYBOARD_SHORTCUTS'; payload: boolean }
  | { type: 'SET_SIDEBAR_OPEN'; payload: boolean }
  | { type: 'SET_SIDEBAR_COLLAPSED'; payload: boolean }
  | { type: 'SET_COPIED_MESSAGE'; payload: string | null }
  | { type: 'SET_DELETE_CONFIRM'; payload: string | null }
  | { type: 'SET_SHOW_GO_TO_BOTTOM'; payload: boolean }

  // Settings
  | { type: 'SET_RAG_TYPE'; payload: AdminRAGType }
  | { type: 'SET_SELECTED_MODEL'; payload: string }
  | { type: 'SET_AVAILABLE_MODELS'; payload: ModelInfo[] }
  | { type: 'SET_TEMPERATURE'; payload: number }

  // Article highlight modal
  | { type: 'SET_HIGHLIGHT_MODAL'; payload: { isOpen: boolean; articleId: string; userQuery: string } }

  // Streaming actions
  | { type: 'START_STREAMING'; payload: { streamId: string; controller: AbortController; tempMessageId: string; conversationId?: string } }
  | { type: 'END_STREAMING'; payload: string }
  | { type: 'STREAMING_EVENT'; payload: { streamId: string; event: StreamingEvent } }

interface UseSuperAdminChatProps {
  user: User | null
  FEATURE_FLAGS: {
    SHOW_SETTINGS: boolean
    SHOW_VOICE_INPUT: boolean
  }
  MODELS_CONFIG: {
    models: ModelInfo[]
    // Add other config properties as needed
  }
  getDefaultModel: (type: 'rag' | 'chat' | 'intent' | 'embedder') => string
  getModelById: (id: string) => ModelInfo | undefined
  toast: {
    error: (message: string) => void
    success: (message: string) => void
  }
  chatService: typeof chatService
}

// Reducer function
const chatReducer = (state: ChatState, action: ChatAction): ChatState => {
  switch (action.type) {
    case 'SET_CONVERSATIONS':
      return { ...state, conversations: action.payload }

    case 'ADD_CONVERSATION':
      return { ...state, conversations: [action.payload, ...state.conversations] }

    case 'UPDATE_CONVERSATION':
      return {
        ...state,
        conversations: state.conversations.map(conv =>
          conv.id === action.payload.id ? { ...conv, ...action.payload.updates } : conv
        ),
        selectedConversation: state.selectedConversation?.id === action.payload.id
          ? { ...state.selectedConversation, ...action.payload.updates }
          : state.selectedConversation
      }

    case 'DELETE_CONVERSATION':
      return {
        ...state,
        conversations: state.conversations.filter(conv => conv.id !== action.payload),
        selectedConversation: state.selectedConversation?.id === action.payload ? null : state.selectedConversation
      }

    case 'SELECT_CONVERSATION':
      return { ...state, selectedConversation: action.payload }

    case 'SET_CONVERSATION_MESSAGES':
      return {
        ...state,
        selectedConversation: state.selectedConversation?.id === action.payload.conversationId
          ? { ...state.selectedConversation, messages: action.payload.messages }
          : state.selectedConversation
      }

    case 'MAP_CONVERSATION_ID':
      const newMap = new Map(state.conversationIdMap)
      newMap.set(action.payload.tempId, action.payload.realId)
      return { ...state, conversationIdMap: newMap }

    case 'SET_NEW_MESSAGE':
      return { ...state, newMessage: action.payload }

    case 'SET_LOADING':
      return { ...state, isLoading: action.payload }

    case 'SET_INITIAL_LOADING':
      return { ...state, isInitialLoading: action.payload }

    case 'SET_THINKING':
      return { ...state, isThinking: action.payload }

    case 'SET_REGENERATING_MESSAGE':
      return { ...state, regeneratingMessageId: action.payload }

    case 'SET_SEARCH_QUERY':
      return { ...state, searchQuery: action.payload }

    case 'SET_MODEL_SEARCH_QUERY':
      return { ...state, modelSearchQuery: action.payload }

    case 'SET_SHOW_SETTINGS_MODAL':
      return { ...state, showSettingsModal: action.payload }

    case 'SET_SHOW_KEYBOARD_SHORTCUTS':
      return { ...state, showKeyboardShortcuts: action.payload }

    case 'SET_SIDEBAR_OPEN':
      return { ...state, isSidebarOpen: action.payload }

    case 'SET_SIDEBAR_COLLAPSED':
      return { ...state, isSidebarCollapsed: action.payload }

    case 'SET_COPIED_MESSAGE':
      return { ...state, copiedMessageId: action.payload }

    case 'SET_DELETE_CONFIRM':
      return { ...state, deleteConfirmId: action.payload }

    case 'SET_SHOW_GO_TO_BOTTOM':
      return { ...state, showGoToBottomBtn: action.payload }

    case 'SET_RAG_TYPE':
      return { ...state, ragType: action.payload }

    case 'SET_SELECTED_MODEL':
      return { ...state, selectedModel: action.payload }

    case 'SET_AVAILABLE_MODELS':
      return { ...state, availableModels: action.payload }

    case 'SET_TEMPERATURE':
      return { ...state, temperature: action.payload }

    case 'SET_HIGHLIGHT_MODAL':
      return { ...state, highlightModal: action.payload }

    case 'START_STREAMING':
      const newActiveStreams = new Map(state.activeStreams)
      newActiveStreams.set(action.payload.streamId, {
        controller: action.payload.controller,
        tempMessageId: action.payload.tempMessageId,
        conversationId: action.payload.conversationId
      })
      return { ...state, activeStreams: newActiveStreams }

    case 'END_STREAMING':
      const updatedActiveStreams = new Map(state.activeStreams)
      updatedActiveStreams.delete(action.payload)
      return { ...state, activeStreams: updatedActiveStreams }

    case 'STREAMING_EVENT':
      const streamInfo = state.activeStreams.get(action.payload.streamId)
      if (!streamInfo) return state

      const { event } = action.payload

      switch (event.type) {
        case 'init':
          if (event.conversation_id) {
            console.log('🎯 Init event - conversation_id:', event.conversation_id, 'streamInfo:', streamInfo)

            if (streamInfo.conversationId) {
              // Update existing conversation ID
              const updatedMap = new Map(state.conversationIdMap)
              updatedMap.set(streamInfo.conversationId, event.conversation_id)

              // Update conversations list
              const updatedConversations: Conversation[] = state.conversations.map(conv =>
                conv.id === streamInfo.conversationId ? { ...conv, id: event.conversation_id! } : conv
              )

              return {
                ...state,
                conversationIdMap: updatedMap,
                conversations: updatedConversations,
                selectedConversation: state.selectedConversation?.id === streamInfo.conversationId
                  ? { ...state.selectedConversation, id: event.conversation_id! }
                  : state.selectedConversation
              }
            } else {
              // This is a new conversation, update the selected conversation ID
              console.log('🎯 New conversation init - updating selectedConversation ID to:', event.conversation_id)
              const updatedConversations = state.conversations.map(conv =>
                conv.id.startsWith('new-') ? { ...conv, id: event.conversation_id! } : conv
              )

              return {
                ...state,
                conversations: updatedConversations,
                selectedConversation: state.selectedConversation ? {
                  ...state.selectedConversation,
                  id: event.conversation_id!
                } : state.selectedConversation
              }
            }
          }
          return state

        case 'sources':
          if (!state.selectedConversation) return state
          return {
            ...state,
            selectedConversation: {
              ...state.selectedConversation,
              messages: state.selectedConversation.messages.map(msg =>
                msg.id === streamInfo.tempMessageId
                  ? { ...msg, sources: event.sources, confidence: event.confidence }
                  : msg
              )
            }
          }

        case 'chunk':
          if (!state.selectedConversation) return { ...state, isThinking: true }

          console.log('🎯 Chunk event - content:', event.content, 'existing:', state.selectedConversation.messages.find(m => m.id === streamInfo.tempMessageId)?.content)

          const chunkMessage = state.selectedConversation.messages.find(m => m.id === streamInfo.tempMessageId)
          const existingContent = chunkMessage?.content || ''
          let chunkContent = event.content || ''

          // ✅ FIXED: LLM streaming tokens include proper spacing (e.g., " world" starts with space) - no strip() in backend
          return {
            ...state,
            isThinking: true,
            selectedConversation: {
              ...state.selectedConversation,
              messages: state.selectedConversation.messages.map(msg =>
                msg.id === streamInfo.tempMessageId
                  ? { ...msg, content: (msg.content || '') + chunkContent }
                  : msg
              )
            }
          }

        case 'complete':
          if (!state.selectedConversation) return state

          // Use content if available, otherwise use the accumulated content from chunks
          const existingMessage = state.selectedConversation.messages.find(m => m.id === streamInfo.tempMessageId)
          const finalContent = existingMessage?.content || event.content || ''

          console.log('🎯 Complete event - final content:', finalContent, 'existing content:', existingMessage?.content, 'event response:', event.content)
          console.log('🎯 Selected conversation messages:', state.selectedConversation.messages)

          const updatedState = {
            ...state,
            selectedConversation: {
              ...state.selectedConversation,
              messages: state.selectedConversation.messages.map(msg =>
                msg.id === streamInfo.tempMessageId
                  ? {
                      ...msg,
                      id: event.message_id || streamInfo.tempMessageId,
                      content: finalContent,
                      complexity_fa: event.complexity_fa,
                      model: event.model,
                      metadata: {
                        ...(msg.metadata || {}),
                        rag_type: event.rag_type,
                        can_get_more_details: event.can_get_more_details || false
                      }
                    }
                  : msg
              )
            },
            isLoading: false,
            regeneratingMessageId: null
          }

          console.log('🎯 Updated messages:', updatedState.selectedConversation.messages)
          console.log('🎯 Final state:', updatedState)
          return updatedState

        case 'error':
          if (!state.selectedConversation) return state
          return {
            ...state,
            selectedConversation: {
              ...state.selectedConversation,
              messages: state.selectedConversation.messages.map(msg =>
                msg.id === streamInfo.tempMessageId
                  ? { ...msg, is_failed: true, failure_reason: event.message }
                  : msg
              )
            },
            isLoading: false,
            regeneratingMessageId: null
          }

        default:
          return state
      }

    default:
      return state
  }
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

  // Initialize state with persisted values
  const initialState: ChatState = {
    conversations: [],
    selectedConversation: null,
    conversationIdMap: new Map(),
    newMessage: '',
    isLoading: false,
    isInitialLoading: true,
    isThinking: false,
    regeneratingMessageId: null,
    searchQuery: '',
    modelSearchQuery: '',
    showSettingsModal: false,
    showKeyboardShortcuts: false,
    isSidebarOpen: false,
    isSidebarCollapsed: false,
    copiedMessageId: null,
    deleteConfirmId: null,
    showGoToBottomBtn: false,
    ragType: (localStorage.getItem('superAdmin_ragType') as AdminRAGType) || 'simple',
    selectedModel: localStorage.getItem('superAdmin_selectedModel') || getDefaultModel('chat'),
    availableModels: [],
    temperature: localStorage.getItem('superAdmin_temperature') ? parseFloat(localStorage.getItem('superAdmin_temperature')!) : 0.7,
    highlightModal: { isOpen: false, articleId: '', userQuery: '' },
    activeStreams: new Map()
  }

  // Use reducer for state management
  const [state, dispatch] = useReducer(chatReducer, initialState)

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const initializationRef = useRef(false)
  const settingsModalRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const conversationIdRef = useRef<string | undefined>(undefined)
  const refreshInProgressRef = useRef<Set<string>>(new Set())
  const assistantTempIdRef = useRef<string>('')

  // Smart scroll state
  const userHasScrolledUp = useRef(false)
  const [showGoToBottomBtn, setShowGoToBottomBtn] = useState(false)

  // Save settings to localStorage
  useEffect(() => {
    localStorage.setItem('superAdmin_ragType', state.ragType)
  }, [state.ragType])

  useEffect(() => {
    localStorage.setItem('superAdmin_selectedModel', state.selectedModel)
  }, [state.selectedModel])

  useEffect(() => {
    localStorage.setItem('superAdmin_temperature', state.temperature.toString())
  }, [state.temperature])

  // Load conversations
  const loadConversations = useCallback(async () => {
    if (!user?.id || initializationRef.current) return

    try {
      dispatch({ type: 'SET_INITIAL_LOADING', payload: true })
      const data = await chatService.getConversations()

      const formattedConversations: Conversation[] = data.map((conv: any) => ({
        id: String(conv.id || `conv-${Date.now()}-${Math.random()}`),
        title: conv.title || 'گفتگوی جدید',
        messages: [],
        created_at: conv.created_at,
        updated_at: conv.updated_at,
        rag_type: (conv.type === 'Agentic' ? 'agentic' : 'simple') as AdminRAGType,
        model_name: conv.model_name,
        temperature: conv.temperature
      }))

      dispatch({ type: 'SET_CONVERSATIONS', payload: formattedConversations })
      initializationRef.current = true
    } catch (error: any) {
      console.error('Failed to load conversations:', error)
      if (process.env.NODE_ENV !== 'development') {
        toast.error('خطا در بارگذاری گفتگوها')
      }
    } finally {
      dispatch({ type: 'SET_INITIAL_LOADING', payload: false })
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

      dispatch({ type: 'SET_AVAILABLE_MODELS', payload: formattedModels })

      const defaultModel = modelData.default_model || getDefaultModel('chat')
      if (!formattedModels.find(m => m.id === state.selectedModel)) {
        dispatch({ type: 'SET_SELECTED_MODEL', payload: defaultModel })
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
      dispatch({ type: 'SET_AVAILABLE_MODELS', payload: configModels })

      const defaultModel = getDefaultModel('chat')
      if (!configModels.find(m => m.id === state.selectedModel)) {
        dispatch({ type: 'SET_SELECTED_MODEL', payload: defaultModel })
      }
    }
  }, [state.selectedModel, chatService, getModelById, getDefaultModel, MODELS_CONFIG])

  // Process streaming message with proper concurrency control
  const processStreamingMessage = useCallback(async (
    conversationId: string | undefined,
    messageContent: string,
    ragType: AdminRAGType,
    tempMessageId: string,
    conversationTempId?: string
  ) => {
    const streamId = `stream-${Date.now()}-${Math.random()}`

    dispatch({
      type: 'START_STREAMING',
      payload: {
        streamId,
        controller: new AbortController(), // Placeholder, actual controller is managed by service
        tempMessageId,
        conversationId: conversationTempId
      }
    })

    try {
      const result = await chatService.sendAdminMessageStream(
        conversationId,
        messageContent,
        ragType,
        (event: any) => {
          // Convert StreamEvent to StreamingEvent
          const streamingEvent: StreamingEvent = {
            type: event.type,
            conversation_id: event.conversation_id,
            sources: event.sources,
            confidence: event.confidence,
            content: event.response || event.content || event.data || '',
            message_id: event.message_id,
            complexity_fa: event.complexity,
            model: event.metadata?.model_name,
            rag_type: event.metadata?.rag_type,
            can_get_more_details: event.metadata?.can_get_more_details,
            message: event.message
          }
          console.log('🎯 Raw event:', JSON.stringify(event, null, 2))
          console.log('🎯 Content found:', streamingEvent.content)

          // Handle 'done' event as complete
          if (event.type === 'done') {
            streamingEvent.type = 'complete'
          }

          dispatch({ type: 'STREAMING_EVENT', payload: { streamId, event: streamingEvent } })
        },
        state.selectedModel,
        state.temperature
      )

      // Store the abort function for cleanup
      if (result && result.abort) {
        // Update the stream info with the abort function
        dispatch({
          type: 'START_STREAMING',
          payload: {
            streamId,
            controller: { abort: result.abort } as any, // Type assertion for simplicity
            tempMessageId,
            conversationId: conversationTempId
          }
        })
      }
    } catch (error: any) {
      console.error('Streaming error:', error)
      dispatch({ type: 'STREAMING_EVENT', payload: {
        streamId,
        event: { type: 'error', message: error.message || 'خطا در ارسال پیام' }
      } })
    } finally {
      dispatch({ type: 'END_STREAMING', payload: streamId })
    }
  }, [chatService, state.selectedModel, state.temperature])

  // Select conversation and load messages
  const handleSelectConversation = async (conversation: Conversation) => {
    if (state.selectedConversation?.id === conversation.id) return

    dispatch({ type: 'SELECT_CONVERSATION', payload: conversation })
    dispatch({ type: 'SET_LOADING', payload: true })

    try {
      const messages = await chatService.getConversationMessages(conversation.id)

      const formattedMessages: Message[] = messages.map((msg: any) => ({
        id: msg.id,
        content: msg.content,
        role: msg.sender_type === 'AI' ? 'assistant' : 'user',
        timestamp: new Date(msg.created_at),
        sender_type: msg.sender_type,
        is_failed: msg.is_failed,
        failure_reason: msg.failure_reason,
        rating: msg.rating,
        metadata: msg.metadata,
        // Map other fields if necessary, e.g. sources from metadata if available
        sources: msg.metadata?.sources,
        confidence: msg.metadata?.confidence,
        model: msg.metadata?.model_name
      }))

      dispatch({ type: 'SET_CONVERSATION_MESSAGES', payload: { conversationId: conversation.id, messages: formattedMessages } })
    } catch (error) {
      console.error('Failed to load messages:', error)
      toast.error('خطا در بارگذاری پیام‌ها')
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false })
    }
  }

  // Send message handler with proper state management
  const handleSendMessage = async () => {
    if (state.newMessage.trim() === '') return

    let currentConversation = state.selectedConversation
    if (!currentConversation) {
      const newConv: Conversation = {
        id: `new-${Date.now()}`,
        title: state.newMessage.trim().slice(0, 30) + (state.newMessage.trim().length > 30 ? '...' : ''),
        messages: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        tags: [],
        rag_type: state.ragType
      }
      dispatch({ type: 'ADD_CONVERSATION', payload: newConv })
      dispatch({ type: 'SELECT_CONVERSATION', payload: newConv })
      currentConversation = newConv
    }

    dispatch({ type: 'SET_LOADING', payload: true })
    dispatch({ type: 'SET_THINKING', payload: true })
    const messageContent = state.newMessage.trim()

    try {
      const userMessage: Message = {
        id: `temp-${Date.now()}`,
        content: messageContent,
        role: 'user',
        timestamp: new Date()
      }

      // Add user message and assistant placeholder
      const assistantTempId = `ai-temp-${Date.now()}`

      dispatch({ type: 'UPDATE_CONVERSATION', payload: {
        id: currentConversation.id,
        updates: {
          messages: [...currentConversation.messages, userMessage, {
            id: assistantTempId,
            content: '',
            role: 'assistant',
            timestamp: new Date(),
            metadata: { rag_type: state.ragType }
          } as Message],
          title: currentConversation.messages.length === 0
            ? messageContent.slice(0, 30) + (messageContent.length > 30 ? '...' : '')
            : currentConversation.title
        }
      } })

      dispatch({ type: 'SET_NEW_MESSAGE', payload: '' })

      const currentConvId = currentConversation.id.startsWith('new-') ? undefined : currentConversation.id

      await processStreamingMessage(
        currentConvId,
        messageContent,
        state.ragType,
        assistantTempId,
        currentConversation.id
      )

      // Handle conversation refresh after streaming completes
      const finalConvId = state.conversationIdMap.get(currentConversation.id) || currentConvId

      if (finalConvId && !refreshInProgressRef.current.has(finalConvId)) {
        refreshInProgressRef.current.add(finalConvId)

        setTimeout(async () => {
          try {
            const updatedConv = await chatService.getConversation(finalConvId)

            dispatch({ type: 'UPDATE_CONVERSATION', payload: {
              id: finalConvId,
              updates: {
                title: updatedConv.title,
                rag_type: updatedConv.rag_type,
                updated_at: updatedConv.updated_at
              }
            } })
          } catch (error) {
            console.error('❌ Failed to refresh conversation:', error)
          } finally {
            refreshInProgressRef.current.delete(finalConvId)
          }
        }, 500)
      }

    } catch (error: any) {
      console.error('Failed to send message (streaming):', error)
      toast.error('خطا در ارسال پیام')
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false })
      dispatch({ type: 'SET_THINKING', payload: false })
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
    if (state.deleteConfirmId !== convId) {
      dispatch({ type: 'SET_DELETE_CONFIRM', payload: convId })
      return
    }

    dispatch({ type: 'SET_DELETE_CONFIRM', payload: null })

    if (convId.startsWith('new-')) {
      dispatch({ type: 'DELETE_CONVERSATION', payload: convId })
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

      dispatch({ type: 'DELETE_CONVERSATION', payload: convId })
      toast.success('گفتگو حذف شد')
    } catch (error: any) {
      console.error('Failed to delete conversation:', error)
      toast.error('خطا در حذف گفتگو')
    }
  }

  // Utility functions
  const copyMessage = (messageId: string, content: string) => {
    navigator.clipboard.writeText(content)
    dispatch({ type: 'SET_COPIED_MESSAGE', payload: messageId })
    setTimeout(() => dispatch({ type: 'SET_COPIED_MESSAGE', payload: null }), 2000)
    toast.success('پیام کپی شد')
  }

  const retryMessage = async (messageId: string) => {
    // Implementation for retry message
    toast.success('در حال تلاش مجدد...')
  }

  const regenerateMessage = async (messageId: string) => {
    if (!state.selectedConversation) return

    const messageIndex = state.selectedConversation.messages.findIndex(m => m.id === messageId)
    if (messageIndex === -1) return

    // Find the preceding user message
    let userMessageContent = ''
    for (let i = messageIndex - 1; i >= 0; i--) {
      if (state.selectedConversation.messages[i].role === 'user') {
        userMessageContent = state.selectedConversation.messages[i].content
        break
      }
    }

    if (!userMessageContent) {
      toast.error('پیام کاربر یافت نشد')
      return
    }

    // Set regenerating state and clear message content
    dispatch({ type: 'SET_REGENERATING_MESSAGE', payload: messageId })
    dispatch({ type: 'SET_LOADING', payload: true })
    dispatch({ type: 'SET_THINKING', payload: true })

    dispatch({ type: 'UPDATE_CONVERSATION', payload: {
      id: state.selectedConversation.id,
      updates: {
        messages: state.selectedConversation.messages.map(m =>
          m.id === messageId
            ? { ...m, content: '', is_failed: false, failure_reason: undefined }
            : m
        )
      }
    } })

    try {
      await processStreamingMessage(
        state.selectedConversation.id,
        userMessageContent,
        state.ragType,
        messageId
      )
    } catch (error: any) {
      console.error('Failed to regenerate message:', error)
      toast.error('خطا در بازسازی پیام')
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false })
      dispatch({ type: 'SET_THINKING', payload: false })
      dispatch({ type: 'SET_REGENERATING_MESSAGE', payload: null })
    }
  }

  const createNewConversation = useCallback(() => {
    const newConv: Conversation = {
      id: `new-${Date.now()}`,
      title: 'گفتگوی جدید',
      messages: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      tags: [],
      rag_type: state.ragType
    }
    dispatch({ type: 'ADD_CONVERSATION', payload: newConv })
    dispatch({ type: 'SELECT_CONVERSATION', payload: newConv })
  }, [state.ragType])

  const toggleSidebar = useCallback(() => {
    dispatch({ type: 'SET_SIDEBAR_OPEN', payload: !state.isSidebarOpen })
  }, [state.isSidebarOpen])

  const toggleSidebarCollapse = () => {
    dispatch({ type: 'SET_SIDEBAR_COLLAPSED', payload: !state.isSidebarCollapsed })
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
  }, [messagesContainerRef])

  const handleGoToBottom = () => {
    userHasScrolledUp.current = false
    setShowGoToBottomBtn(false)
    scrollToBottom()
  }

  const handleSourceClick = (sourceId: string, messageId: string) => {
    console.log('Source clicked:', sourceId, messageId)

    if (!state.selectedConversation) return

    // Find the message to get context
    const messageIndex = state.selectedConversation.messages.findIndex(m => m.id === messageId)
    let userQuery = ''

    if (messageIndex !== -1) {
      // Search backwards for the last user message
      for (let i = messageIndex - 1; i >= 0; i--) {
        if (state.selectedConversation.messages[i].role === 'user') {
          userQuery = state.selectedConversation.messages[i].content
          break
        }
      }
    }

    dispatch({ type: 'SET_HIGHLIGHT_MODAL', payload: {
      isOpen: true,
      articleId: sourceId,
      userQuery: userQuery
    } })
  }

  const closeHighlightModal = () => {
    dispatch({ type: 'SET_HIGHLIGHT_MODAL', payload: {
      ...state.highlightModal,
      isOpen: false
    } })
  }


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

  // Cleanup streaming connections
  useEffect(() => {
    return () => {
      // Cancel all active streams when component unmounts
      state.activeStreams.forEach((streamInfo) => {
        streamInfo.controller.abort()
      })
    }
  }, [state.activeStreams])

  // Setter functions for external use
  const setNewMessage = (message: string | ((prev: string) => string)) => {
    if (typeof message === 'function') {
      dispatch({ type: 'SET_NEW_MESSAGE', payload: message(state.newMessage) })
    } else {
      dispatch({ type: 'SET_NEW_MESSAGE', payload: message })
    }
  }
  const setSearchQuery = (query: string) => dispatch({ type: 'SET_SEARCH_QUERY', payload: query })
  const setSelectedConversation = (conversation: Conversation | null) => dispatch({ type: 'SELECT_CONVERSATION', payload: conversation })
  const setDeleteConfirmId = (id: string | null) => dispatch({ type: 'SET_DELETE_CONFIRM', payload: id })
  const setShowSettingsModal = (show: boolean) => dispatch({ type: 'SET_SHOW_SETTINGS_MODAL', payload: show })
  const setIsSidebarOpen = (open: boolean) => dispatch({ type: 'SET_SIDEBAR_OPEN', payload: open })
  const setSelectedModel = (model: string) => dispatch({ type: 'SET_SELECTED_MODEL', payload: model })
  const setTemperature = (temp: number) => dispatch({ type: 'SET_TEMPERATURE', payload: temp })
  const setRagType = (type: AdminRAGType) => dispatch({ type: 'SET_RAG_TYPE', payload: type })

  console.log('🎯 Hook return - selectedConversation:', state.selectedConversation)

  return {
    // State
    conversations: state.conversations,
    selectedConversation: state.selectedConversation,
    newMessage: state.newMessage,
    isLoading: state.isLoading,
    isInitialLoading: state.isInitialLoading,
    searchQuery: state.searchQuery,
    modelSearchQuery: state.modelSearchQuery,
    ragType: state.ragType,
    showSettingsModal: state.showSettingsModal,
    selectedModel: state.selectedModel,
    availableModels: state.availableModels,
    temperature: state.temperature,
    isThinking: state.isThinking,
    copiedMessageId: state.copiedMessageId,
    deleteConfirmId: state.deleteConfirmId,
    showKeyboardShortcuts: state.showKeyboardShortcuts,
    regeneratingMessageId: state.regeneratingMessageId,
    isSidebarOpen: state.isSidebarOpen,
    isSidebarCollapsed: state.isSidebarCollapsed,
    messagesEndRef,
    messagesContainerRef,
    textareaRef,
    highlightModal: state.highlightModal,
    closeHighlightModal,
    showGoToBottomBtn: state.showGoToBottomBtn,
    userHasScrolledUp,

    // Actions
    handleSendMessage,
    handleSelectConversation,
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
    setNewMessage,
    setSearchQuery,
    setSelectedConversation,
    setDeleteConfirmId,
    setShowSettingsModal,
    setIsSidebarOpen,
    setSelectedModel,
    setTemperature,
    setRagType
  }
}