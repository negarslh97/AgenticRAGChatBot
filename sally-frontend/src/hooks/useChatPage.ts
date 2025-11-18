import { useState, useRef, useEffect, useCallback } from 'react'
import { chatService } from '../services/chatService'
import { useAuth } from '../context/AuthContext'
import { toast } from 'react-hot-toast'
import type { Conversation, Message, ChatState, ChatActions } from '../types/chat'

interface UseChatPageProps {
  isDevelopment?: boolean
}

export const useChatPage = ({ isDevelopment = false }: UseChatPageProps = {}): ChatState & ChatActions => {
  const { user } = useAuth()
  
  // State management
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)
  const [newMessage, setNewMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isInitialLoading, setIsInitialLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [editingTitle, setEditingTitle] = useState<string | null>(null)
  const [newTitle, setNewTitle] = useState('')
  const [guestSessionId, setGuestSessionId] = useState<string | null>(null)
  
  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const initializationRef = useRef(false)

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
      const response = await chatService.getConversations()
      console.log('📥 Raw API response:', response)

      if (response && Array.isArray(response)) {
        const formattedConversations: Conversation[] = response.map(conv => ({
          id: conv.id,
          title: conv.title,
          messages: [],
          created_at: conv.created_at,
          updated_at: conv.updated_at
        }))
        console.log('✅ Loaded conversations from database:', formattedConversations.length, 'conversations')
        setConversations(formattedConversations)
      } else {
        console.warn('⚠️ API returned unexpected format for conversations:', response)
        setConversations([])
      }
    } catch (error: any) {
      console.error('❌ Error loading conversations:', error)
      if (!user) {
        console.warn('🔄 Guest user - using empty conversations list')
        setConversations([])
      } else {
        console.warn('🔄 Using empty conversations list due to API error')
        setConversations([])
      }
    }
  }, [user])

  // Load messages for a specific conversation
  const loadConversationMessages = useCallback(async (conversationId: string): Promise<Message[]> => {
    try {
      console.log('📨 Loading messages for conversation:', conversationId)
      console.log('🔑 Guest session ID:', guestSessionId)
      const messages = await chatService.getConversationMessages(conversationId, guestSessionId || undefined)
      console.log('📦 Raw API response for messages:', messages)
      if (messages && Array.isArray(messages)) {
        const formattedMessages: Message[] = messages.map(msg => ({
          id: msg.id,
          content: msg.content,
          role: msg.sender_type === 'AI' ? 'assistant' : 'user',
          timestamp: new Date(msg.created_at),
          sources: msg.metadata?.sources,
          confidence: msg.metadata?.confidence,
          suggested_actions: msg.metadata?.suggested_actions,
          sender_type: msg.sender_type === 'AI' ? 'ai' : msg.sender_type,
          is_failed: msg.is_failed,
          failure_reason: msg.failure_reason,
          rating: msg.rating,
          metadata: msg.metadata
        }))
        console.log('✅ Loaded messages from database:', formattedMessages.length, 'messages')
        console.log('📝 Formatted messages:', formattedMessages)
        return formattedMessages
      } else {
        console.warn('⚠️ API returned unexpected format for messages:', messages)
        return []
      }
    } catch (error) {
      console.error('❌ Error loading messages:', error)
      console.warn('Using empty messages list due to API error')
      return []
    }
  }, [guestSessionId])

  // Send message handler
  const handleSendMessage = async () => {
    if (newMessage.trim() === '' || !selectedConversation) return

    setIsLoading(true)
    const messageContent = newMessage.trim()

    try {
      // Add user message to UI immediately
      const userMessage: Message = {
        id: `temp-${Date.now()}`,
        content: messageContent,
        role: 'user',
        timestamp: new Date()
      }

      const tempConversation = {
        ...selectedConversation,
        messages: [...selectedConversation.messages, userMessage],
        title: selectedConversation.messages.length === 0
          ? messageContent.slice(0, 30) + (messageContent.length > 30 ? '...' : '')
          : selectedConversation.title
      }

      setSelectedConversation(tempConversation)
      setNewMessage('')

      // Send message to API
      const response = await chatService.sendMessage({
        content: messageContent,
        conversation_id: selectedConversation.id.startsWith('new-') ? undefined : selectedConversation.id,
        guest_session_id: guestSessionId || undefined
      })

      // Update conversation ID if it was a new conversation
      let conversationId = selectedConversation.id
      if (selectedConversation.id.startsWith('new-')) {
        conversationId = response.conversation_id
        setConversations(prev =>
          prev.map(conv =>
            conv.id === selectedConversation.id
              ? { ...tempConversation, id: conversationId }
              : conv
          )
        )
      }

      // Add AI response to conversation
      const aiMessage: Message = {
        id: response.message_id,
        content: response.message,
        role: 'assistant',
        timestamp: new Date(),
        sources: response.sources,
        confidence: response.confidence,
        suggested_actions: response.suggested_actions
      }

      const finalConversation = {
        ...tempConversation,
        id: conversationId,
        messages: [...tempConversation.messages.slice(0, -1), userMessage, aiMessage]
      }

      setSelectedConversation(finalConversation)
      setConversations(prev =>
        prev.map(conv => conv.id === selectedConversation.id || conv.id === conversationId ? finalConversation : conv)
      )

      // Update conversation title if it was auto-generated
      if (selectedConversation.messages.length === 0 && response.conversation_id) {
        try {
          await chatService.updateConversationTitle(response.conversation_id, finalConversation.title)
        } catch (error) {
          console.warn('API not available for updating title:', error)
        }
      }
    } catch (error) {
      console.error('Error sending message:', error)
      toast.error('خطا در ارسال پیام')

      // Keep the user message even if API fails
      const fallbackAiMessage: Message = {
        id: `fallback-${Date.now()}`,
        content: 'متأسفانه در حال حاضر به سرویس پاسخگویی دسترسی ندارم. لطفاً دوباره تلاش کنید.',
        role: 'assistant',
        timestamp: new Date()
      }

      const errorConversation = {
        ...selectedConversation,
        messages: [...selectedConversation.messages, fallbackAiMessage]
      }

      setSelectedConversation(errorConversation)
      setConversations(prev =>
        prev.map(conv => conv.id === selectedConversation.id ? errorConversation : conv)
      )
    } finally {
      setIsLoading(false)
    }
  }

  // Handle new chat
  const handleNewChat = () => {
    if (selectedConversation?.id.startsWith('new-') && selectedConversation.messages.length === 0) {
      return
    }

    const uniqueId = `new-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    const newConversation: Conversation = {
      id: uniqueId,
      title: 'گفتگوی جدید',
      messages: []
    }

    console.log('🆕 Creating new conversation:', uniqueId)
    setConversations(prev => {
      const existingIds = prev.map(c => c.id)
      if (existingIds.includes(uniqueId)) {
        console.warn('⚠️ Duplicate conversation ID detected:', uniqueId)
        return prev
      }
      return [newConversation, ...prev]
    })
    setSelectedConversation(newConversation)
  }

  // Handle selecting a conversation
  const handleSelectConversation = async (conversation: Conversation) => {
    console.log('🔄 Selecting conversation:', conversation.id, conversation.title)
    setSelectedConversation(conversation)

    // Always load messages for existing conversations (not new conversations)
    if (!conversation.id.startsWith('new-')) {
      console.log('📨 Loading messages for conversation:', conversation.id)
      const messages = await loadConversationMessages(conversation.id)
      console.log('✅ Loaded messages:', messages.length, messages)
      const updatedConversation = { ...conversation, messages }
      setSelectedConversation(updatedConversation)
      setConversations(prev =>
        prev.map(conv => conv.id === conversation.id ? updatedConversation : conv)
      )
    } else {
      console.log('🆕 New conversation, no messages to load')
    }
  }

  // Handle title editing
  const handleTitleEdit = (conversationId: string, currentTitle: string) => {
    setEditingTitle(conversationId)
    setNewTitle(currentTitle)
  }

  const handleTitleSave = async (conversationId: string) => {
    if (!newTitle.trim()) return

    try {
      if (!conversationId.startsWith('new-') && user) {
        await chatService.updateConversationTitle(conversationId, newTitle.trim())
      }

      setConversations(prev =>
        prev.map(conv =>
          conv.id === conversationId
            ? { ...conv, title: newTitle.trim() }
            : conv
        )
      )

      if (selectedConversation?.id === conversationId) {
        setSelectedConversation(prev => prev ? { ...prev, title: newTitle.trim() } : null)
      }
    } catch (error) {
      console.warn('API not available for updating title:', error)
    }

    if (!user) {
      setConversations(prev =>
        prev.map(conv =>
          conv.id === conversationId
            ? { ...conv, title: newTitle.trim() }
            : conv
        )
      )

      if (selectedConversation?.id === conversationId) {
        setSelectedConversation(prev => prev ? { ...prev, title: newTitle.trim() } : null)
      }
    }

    setEditingTitle(null)
    setNewTitle('')
  }

  const handleTitleCancel = () => {
    setEditingTitle(null)
    setNewTitle('')
  }

  // Handle conversation deletion
  const handleDeleteConversation = async (conversationId: string) => {
    if (window.confirm('آیا مطمئن هستید که می‌خواهید این گفتگو را حذف کنید؟')) {
      try {
        setConversations(prev => prev.filter(conv => conv.id !== conversationId))
        if (selectedConversation?.id === conversationId) {
          setSelectedConversation(null)
        }
        toast.success('گفتگو حذف شد')
      } catch (error) {
        console.error('Error deleting conversation:', error)
        toast.error('خطا در حذف گفتگو')
      }
    }
  }

  // Utility functions
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('fa-IR', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  // Copy message to clipboard
  const copyMessage = useCallback(async (messageId: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content)
      toast.success('پیام کپی شد')
    } catch (error) {
      console.error('Error copying to clipboard:', error)
      // Fallback for older browsers
      const textArea = document.createElement('textarea')
      textArea.value = content
      document.body.appendChild(textArea)
      textArea.select()
      try {
        document.execCommand('copy')
        toast.success('پیام کپی شد')
      } catch (fallbackError) {
        console.error('Fallback copy failed:', fallbackError)
        toast.error('خطا در کپی کردن')
      }
      document.body.removeChild(textArea)
    }
  }, [])

  // Retry message (for failed messages)
  const retryMessage = useCallback((messageId: string) => {
    if (!selectedConversation) return
    
    const messageIndex = selectedConversation.messages.findIndex(msg => msg.id === messageId)
    if (messageIndex === -1) return
    
    const message = selectedConversation.messages[messageIndex]
    if (message.role !== 'user') return
    
    // Remove the failed message and resend
    const updatedMessages = selectedConversation.messages.slice(0, messageIndex)
    setSelectedConversation(prev => prev ? { ...prev, messages: updatedMessages } : null)
    
    // Set the message content and send
    setNewMessage(message.content)
    setTimeout(() => handleSendMessage(), 100)
  }, [selectedConversation, handleSendMessage])

  // Regenerate assistant response
  const regenerateMessage = useCallback(async (messageId: string) => {
    if (!selectedConversation) return
    
    const messageIndex = selectedConversation.messages.findIndex(msg => msg.id === messageId)
    if (messageIndex === -1) return
    
    const message = selectedConversation.messages[messageIndex]
    if (message.role !== 'assistant') return
    
    // Find the user message that prompted this response
    const userMessageIndex = messageIndex - 1
    if (userMessageIndex < 0) return
    
    const userMessage = selectedConversation.messages[userMessageIndex]
    if (userMessage.role !== 'user') return
    
    // Remove the assistant message and resend the user message
    const updatedMessages = selectedConversation.messages.slice(0, userMessageIndex + 1)
    setSelectedConversation(prev => prev ? { ...prev, messages: updatedMessages } : null)
    
    // Set the user message content and send
    setNewMessage(userMessage.content)
    setTimeout(() => handleSendMessage(), 100)
  }, [selectedConversation, handleSendMessage])

  // Initialize - load conversations and create new chat
  useEffect(() => {
    if (initializationRef.current) {
      console.log('🚫 ChatPage initialization already completed, skipping')
      return
    }

    console.log('🚀 ChatPage useEffect initialization starting')
    let isMounted = true
    initializationRef.current = true

    const initializeChat = async () => {
      if (isDevelopment) {
        console.log('🔧 ChatPage: Running in development mode - Connected to real database API')
      }

      if (isMounted) {
        initializeGuestSession()
        await loadConversations()
        setIsInitialLoading(false)

        setConversations(prev => {
          const firstConversation = prev[0]
          if (!firstConversation || !firstConversation.id.startsWith('new-')) {
            const uniqueId = `new-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
            console.log('🏗️ Initializing with new conversation:', uniqueId)
            const newConversation: Conversation = {
              id: uniqueId,
              title: 'گفتگوی جدید',
              messages: []
            }
            setSelectedConversation(newConversation)
            return [newConversation, ...prev]
          } else {
            console.log('🔄 Initializing with existing conversation:', firstConversation.id)
            setSelectedConversation(firstConversation)
            return prev
          }
        })
      }
    }

    initializeChat()

    return () => {
      console.log('🧹 ChatPage useEffect cleanup')
      isMounted = false
    }
  }, [])

  useEffect(() => {
    if (selectedConversation?.messages) {
      scrollToBottom()
    }
  }, [selectedConversation?.messages])

  useEffect(() => {
    if (initializationRef.current) {
      console.log('🔄 User authentication changed, reloading conversations...')
      loadConversations()
    }
  }, [user?.id, loadConversations])

  return {
    // State
    conversations,
    selectedConversation,
    newMessage,
    isLoading,
    isInitialLoading,
    searchQuery,
    editingTitle,
    newTitle,
    guestSessionId,
    
    // Actions
    handleSendMessage,
    handleNewChat,
    handleSelectConversation,
    handleTitleEdit,
    handleTitleSave,
    handleTitleCancel,
    handleDeleteConversation,
    handleKeyPress,
    setNewMessage,
    setSearchQuery,
    setEditingTitle,
    setNewTitle,
    loadConversations,
    loadConversationMessages,
    formatTime,
    scrollToBottom,
    
    // Message actions
    copyMessage,
    retryMessage,
    regenerateMessage
  }
}