import { useState, useRef, useEffect, useCallback } from 'react'
import { toast } from 'react-hot-toast'
import { chatService } from '../services/chatService'

export interface Source {
  id: string
  title: string
  score?: number
  snippet?: string
  category?: string
  tags?: string[]
}

export interface Message {
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

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  created_at?: string
  updated_at?: string
}

export const useChat = (initialRagType: string = 'agentic', initialUseStreaming: boolean = true) => {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)
  const [newMessage, setNewMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isInitialLoading, setIsInitialLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [guestSessionId, setGuestSessionId] = useState<string | null>(null)
  const ragType = initialRagType
  const useStreaming = initialUseStreaming
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Initialize guest session if user is not authenticated
  const initializeGuestSession = useCallback(() => {
    if (!guestSessionId) {
      const sessionId = localStorage.getItem('guest_session_id') || `guest_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      localStorage.setItem('guest_session_id', sessionId)
      setGuestSessionId(sessionId)
      console.log('👤 Guest session initialized:', sessionId)
    }
  }, [guestSessionId])

  // Auto-scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  // Load conversations from API
  const loadConversations = useCallback(async (chatService: any, user: any) => {
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
  }, [])

  // Load messages for a conversation
  const loadMessages = useCallback(async (chatService: any, conversationId: string, guestSessionId: string | null) => {
    try {
      console.log('📥 Loading messages for conversation:', conversationId)
      const response = await chatService.getConversationMessages(conversationId, guestSessionId ?? undefined)

      if (response && Array.isArray(response)) {
        const formattedMessages: Message[] = response.map((msg: any) => ({
          id: msg.id,
          content: msg.content,
          role: msg.sender_type === 'AI' || msg.sender_type === 'AI' ? 'assistant' : 'user',
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
  }, [scrollToBottom])

  // Create new conversation
  const createNewConversation = useCallback(() => {
    const newConv: Conversation = {
      id: `temp_${Date.now()}`,
      title: 'گفتگوی جدید',
      messages: []
    }
    setConversations(prev => [newConv, ...prev])
    setSelectedConversation(newConv)
    setNewMessage('')
  }, [])

  // Delete conversation
  const deleteConversation = useCallback(async (chatService: any, conversationId: string) => {
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
  }, [selectedConversation])

  // Filter conversations
  const filteredConversations = conversations.filter(conv =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return {
    conversations,
    selectedConversation,
    setConversations,
    setSelectedConversation,
    newMessage,
    setNewMessage,
    isLoading,
    setIsLoading,
    isInitialLoading,
    searchQuery,
    setSearchQuery,
    guestSessionId,
    setGuestSessionId,
    ragType,
    useStreaming,
    messagesEndRef,
    initializeGuestSession,
    loadConversations,
    loadMessages,
    createNewConversation,
    deleteConversation,
    filteredConversations,
    scrollToBottom
  }
}