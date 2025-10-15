'use client'

/**
 * ChatPage - Dynamic Chat Interface
 *
 * Features:
 * - Dynamic conversation history (saved to database)
 * - New chat on every page load
 * - Search functionality in conversations
 * - Edit conversation titles
 * - Delete conversations
 * - Responsive design
 *
 * Current Status:
 * - ✅ Connected to real database API
 * - ✅ Loads conversations by user ID
 * - ✅ Saves messages to database
 * - ✅ Real-time conversation updates
 *
 * API Integration:
 * - Uses chatService for API calls
 * - Authenticates requests with user token
 * - Handles API errors gracefully
 */

import React, { useState, useRef, useEffect, KeyboardEvent, useCallback } from 'react'
import {
  Plus,
  Send,
  Bot,
  User,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Lightbulb,
  HelpCircle,
  Trash2,
  Search
} from 'lucide-react'
import { Button } from '../components/ui/button'
import { Textarea } from '../components/ui/textarea'
import { MarkdownRenderer } from '../components/ui/markdown-renderer'
import { VoiceInput } from '../components/ui/voice-input'
import { chatService } from '../services/chatService'
import { useAuth } from '../context/AuthContext'
import { toast } from 'react-hot-toast'

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
  sender_type?: 'Customer' | 'Admin' | 'SuperAdmin' | 'Guest' | 'customer' | 'admin' | 'super_admin' | 'guest' | 'ai'
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
    rag_type?: 'simple' | 'detailed'
    can_get_more_details?: boolean
    sources?: Array<{
      id: string
      title: string
      score: number
      category?: string
      tags?: string[]
    }>
    suggested_actions?: string[]
    token_usage?: {
      prompt_tokens?: number
      completion_tokens?: number
      total_tokens?: number
    }
  }
  sources?: Array<{ title: string; id: string }>
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

