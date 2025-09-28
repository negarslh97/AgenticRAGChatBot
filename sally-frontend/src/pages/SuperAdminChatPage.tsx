'use client'

/**
 * SuperAdminChatPage - Admin Chat Interface with RAG Selection
 *
 * Features:
 * - RAG type selection (SimpleRAG vs AgenticRAG)
 * - Dynamic conversation history
 * - Admin-specific chat functionality
 * - Real-time conversation updates
 * - Testing interface for RAG services
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
  Search,
  Settings,
  Zap,
  Brain,
  X,
  ExternalLink
} from 'lucide-react'
import { Button } from '../components/ui/button'
import { Textarea } from '../components/ui/textarea'
import { chatService, Conversation as ApiConversation, ChatMessage } from '../services/chatService'
import { useAuth } from '../context/AuthContext'
import { toast } from 'react-hot-toast'

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
  sender_type?: 'Customer' | 'Admin' | 'SuperAdmin' | 'Guest' |'AI'
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
  rag_type?: 'simple' | 'agentic'
}

type RAGType = 'simple' | 'agentic'

const SuperAdminChatPage = () => {
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
    const [ragType, setRagType] = useState<RAGType>('simple')
    const [selectedArticle, setSelectedArticle] = useState<{id: string, title: string, content: string} | null>(null)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const initializationRef = useRef(false)

    // Development mode: API might not be available
    const isDevelopment = process.env.NODE_ENV === 'development'

    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [])

    useEffect(() => {
        scrollToBottom()
    }, [selectedConversation?.messages, scrollToBottom])

    // Load conversations on component mount
    const loadConversations = useCallback(async () => {
        if (!user?.id || initializationRef.current) return

        try {
            setIsInitialLoading(true)
            const data = await chatService.getConversations()
            
            // Convert API conversations to our format
            const formattedConversations: Conversation[] = data.map(conv => ({
                id: conv.id,
                title: conv.title || 'گفتگوی جدید',
                messages: [],
                created_at: conv.created_at,
                updated_at: conv.updated_at,
                rag_type: 'simple' // Default for existing conversations
            }))

            setConversations(formattedConversations)
            initializationRef.current = true
        } catch (error: any) {
            console.error('Failed to load conversations:', error)
            if (!isDevelopment) {
                toast.error('خطا در بارگذاری گفتگوها')
            }
        } finally {
            setIsInitialLoading(false)
        }
    }, [user?.id, isDevelopment])

    useEffect(() => {
        if (user?.id) {
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
                    : selectedConversation.title,
                rag_type: ragType
            }

            setSelectedConversation(tempConversation)
            setNewMessage('')

            // Send message to API with RAG type
            const response = await chatService.sendAdminMessage(
                messageContent,
                selectedConversation.id.startsWith('new-') ? undefined : selectedConversation.id,
                ragType
            )

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
                suggested_actions: response.suggested_actions,
                metadata: {
                    ...response.metadata,
                    rag_type: ragType
                }
            }

            // Update the conversation with the real messages
            const updatedConversation = {
                ...tempConversation,
                id: conversationId,
                messages: [...tempConversation.messages.slice(0, -1), userMessage, aiMessage]
            }

            setSelectedConversation(updatedConversation)

            // Update conversations list
            setConversations(prev =>
                prev.map(conv =>
                    conv.id === conversationId ? updatedConversation : conv
                )
            )

        } catch (error: any) {
            console.error('Failed to send message:', error)
            toast.error(error.response?.data?.detail || 'خطا در ارسال پیام')
            // Remove the temporary user message
            setSelectedConversation(prev => prev ? {
                ...prev,
                messages: prev.messages.slice(0, -1)
            } : null)
        } finally {
            setIsLoading(false)
        }
    }

    const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSendMessage()
        }
    }

    const createNewConversation = () => {
        const newConv: Conversation = {
            id: `new-${Date.now()}`,
            title: 'گفتگوی جدید',
            messages: [],
            rag_type: ragType
        }
        setConversations(prev => [newConv, ...prev])
        setSelectedConversation(newConv)
    }

    const deleteConversation = async (convId: string) => {
        if (convId.startsWith('new-')) {
            // Just remove from local state if it's a new conversation
            setConversations(prev => prev.filter(c => c.id !== convId))
            if (selectedConversation?.id === convId) {
                setSelectedConversation(null)
            }
            return
        }

        try {
            await chatService.deleteConversation(convId)
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

    const loadConversationMessages = async (conversationId: string) => {
        try {
            const messages = await chatService.getConversationMessages(conversationId)
            
            // Convert API messages to our format
            const formattedMessages: Message[] = messages.map(msg => ({
                id: msg.id,
                content: msg.content,
                role: msg.sender_type === 'ai' ? 'assistant' : 'user',
                timestamp: new Date(msg.created_at),
                sender_type: msg.sender_type as any,
                is_failed: msg.is_failed,
                failure_reason: msg.failure_reason,
                rating: msg.rating,
                metadata: msg.metadata,
                sources: msg.metadata?.sources || [],
                confidence: msg.metadata?.confidence,
                suggested_actions: msg.metadata?.suggested_actions || []
            }))

            // Update the selected conversation with messages
            setSelectedConversation(prev => prev ? {
                ...prev,
                messages: formattedMessages
            } : null)

            // Also update in conversations list
            setConversations(prev => 
                prev.map(conv => 
                    conv.id === conversationId 
                        ? { ...conv, messages: formattedMessages }
                        : conv
                )
            )
        } catch (error: any) {
            console.error('Failed to load conversation messages:', error)
            toast.error('خطا در بارگذاری پیام‌ها')
        }
    }

    const handleConversationClick = async (conversation: Conversation) => {
        setSelectedConversation(conversation)
        
        // Load messages if not already loaded
        if (conversation.messages.length === 0) {
            await loadConversationMessages(conversation.id)
        }
    }

    const handleSourceClick = async (sourceId: string, sourceTitle: string) => {
        try {
            // Call API to get article content
            const response = await fetch(`/api/super-admin/kb/articles/${sourceId}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            })
            
            if (response.ok) {
                const article = await response.json()
                setSelectedArticle({
                    id: sourceId,
                    title: sourceTitle,
                    content: article.content_html || article.content_markdown || 'محتوای مقاله در دسترس نیست'
                })
            } else {
                toast.error('خطا در بارگذاری مقاله')
            }
        } catch (error) {
            console.error('Error fetching article:', error)
            toast.error('خطا در بارگذاری مقاله')
        }
    }

    const formatTime = (date: Date) => {
        return date.toLocaleTimeString('fa-IR', {
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    const filteredConversations = conversations.filter(conv =>
        conv.title.toLowerCase().includes(searchQuery.toLowerCase())
    )

    const getRagTypeIcon = (type: RAGType) => {
        return type === 'simple' ? <Zap className="h-4 w-4" /> : <Brain className="h-4 w-4" />
    }

    const getRagTypeLabel = (type: RAGType) => {
        return type === 'simple' ? 'Simple RAG' : 'Agentic RAG'
    }

    const getRagTypeDescription = (type: RAGType) => {
        return type === 'simple' 
            ? 'پاسخ‌دهی ساده و مستقیم بدون استفاده از پایگاه دانش'
            : 'پاسخ‌دهی پیشرفته با استفاده کامل از پایگاه دانش و قابلیت‌های هوشمند'
    }

    if (isInitialLoading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
            </div>
        )
    }

    return (
        <div className="flex bg-gray-50 h-[calc(100vh-130px)]">
            {/* Sidebar */}
            <div className={`${isSidebarOpen ? 'w-80' : 'w-0'} transition-all duration-300 bg-white border-l border-gray-200 flex flex-col overflow-hidden`}>
                {/* Header */}
                <div className="p-4 border-b border-gray-200">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold text-gray-900">چت ادمین</h2>
                        <Button
                            onClick={createNewConversation}
                            size="sm"
                            className="bg-blue-600 hover:bg-blue-700"
                        >
                            <Plus className="h-4 w-4 ml-1" />
                            گفتگوی جدید
                        </Button>
                    </div>

                    {/* RAG Type Selection */}
                    <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            نوع RAG:
                        </label>
                        <div className="space-y-2">
                            <label className="flex items-center">
                                <input
                                    type="radio"
                                    name="ragType"
                                    value="simple"
                                    checked={ragType === 'simple'}
                                    onChange={(e) => setRagType(e.target.value as RAGType)}
                                    className="ml-2"
                                />
                                <div className="flex items-center">
                                    <Zap className="h-4 w-4 ml-2 text-yellow-500" />
                                    <span className="text-sm">Simple RAG</span>
                                </div>
                            </label>
                            <label className="flex items-center">
                                <input
                                    type="radio"
                                    name="ragType"
                                    value="agentic"
                                    checked={ragType === 'agentic'}
                                    onChange={(e) => setRagType(e.target.value as RAGType)}
                                    className="ml-2"
                                />
                                <div className="flex items-center">
                                    <Brain className="h-4 w-4 ml-2 text-purple-500" />
                                    <span className="text-sm">Agentic RAG</span>
                                </div>
                            </label>
                        </div>
                        <p className="text-xs text-gray-500 mt-2">
                            {getRagTypeDescription(ragType)}
                        </p>
                    </div>

                    {/* Search */}
                    <div className="relative">
                        <Search className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                        <input
                            type="text"
                            placeholder="جستجو در گفتگوها..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pr-10 pl-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        />
                    </div>
                </div>

                {/* Conversations List */}
                <div className="flex-1 overflow-y-auto">
                    {filteredConversations.length === 0 ? (
                        <div className="p-4 text-center text-gray-500">
                            <Bot className="h-12 w-12 mx-auto mb-2 text-gray-300" />
                            <p>هنوز گفتگویی ندارید</p>
                        </div>
                    ) : (
                        filteredConversations.map((conversation) => (
                            <div
                                key={conversation.id}
                                className={`p-4 border-b border-gray-100 cursor-pointer hover:bg-gray-50 transition-colors ${
                                    selectedConversation?.id === conversation.id ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''
                                }`}
                                onClick={() => handleConversationClick(conversation)}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center mb-1">
                                            {getRagTypeIcon(conversation.rag_type || 'simple')}
                                            <h3 className="text-sm font-medium text-gray-900 truncate mr-2">
                                                {conversation.title}
                                            </h3>
                                        </div>
                                        <p className="text-xs text-gray-500">
                                            {getRagTypeLabel(conversation.rag_type || 'simple')}
                                        </p>
                                        {conversation.messages.length > 0 && (
                                            <p className="text-xs text-gray-400 mt-1 truncate">
                                                {conversation.messages[conversation.messages.length - 1].content}
                                            </p>
                                        )}
                                    </div>
                                    <Button
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            deleteConversation(conversation.id)
                                        }}
                                        variant="ghost"
                                        size="sm"
                                        className="text-gray-400 hover:text-red-500 p-1"
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col">
                {/* Header */}
                <div className="bg-white border-b border-gray-200 p-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center">
                            <Button
                                onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                                variant="ghost"
                                size="sm"
                                className="ml-2"
                            >
                                {isSidebarOpen ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
                            </Button>
                            <div className="flex items-center">
                                <Bot className="h-6 w-6 text-blue-600 ml-2" />
                                <div>
                                    <h1 className="text-lg font-semibold text-gray-900">
                                        چت با Sally - {selectedConversation?.title || 'گفتگوی جدید'}
                                    </h1>
                                    <div className="flex items-center text-sm text-gray-500">
                                        {getRagTypeIcon(ragType)}
                                        <span className="mr-1">{getRagTypeLabel(ragType)}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {!selectedConversation ? (
                        <div className="flex flex-col items-center justify-center h-full text-gray-500">
                            <Bot className="h-16 w-16 mb-4 text-gray-300" />
                            <h3 className="text-xl font-medium mb-2">به چت ادمین خوش آمدید</h3>
                            <p className="text-center mb-4">
                                برای شروع، یک گفتگوی جدید ایجاد کنید یا از گفتگوهای موجود انتخاب کنید
                            </p>
                            <div className="bg-blue-50 p-4 rounded-lg max-w-md">
                                <h4 className="font-medium text-blue-900 mb-2">انواع RAG:</h4>
                                <ul className="text-sm text-blue-800 space-y-1">
                                    <li className="flex items-center">
                                        <Zap className="h-4 w-4 ml-2 text-yellow-500" />
                                        Simple RAG: پاسخ‌دهی مستقیم
                                    </li>
                                    <li className="flex items-center">
                                        <Brain className="h-4 w-4 ml-2 text-purple-500" />
                                        Agentic RAG: پاسخ‌دهی هوشمند با پایگاه دانش
                                    </li>
                                </ul>
                            </div>
                        </div>
                    ) : (
                        <>
                            {selectedConversation.messages.map((message) => (
                                <div
                                    key={message.id}
                                    className={`flex ${message.role === 'user' ? 'justify-start' : 'justify-end'}`}
                                >
                                    <div
                                        className={`max-w-xs lg:max-w-md xl:max-w-lg px-4 py-2 rounded-lg ${
                                            message.role === 'user'
                                                ? 'bg-gray-200 text-gray-900'
                                                : 'bg-blue-600 text-white'
                                        }`}
                                    >
                                        <div className="flex items-start">
                                            {message.role === 'user' ? (
                                                <User className="h-4 w-4 ml-2 mt-0.5 flex-shrink-0" />
                                            ) : (
                                                <Bot className="h-4 w-4 ml-2 mt-0.5 flex-shrink-0" />
                                            )}
                                            <div className="flex-1">
                                                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                                                <div className="flex items-center justify-between mt-2">
                                                    <span className="text-xs opacity-70">
                                                        {formatTime(message.timestamp)}
                                                    </span>
                                                    {message.metadata?.rag_type && (
                                                        <div className="flex items-center text-xs opacity-70">
                                                            {getRagTypeIcon(message.metadata.rag_type)}
                                                            <span className="mr-1">{getRagTypeLabel(message.metadata.rag_type)}</span>
                                                        </div>
                                                    )}
                                                </div>
                                                {message.sources && message.sources.length > 0 && (
                                                    <div className="mt-2 p-2 bg-blue-50 rounded text-xs">
                                                        <p className="font-medium text-blue-800 mb-1">📚 منابع مرتبط:</p>
                                                        <div className="space-y-1">
                                                            {message.sources.map((source, index) => (
                                                                <button
                                                                    key={index}
                                                                    onClick={() => handleSourceClick(source.id, source.title)}
                                                                    className="flex items-center text-blue-700 hover:text-blue-900 hover:bg-blue-100 p-1 rounded transition-colors w-full text-right"
                                                                >
                                                                    <ExternalLink className="h-3 w-3 ml-1 flex-shrink-0" />
                                                                    <span>• {source.title}</span>
                                                                </button>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                                {message.confidence && (
                                                    <div className="mt-1 text-xs opacity-70">
                                                        اعتماد: {Math.round(message.confidence * 100)}%
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                            <div ref={messagesEndRef} />
                        </>
                    )}
                </div>

                {/* Input Area */}
                {selectedConversation && (
                    <div className="bg-white border-t border-gray-200 p-4">
                        <div className="flex items-end space-x-2 space-x-reverse">
                            <div className="flex-1">
                                <Textarea
                                    value={newMessage}
                                    onChange={(e) => setNewMessage(e.target.value)}
                                    onKeyPress={handleKeyPress}
                                    placeholder="پیام خود را بنویسید..."
                                    className="resize-none"
                                    rows={1}
                                    disabled={isLoading}
                                />
                            </div>
                            <Button
                                onClick={handleSendMessage}
                                disabled={!newMessage.trim() || isLoading}
                                className="bg-blue-600 hover:bg-blue-700"
                            >
                                {isLoading ? (
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                ) : (
                                    <Send className="h-4 w-4" />
                                )}
                            </Button>
                        </div>
                        <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
                            <span>Enter برای ارسال، Shift+Enter برای خط جدید</span>
                            <div className="flex items-center">
                                {getRagTypeIcon(ragType)}
                                <span className="mr-1">حالت فعال: {getRagTypeLabel(ragType)}</span>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Article Modal */}
            {selectedArticle && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg max-w-4xl max-h-[80vh] w-full flex flex-col">
                        {/* Modal Header */}
                        <div className="flex items-center justify-between p-4 border-b border-gray-200">
                            <h2 className="text-lg font-semibold text-gray-900 flex-1 ml-4">
                                {selectedArticle.title}
                            </h2>
                            <Button
                                onClick={() => setSelectedArticle(null)}
                                variant="ghost"
                                size="sm"
                                className="text-gray-400 hover:text-gray-600"
                            >
                                <X className="h-5 w-5" />
                            </Button>
                        </div>
                        
                        {/* Modal Content */}
                        <div className="flex-1 overflow-y-auto p-4">
                            <div 
                                className="prose prose-sm max-w-none text-right"
                                dangerouslySetInnerHTML={{ __html: selectedArticle.content }}
                                style={{ direction: 'rtl' }}
                            />
                        </div>
                        
                        {/* Modal Footer */}
                        <div className="flex justify-end p-4 border-t border-gray-200">
                            <Button
                                onClick={() => setSelectedArticle(null)}
                                variant="outline"
                            >
                                بستن
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default SuperAdminChatPage