const ChatPage = () => {
    const { user } = useAuth()
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)
    const [conversations, setConversations] = useState<Conversation[]>([])
    const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)
    const [newMessage, setNewMessage] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [isInitialLoading, setIsInitialLoading] = useState(true)
    const [editingTitle, setEditingTitle] = useState<string | null>(null)
    const [newTitle, setNewTitle] = useState('')
    const [searchQuery, setSearchQuery] = useState('')
    const [guestSessionId, setGuestSessionId] = useState<string | null>(null)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const initializationRef = useRef(false)

    // Development mode: API might not be available
    const isDevelopment = process.env.NODE_ENV === 'development'

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

            // Load conversations from database for the authenticated user or guest
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
                console.log('📋 Conversation IDs:', formattedConversations.map(c => c.id))
                setConversations(formattedConversations)
            } else {
                console.warn('⚠️ API returned unexpected format for conversations:', response)
                console.warn('Expected: Array, Got:', typeof response)
                setConversations([])
            }

        } catch (error: any) {
            console.error('❌ Error loading conversations:', error)
            console.error('Error details:', {
                message: error.message,
                status: error.response?.status,
                statusText: error.response?.statusText,
                data: error.response?.data,
                stack: error.stack
            })

            // For guests, if API fails, we can still create new conversations
            if (!user) {
                console.warn('🔄 Guest user - using empty conversations list')
                setConversations([])
            } else {
                // Fallback: continue with empty conversations list
                console.warn('🔄 Using empty conversations list due to API error')
                setConversations([])
            }
        }
    }, [user])

    // Load messages for a specific conversation
    const loadConversationMessages = useCallback(async (conversationId: string) => {
        try {
            console.log('📨 Loading messages for conversation:', conversationId)
            console.log('👤 Guest session ID:', guestSessionId)

            // Load messages from database for this conversation
            const messages = await chatService.getConversationMessages(conversationId, guestSessionId || undefined)
            if (messages && Array.isArray(messages)) {
                const formattedMessages: Message[] = messages.map(msg => ({
                    id: msg.id,
                    content: msg.content,
                    role: msg.sender_type === 'ai' ? 'assistant' : 'user',
                    timestamp: new Date(msg.created_at),
                    sources: msg.metadata?.sources,
                    confidence: msg.metadata?.confidence,
                    suggested_actions: msg.metadata?.suggested_actions,
                    sender_type: msg.sender_type,
                    is_failed: msg.is_failed,
                    failure_reason: msg.failure_reason,
                    rating: msg.rating,
                    metadata: msg.metadata
                }))
                console.log('✅ Loaded messages from database:', formattedMessages.length, 'messages')
                return formattedMessages
            } else {
                console.warn('⚠️ API returned unexpected format for messages:', messages)
                return []
            }

        } catch (error) {
            console.error('Error loading messages:', error)
            console.warn('Using empty messages list due to API error')
            return []
        }
    }, [guestSessionId])

    // Initialize - load conversations and create new chat
    useEffect(() => {
        // Prevent duplicate initialization (React strict mode runs effects twice)
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
                // Initialize guest session for non-authenticated users
                initializeGuestSession()

                await loadConversations()
                setIsInitialLoading(false)

                // Only create new conversation if we don't already have one
                setConversations(prev => {
                    const firstConversation = prev[0]
                    if (!firstConversation || !firstConversation.id.startsWith('new-')) {
                        // Create a truly unique ID
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
                        // Already have a new conversation, just select it
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
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []) // Empty dependency array to run only once

    useEffect(() => {
        if (selectedConversation?.messages) {
            scrollToBottom()
        }
    }, [selectedConversation?.messages])

    // Reload conversations when user authentication status changes
    useEffect(() => {
        if (initializationRef.current) {
            console.log('🔄 User authentication changed, reloading conversations...')
            loadConversations()
        }
    }, [user?.id, loadConversations])

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

                // Update the conversation in the list
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
                messages: [...tempConversation.messages.slice(0, -1), userMessage, aiMessage] // Replace temp message
            }

            setSelectedConversation(finalConversation)

            // Update conversation in the list
            setConversations(prev =>
                prev.map(conv => conv.id === selectedConversation.id || conv.id === conversationId ? finalConversation : conv)
            )

            // Update conversation title if it was auto-generated
            if (selectedConversation.messages.length === 0 && response.conversation_id) {
                try {
                    await chatService.updateConversationTitle(response.conversation_id, finalConversation.title)
                } catch (error) {
                    console.warn('API not available for updating title:', error)
                    // Continue without updating title
                }
            }

        } catch (error) {
            console.error('Error sending message:', error)
            toast.error('خطا در ارسال پیام')

            // Keep the user message even if API fails - just add a fallback AI response
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

            // Update conversation in the list
            setConversations(prev =>
                prev.map(conv => conv.id === selectedConversation.id ? errorConversation : conv)
            )
        } finally {
            setIsLoading(false)
        }
    }

    const handleNewChat = () => {
        // Check if the currently selected conversation is already a new one
        if (selectedConversation?.id.startsWith('new-') && selectedConversation.messages.length === 0) {
            // Already have an empty new conversation selected, do nothing
            return
        }

        // Create new conversation and select it
        const uniqueId = `new-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
        const newConversation: Conversation = {
            id: uniqueId,
            title: 'گفتگوی جدید',
            messages: []
        }

        console.log('🆕 Creating new conversation:', uniqueId)
        setConversations(prev => {
            // Double check for uniqueness
            const existingIds = prev.map(c => c.id)
            if (existingIds.includes(uniqueId)) {
                console.warn('⚠️ Duplicate conversation ID detected:', uniqueId)
                return prev
            }
            return [newConversation, ...prev]
        })
        setSelectedConversation(newConversation)
    }

    // Handle selecting a conversation from the list
    const handleSelectConversation = async (conversation: Conversation) => {
        setSelectedConversation(conversation)

        // Load messages if not already loaded
        if (conversation.messages.length === 0 && !conversation.id.startsWith('new-')) {
            const messages = await loadConversationMessages(conversation.id)
            const updatedConversation = { ...conversation, messages }
            setSelectedConversation(updatedConversation)
            setConversations(prev =>
                prev.map(conv => conv.id === conversation.id ? updatedConversation : conv)
            )
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
            // Only update title via API if it's not a new conversation and user is authenticated
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

            setEditingTitle(null)
            setNewTitle('')
        } catch (error) {
            console.warn('API not available for updating title:', error)
            // Still update the UI even if API fails
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

            setEditingTitle(null)
            setNewTitle('')
        }

        // For guests, always update the UI locally
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

            setEditingTitle(null)
            setNewTitle('')
        }
    }

    const handleTitleCancel = () => {
        setEditingTitle(null)
        setNewTitle('')
    }

    // Filter conversations based on search query
    const filteredConversations = conversations.filter(conversation =>
        conversation.title.toLowerCase().includes(searchQuery.toLowerCase())
    )

    // Handle conversation deletion
    const handleDeleteConversation = async (conversationId: string) => {
        if (window.confirm('آیا مطمئن هستید که می‌خواهید این گفتگو را حذف کنید؟')) {
            try {
                // Note: API call for deletion can be added later
                // await chatService.deleteConversation(conversationId)

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

    const formatTime = (date: Date) => {
        return date.toLocaleTimeString('fa-IR', { 
            hour: '2-digit', 
            minute: '2-digit' 
        })
    }

    const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSendMessage()
        }
    }

    return (
        <div className="flex h-[calc(100vh-8rem)] w-full bg-gray-50">
        {/* // <div className="flex h-[calc(100vh-4rem)] w-full bg-gray-50"> */}
            {/* =============================================================== */}
            {/* Main Content Area (MUST BE THE FIRST ELEMENT FOR RTL FLEX) */}
            {/* =============================================================== */}
            <main
                className={`flex-1 flex flex-col transition-all duration-300${isSidebarOpen ? 'ml-80' : 'ml-0'}
                `}
            >
                {/* Header with the toggle button */}
                <header className="flex items-center justify-between p-4 bg-white shadow-sm">
                    <div className="flex items-center gap-3 mr-4">
                        <div className="relative">
                            <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center">
                                <Bot className="h-4 w-4 text-white" />
                            </div>
                            <div className="absolute -bottom-1 -right-1 h-3 w-3 bg-green-500 border-2 border-white rounded-full"></div>
                        </div>
                        <div>
                            <h1 className="font-semibold text-gray-900">سالی</h1>
                            <p className="text-xs text-gray-500">آنلاین</p>
                        </div>
                    </div>
                    <Button
                        onClick={toggleSidebar}
                        variant="ghost"
                        size="icon"
                        className=""
                    >
                        {isSidebarOpen ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
                    </Button>
                </header>

                {/* Chat messages area */}
                <div className="flex-1 p-4 overflow-y-auto">
                    {isInitialLoading ? (
                        <div className="flex items-center justify-center h-full">
                            <div className="text-center">
                                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                                <p className="text-gray-500">در حال بارگذاری...</p>
                            </div>
                        </div>
                    ) : selectedConversation && selectedConversation.messages.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full text-center space-y-6">
                            <div className="relative">
                                <div className="h-20 w-20 rounded-full bg-blue-600 flex items-center justify-center">
                                    <Sparkles className="h-10 w-10 text-white" />
                                </div>
                                <div className="absolute -bottom-2 -right-2 h-6 w-6 bg-green-500 border-2 border-white rounded-full flex items-center justify-center">
                                    <div className="h-2 w-2 bg-white rounded-full"></div>
                                </div>
                            </div>
                            <h2 className="text-2xl font-bold text-gray-900 text-right">به چت با سالی خوش آمدید!</h2>
                            <p className="text-gray-600 max-w-md text-right">
                                من Sally، دستیار هوش مصنوعی شما هستم. می‌توانم به سؤالات شما پاسخ دهم، اطلاعات ارائه کنم و در کارهای شما کمک کنم.
                            </p>
                            <div className="space-y-3 w-full max-w-md">
                                <div className="flex flex-col gap-2">
                                    <h3 className="text-sm font-medium text-gray-500 text-right">مثال‌های سؤال:</h3>
                                    <Button
                                        variant="outline"
                                        className="flex items-center justify-start text-right p-2"
                                        onClick={() => {
                                            setNewMessage('به من درباره شرکت صدگان بگو')
                                            setTimeout(() => handleSendMessage(), 100)
                                        }}
                                    >
                                        <HelpCircle className="h-4 w-4 ml-2 text-gray-500" />
                                        به من درباره شرکت صدگان بگو
                                    </Button>
                                    <Button
                                        variant="outline"
                                        className="flex items-center justify-start text-right p-2"
                                        onClick={() => {
                                            setNewMessage('محصولات شرکت صدگان چیست؟')
                                            setTimeout(() => handleSendMessage(), 100)
                                        }}
                                    >
                                        <Lightbulb className="h-4 w-4 ml-2 text-gray-500" />
                                        محصولات شرکت صدگان چیست؟
                                    </Button>
                                    <Button
                                        variant="outline"
                                        className="flex items-center justify-start text-right p-2"
                                        onClick={() => {
                                            setNewMessage('چطور می‌توانم محصول CRM این شرکت رو بخرم؟')
                                            setTimeout(() => handleSendMessage(), 100)
                                        }}
                                    >
                                        <Sparkles className="h-4 w-4 ml-2 text-gray-500" />
                                        چطور می‌توانم محصول CRM این شرکت رو بخرم؟
                                    </Button>
                                </div>
                            </div>
                        </div>
                    ) : selectedConversation ? (
                        <div className="space-y-4">
                            {selectedConversation.messages.length === 0 ? (
                                <div className="text-center text-gray-500 py-8">
                                    <p className="text-sm">این گفتگو هنوز پیامی ندارد</p>
                                    <p className="text-xs mt-1">پیام خود را در کادر پایین بنویسید</p>
                                </div>
                            ) : (
                                selectedConversation.messages.map((message) => (
                                    <div key={message.id} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                        {message.role === 'assistant' && (
                                            <div className="h-8 w-8 rounded-full bg-blue-600 flex-shrink-0 flex items-center justify-center">
                                                <Bot className="h-4 w-4 text-white" />
                                            </div>
                                        )}
                                        <div className={`max-w-[70%] ${message.role === 'user' ? 'order-2' : 'order-1'}`}>
                                            <div className={`p-4 rounded-lg shadow-sm ${message.role === 'user' ? 'bg-white text-slate-800' : 'bg-blue-600 text-white'}`}>
                                                {message.role === 'assistant' ? (
                                                    <MarkdownRenderer 
                                                        content={message.content}
                                                        variant="chat"
                                                        className="text-white"
                                                    />
                                                ) : (
                                                    <p className="text-right whitespace-pre-wrap">{message.content}</p>
                                                )}
                                                {message.sources && message.sources.length > 0 && (
                                                    <div className="mt-3 pt-3 border-t border-gray-200">
                                                        <p className="text-xs text-gray-500 mb-2">منابع:</p>
                                                        <div className="flex flex-wrap gap-1">
                                                            {message.sources.map((source, idx) => (
                                                                <span key={idx} className="inline-block bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded">
                                                                    {source.title}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                                {message.confidence && message.confidence < 0.8 && (
                                                    <div className="mt-2 text-xs text-yellow-600">
                                                        دقت پاسخ: {Math.round(message.confidence * 100)}%
                                                    </div>
                                                )}
                                                {message.suggested_actions && message.suggested_actions.length > 0 && (
                                                    <div className="mt-3 pt-3 border-t border-gray-200">
                                                        <p className="text-xs text-gray-500 mb-2">اقدامات پیشنهادی:</p>
                                                        <div className="flex flex-wrap gap-1">
                                                            {message.suggested_actions.map((action, idx) => (
                                                                <span key={idx} className="inline-block bg-green-100 text-green-700 text-xs px-2 py-1 rounded">
                                                                    {action}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                            <p className={`text-xs text-gray-500 mt-1 ${message.role === 'user' ? 'text-right' : 'text-left'}`}>
                                                {formatTime(message.timestamp)}
                                            </p>
                                        </div>
                                        {message.role === 'user' && (
                                            <div className="h-8 w-8 rounded-full bg-gray-300 flex-shrink-0 flex items-center justify-center">
                                                <User className="h-4 w-4 text-gray-600" />
                                            </div>
                                        )}
                                    </div>
                                ))
                            )}
                            <div ref={messagesEndRef} />
                        </div>
                    ) : (
                        <div className="flex items-center justify-center h-full">
                            <div className="text-center">
                                <p className="text-gray-500">گفتگویی انتخاب نشده</p>
                            </div>
                        </div>
                    )}
                </div>

                {/* Message input form */}
                <footer className="p-4 bg-white shadow-[0_-2px_4px_-2px_rgba(0,0,0,0.05)]">
                    <div className="flex gap-2 items-end">
                        <button
                            onClick={handleSendMessage}
                            disabled={!newMessage.trim() || isLoading}
                            className="whitespace-nowrap text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 text-white bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 h-10 w-10 md:h-12 md:w-12 rounded-xl flex items-center justify-center flex-shrink-0"
                        >
                            {isLoading ? (
                                <div className="animate-spin rounded-full h-4 w-4 md:h-5 md:w-5 border-2 border-white border-t-transparent"></div>
                            ) : (
                                <Send className="h-4 w-4 md:h-5 md:h-5" />
                            )}
                        </button>
                        <VoiceInput
                            onTranscriptionComplete={(text) => {
                                setNewMessage(prev => prev ? `${prev}\n${text}` : text)
                            }}
                            disabled={isLoading}
                        />
                        <Textarea
                            value={newMessage}
                            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setNewMessage(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="پیام خود را بنویسید..."
                            className="flex-1 resize-none text-right bg-white rounded-lg p-3 border-2 border-slate-200 focus-visible:border-blue-500 focus-visible:ring-0 focus-visible:outline-none transition-colors"
                            rows={1}
                        />
                    </div>
                </footer>
            </main>

            {/* =============================================================== */}
            {/* Sidebar (MUST BE THE SECOND ELEMENT FOR RTL FLEX) */}
            {/* =============================================================== */}
            <aside
                className={`flex flex-col bg-white shadow-lg transition-all duration-300 ${
                    isSidebarOpen ? 'w-80' : 'w-0'
                } overflow-hidden`}
            >
                <div className="p-4 bg-white shadow-sm">
                    <Button onClick={handleNewChat} className="w-full justify-end flex items-center gap-2 bg-blue-600 hover:bg-blue-700">
                        <Plus className="h-4 w-4" />
                        گفتگوی جدید
                    </Button>
                </div>
                {/* Search Bar */}
                <div className="p-2 border-b border-gray-200">
                    <div className="relative">
                        <Search className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                        <input
                            type="text"
                            placeholder="جستجو در گفتگوها..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pr-10 pl-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                    </div>
                </div>

                <div className="flex-1 overflow-auto">
                    <div className="p-2 space-y-2">
                        {filteredConversations.map((conversation) => (
                            <div
                                key={conversation.id}
                                className={`group cursor-pointer transition-colors p-3 rounded-lg ${
                                    selectedConversation?.id === conversation.id
                                        ? 'bg-slate-100'
                                        : 'hover:bg-slate-50'
                                }`}
                                onClick={() => handleSelectConversation(conversation)}
                            >
                                <div className="flex items-start gap-2">
                                    <div className="flex-1 min-w-0">
                                        {editingTitle === conversation.id ? (
                                            <div className="flex items-center gap-2">
                                                <input
                                                    type="text"
                                                    value={newTitle}
                                                    onChange={(e) => setNewTitle(e.target.value)}
                                                    onKeyPress={(e) => {
                                                        if (e.key === 'Enter') handleTitleSave(conversation.id)
                                                        if (e.key === 'Escape') handleTitleCancel()
                                                    }}
                                                    className="flex-1 text-sm border border-gray-300 rounded px-2 py-1 text-right"
                                                    autoFocus
                                                />
                                                <button
                                                    onClick={() => handleTitleSave(conversation.id)}
                                                    className="text-green-600 hover:text-green-800"
                                                >
                                                    ✓
                                                </button>
                                                <button
                                                    onClick={handleTitleCancel}
                                                    className="text-red-600 hover:text-red-800"
                                                >
                                                    ✕
                                                </button>
                                            </div>
                                        ) : (
                                            <h4
                                                className="font-medium text-gray-900 truncate text-right cursor-pointer hover:text-blue-600"
                                                onDoubleClick={() => handleTitleEdit(conversation.id, conversation.title)}
                                            >
                                                {conversation.title}
                                            </h4>
                                        )}
                                        <p className="text-xs text-gray-500 text-right">
                                            {conversation.messages.length > 0
                                                ? formatTime(conversation.messages[conversation.messages.length - 1].timestamp)
                                                : conversation.updated_at
                                                    ? formatTime(new Date(conversation.updated_at))
                                                    : 'بدون پیام'}
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        {conversation.messages.length > 0 && (
                                            <div className="flex-shrink-0">
                                                {conversation.messages[conversation.messages.length - 1].role === 'user' ? (
                                                    <User className="h-3 w-3 text-gray-500" />
                                                ) : (
                                                    <Bot className="h-3 w-3 text-gray-500" />
                                                )}
                                            </div>
                                        )}
                                        {!conversation.id.startsWith('new-') && (
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    handleDeleteConversation(conversation.id)
                                                }}
                                                className="opacity-0 group-hover:opacity-100 hover:text-red-600 transition-opacity p-1"
                                            >
                                                <Trash2 className="h-3 w-3" />
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                        {filteredConversations.length === 0 && conversations.length > 0 && (
                            <div className="p-4 text-center text-gray-500">
                                <p className="text-sm">گفتگویی با این عنوان یافت نشد</p>
                            </div>
                        )}
                        {conversations.length === 0 && !isInitialLoading && (
                            <div className="p-4 text-center text-gray-500">
                                <p className="text-sm">هنوز گفتگویی ندارید</p>
                            </div>
                        )}
                    </div>
                </div>
            </aside>
        </div>
    )
}

export default ChatPage
