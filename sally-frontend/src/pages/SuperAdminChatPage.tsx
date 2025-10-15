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
  Trash2,
  Search,
  Zap,
  Brain,
  BookOpen,
  X,
  ExternalLink,
  Menu,
  Target,
  Settings,
  Cpu,
  Thermometer,
  Sparkles
} from 'lucide-react'
import { Button } from '../components/ui/button'
import { Textarea } from '../components/ui/textarea'
import { MarkdownRenderer } from '../components/ui/markdown-renderer'
import { VoiceInput } from '../components/ui/voice-input'
import { chatService } from '../services/chatService'
import { useAuth } from '../context/AuthContext'
import { toast } from 'react-hot-toast'
import ArticleHighlightModal from '../components/ArticleHighlightModal'

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
    rag_type?: 'simple' | 'agentic' | 'detailed'
    complexity?: string
    complexity_fa?: string
    model?: string
    can_get_more_details?: boolean  // 🔥 فیلد جدید برای نمایش دکمه توضیحات کامل
  }
  sources?: Array<{ title: string; id: string }>
  confidence?: number
  suggested_actions?: string[]
  complexity_fa?: string
  model?: string
}

interface Conversation {
  id: string
  title: string
  messages: Message[]
  created_at?: string
  updated_at?: string
  rag_type?: 'simple' | 'agentic' | 'detailed'
}

type RAGType = 'simple' | 'agentic' | 'detailed'
type AdminRAGType = 'simple' | 'agentic'

// 🤖 لیست مدل‌های موجود
const AVAILABLE_MODELS = [
  // 🏆 بهترین مدل‌ها برای RAG (براساس تست‌های واقعی - مرتب شده براساس سرعت)
  
  // 🥇 سریع‌ترین (264 ch/s، 0% empty chunks)
  { id: 'google/gemini-2.5-flash', name: '🏆 Gemini 2.5 Flash', provider: 'Google', description: '✅ سریع‌ترین - 264 ch/s، رایگان' },
  { id: 'qwen/qwen3-235b-a22b:free', name: 'Qwen 3', provider: 'Alibaba', description: '✅ سریع‌ترین - 264 ch/s، رایگان' },

  // 🥈 مدل‌های رایگان عالی
  { id: 'deepseek/deepseek-chat-v3.1:free', name: '⭐ DeepSeek V3.1 (Free)', provider: 'DeepSeek', description: '✅ 117 ch/s، 0% empty، رایگان' },
  
  // 🥉 OpenAI رسمی (از Embedder API استفاده می‌کند)
  { id: 'gpt-4o-mini', name: '⭐ GPT-4o Mini', provider: 'OpenAI', description: '✅ 89 ch/s، پایدار، کیفیت بالا' },
  { id: 'gpt-4o', name: 'GPT-4o', provider: 'OpenAI', description: 'قدرتمندترین OpenAI' },
  { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', provider: 'OpenAI', description: 'نسخه توربو GPT-4' },
  
  // ⚠️ مدل‌های با chunks زیاد (کار می‌کنند اما بهینه نیستند)
  { id: 'x-ai/grok-4-fast', name: 'Grok 4 Fast ⚠️', provider: 'xAI', description: '143 ch/s، اما 70% empty chunks' },
  { id: 'x-ai/grok-3-mini-beta', name: 'Grok 3 Mini Beta ⚠️', provider: 'xAI', description: '149 ch/s، اما 65% empty chunks' },
  
  // سایر مدل‌ها
  { id: 'deepseek/deepseek-r1-0528', name: 'DeepSeek R1', provider: 'DeepSeek', description: 'مدل قدرتمند DeepSeek' },
  { id: 'qwen/qwen3-235b-a22b-2507', name: 'Qwen 3', provider: 'Qwen', description: 'مدل Alibaba' },
  
  // Ollama Local Models
  { id: 'ollama:gpt-oss:20b', name: 'GPT-OSS 20B', provider: 'Ollama', description: 'مدل محلی OpenAI' },
  { id: 'ollama:gemma3n:e4b', name: 'Gemma 3N E4B', provider: 'Ollama', description: 'مدل محلی قدرتمند Google' },
  { id: 'ollama:llama3.1:8b-instruct-q4_0', name: 'Llama 3.1 8B', provider: 'Ollama', description: 'مدل محلی Meta' },
]

const SuperAdminChatPage = () => {
    const { user } = useAuth()
    const [isSidebarOpen, setIsSidebarOpen] = useState(false) // ✅ Default: closed on mobile
    const [conversations, setConversations] = useState<Conversation[]>([])
    const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)
    const [newMessage, setNewMessage] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [isInitialLoading, setIsInitialLoading] = useState(true)
    const [searchQuery, setSearchQuery] = useState('')
    const [ragType, setRagType] = useState<AdminRAGType>('simple')
    const [selectedArticle, setSelectedArticle] = useState<{id: string, title: string, content: string} | null>(null)
    const [showSettingsModal, setShowSettingsModal] = useState(false)
    const [selectedModel, setSelectedModel] = useState<string>('google/gemini-2.5-flash')  // 🏆 سریع‌ترین و بهترین مدل برای RAG
    const [temperature, setTemperature] = useState<number>(0.7)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const initializationRef = useRef(false)
    
    // 🔥 Article Highlight Modal state
    const [highlightModal, setHighlightModal] = useState<{
        isOpen: boolean;
        articleId: string;
        userQuery: string;
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

    // Development mode: API might not be available
    const isDevelopment = process.env.NODE_ENV === 'development'

    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [])

    useEffect(() => {
        scrollToBottom()
    }, [selectedConversation?.messages, scrollToBottom])
    
    const toggleSidebar = () => {
        setIsSidebarOpen(!isSidebarOpen)
    }

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

            // 🔥 استفاده از streaming API برای admin
            const assistantTempId = `ai-temp-${Date.now()}`;
            const addAssistantPlaceholder = () => setSelectedConversation(prev => ({
                ...prev!,
                messages: [...(prev?.messages || []), {
                    id: assistantTempId,
                    content: '',
                    role: 'assistant',
                    timestamp: new Date(),
                    metadata: { rag_type: ragType }
                } as Message]
            }));

            addAssistantPlaceholder();

            const currentConvId = selectedConversation.id.startsWith('new-') ? undefined : selectedConversation.id;

            await chatService.sendAdminMessageStream(
                currentConvId,
                messageContent,
                ragType,
                (evt: any) => {
                    if (!evt) return;

                    if (evt.type === 'init') {
                        // Set conversation ID if it was a new chat
                        if (!currentConvId && evt.conversation_id) {
                            setConversations(prev =>
                                prev.map(conv =>
                                    conv.id === selectedConversation.id
                                        ? { ...conv, id: evt.conversation_id }
                                        : conv
                                )
                            );
                            setSelectedConversation(prev => prev ? ({ ...prev, id: evt.conversation_id }) : prev);
                        }
                    }

                    if (evt.type === 'sources') {
                        console.log('📚 Admin sources:', evt.sources);
                        // Add sources to message metadata
                        setSelectedConversation(prev => {
                            if (!prev) return prev;
                            const updated = { ...prev };
                            updated.messages = updated.messages.map(m => 
                                m.id === assistantTempId 
                                    ? { ...m, sources: evt.sources, confidence: evt.confidence }
                                    : m
                            );
                            return updated;
                        });
                    }

                    if (evt.type === 'chunk') {
                        setSelectedConversation(prev => {
                            if (!prev) return prev;
                            const updated = { ...prev };
                            updated.messages = updated.messages.map(m =>
                                m.id === assistantTempId
                                    ? { ...m, content: (m.content || '') + (evt.content || '') }
                                    : m
                            );
                            return updated;
                        });
                    }

                    if (evt.type === 'complete') {
                        setSelectedConversation(prev => {
                            if (!prev) return prev;
                            const updated = { ...prev };
                            updated.messages = updated.messages.map(m =>
                                m.id === assistantTempId
                                    ? { 
                                        ...m, 
                                        id: evt.message_id || assistantTempId, 
                                        content: evt.full_response || m.content,
                                        complexity_fa: evt.complexity_fa,
                                        model: evt.model,
                                        metadata: {
                                            ...(m.metadata || {}),
                                            rag_type: evt.rag_type,
                                            can_get_more_details: evt.can_get_more_details || false  // 🔥 فیلد کلیدی برای نمایش دکمه
                                        }
                                    }
                                    : m
                            );
                            return updated;
                        });
                        setIsLoading(false);
                        
                        // 🔥 بعد از تکمیل پاسخ، لیست conversations رو refresh کن
                        const finalConvId = evt.conversation_id || currentConvId;
                        console.log('🔍 DEBUG: Starting conversation refresh...', { 
                            finalConvId, 
                            evt_conversation_id: evt.conversation_id,
                            currentConvId,
                            evt_rag_type: evt.rag_type 
                        });
                        
                        if (finalConvId) {
                            setTimeout(async () => {
                                try {
                                    console.log('📡 Fetching conversation from server:', finalConvId);
                                    // دریافت اطلاعات به‌روز conversation از سرور
                                    const updatedConv = await chatService.getConversation(finalConvId);
                                    console.log('📥 Server response:', updatedConv);
                                    
                                    // به‌روزرسانی لیست conversations
                                    setConversations(prev => {
                                        console.log('📝 Current conversations before update:', prev.map(c => ({ id: c.id, title: c.title, rag_type: c.rag_type })));
                                        
                                        const exists = prev.some(c => c.id === finalConvId);
                                        console.log('🔍 Conversation exists in list:', exists);
                                        
                                        if (exists) {
                                            // اگر موجود بود، اطلاعاتش رو update کن
                                            const updated = prev.map(c => 
                                                c.id === finalConvId 
                                                    ? { 
                                                        ...c, 
                                                        title: updatedConv.title || c.title,
                                                        rag_type: updatedConv.rag_type || evt.rag_type,
                                                        updated_at: updatedConv.updated_at
                                                    }
                                                    : c
                                            );
                                            console.log('📝 Updated conversations:', updated.map(c => ({ id: c.id, title: c.title, rag_type: c.rag_type })));
                                            return updated;
                                        } else {
                                            // اگر موجود نبود (مکالمه جدید)، اضافه‌اش کن
                                            const newConversation = {
                                                id: finalConvId,
                                                title: updatedConv.title || messageContent.slice(0, 50),
                                                messages: [],
                                                created_at: updatedConv.created_at || new Date().toISOString(),
                                                updated_at: updatedConv.updated_at || new Date().toISOString(),
                                                rag_type: updatedConv.rag_type || evt.rag_type
                                            };
                                            console.log('➕ Adding new conversation:', newConversation);
                                            return [newConversation, ...prev];
                                        }
                                    });
                                    
                                    // به‌روزرسانی selectedConversation با عنوان و rag_type جدید
                                    setSelectedConversation(prev => {
                                        if (!prev) return prev;
                                        const updated = {
                                            ...prev,
                                            title: updatedConv.title || prev.title,
                                            rag_type: updatedConv.rag_type || evt.rag_type
                                        };
                                        console.log('🎯 Updated selectedConversation:', { 
                                            old_title: prev.title, 
                                            new_title: updated.title,
                                            old_rag_type: prev.rag_type,
                                            new_rag_type: updated.rag_type
                                        });
                                        return updated;
                                    });
                                    
                                    console.log('✅ Conversation updated successfully:', { 
                                        id: finalConvId, 
                                        title: updatedConv.title,
                                        rag_type: updatedConv.rag_type || evt.rag_type 
                                    });
                                } catch (error) {
                                    console.error('❌ Failed to refresh conversation:', error);
                                }
                            }, 500); // کمی تاخیر تا سرور عنوان رو generate کنه
                        } else {
                            console.warn('⚠️ No finalConvId available for refresh');
                        }
                    }

                    if (evt.type === 'error') {
                        toast.error(`خطا: ${evt.message}`);
                        setSelectedConversation(prev => {
                            if (!prev) return prev;
                            const updated = { ...prev };
                            updated.messages = updated.messages.map(m =>
                                m.id === assistantTempId
                                    ? { ...m, is_failed: true, failure_reason: evt.message }
                                    : m
                            );
                            return updated;
                        });
                        setIsLoading(false);
                    }
                },
                selectedModel,
                temperature
            );

        } catch (error: any) {
            console.error('Failed to send message (streaming):', error)
            toast.error('خطا در ارسال پیام')
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

    const handleSourceClick = async (sourceId: string, messageId: string) => {
        // 🔥 پیدا کردن سوال کاربر از message قبلی
        const messageIndex = selectedConversation?.messages.findIndex(m => m.id === messageId);
        const userMessage = messageIndex !== undefined && messageIndex > 0
            ? selectedConversation?.messages[messageIndex - 1]
            : null;
        const userQuery = userMessage?.role === 'user' ? userMessage.content : '';
        
        console.log('🖱️ Admin source clicked!');
        console.log('   Article ID:', sourceId);
        console.log('   User Query:', userQuery);
        
        if (!sourceId) {
            toast.error('شناسه مقاله موجود نیست!');
            return;
        }
        
        setHighlightModal({
            isOpen: true,
            articleId: sourceId,
            userQuery: userQuery
        });
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
        if (type === 'simple') return <Zap className="h-4 w-4" />
        if (type === 'detailed') return <BookOpen className="h-4 w-4" />
        return <Brain className="h-4 w-4" />
    }

    const getRagTypeLabel = (type: RAGType) => {
        if (type === 'simple') return 'Simple RAG'
        if (type === 'detailed') return 'Detailed RAG'
        return 'Agentic RAG'
    }

    if (isInitialLoading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
            </div>
        )
    }

    return (
        <>
            {/* 🔥 Article Highlight Modal */}
            {highlightModal.isOpen && (
                <ArticleHighlightModal
                    articleId={highlightModal.articleId}
                    userQuery={highlightModal.userQuery}
                    onClose={() => setHighlightModal({ isOpen: false, articleId: '', userQuery: '' })}
                />
            )}
            
            {/* ⚙️ Settings Modal */}
            {showSettingsModal && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowSettingsModal(false)}>
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                        <div className="sticky top-0 bg-gradient-to-r from-purple-600 to-blue-600 text-white p-6 rounded-t-2xl">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Settings className="w-6 h-6" />
                                    <h2 className="text-xl font-bold">تنظیمات پیشرفته چت</h2>
                                </div>
                                <button
                                    onClick={() => setShowSettingsModal(false)}
                                    className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                    </div>

                        {/* Content */}
                        <div className="p-6 space-y-6">
                    {/* RAG Type Selection */}
                            <div>
                                <label className="block text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                                    <Brain className="w-4 h-4 text-purple-600" />
                                    نوع سیستم RAG
                        </label>
                                <div className="grid grid-cols-2 gap-3">
                                    <button
                                        onClick={() => setRagType('simple')}
                                        className={`p-4 rounded-xl border-2 transition-all ${
                                            ragType === 'simple'
                                                ? 'border-blue-500 bg-blue-50 shadow-md'
                                                : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
                                        }`}
                                    >
                                        <div className="flex items-center gap-2 mb-2">
                                            <Zap className={`w-5 h-5 ${ragType === 'simple' ? 'text-blue-600' : 'text-gray-400'}`} />
                                            <span className={`font-bold ${ragType === 'simple' ? 'text-blue-900' : 'text-gray-700'}`}>
                                                Simple RAG
                                            </span>
                                </div>
                                        <p className="text-xs text-gray-600 text-right">
                                            جستجوی ساده و سریع در پایگاه دانش
                                        </p>
                                    </button>
                                    <button
                                        onClick={() => setRagType('agentic')}
                                        className={`p-4 rounded-xl border-2 transition-all ${
                                            ragType === 'agentic'
                                                ? 'border-purple-500 bg-purple-50 shadow-md'
                                                : 'border-gray-200 hover:border-purple-300 hover:bg-gray-50'
                                        }`}
                                    >
                                        <div className="flex items-center gap-2 mb-2">
                                            <Brain className={`w-5 h-5 ${ragType === 'agentic' ? 'text-purple-600' : 'text-gray-400'}`} />
                                            <span className={`font-bold ${ragType === 'agentic' ? 'text-purple-900' : 'text-gray-700'}`}>
                                                Agentic RAG
                                            </span>
                                        </div>
                                        <p className="text-xs text-gray-600 text-right">
                                            تحلیل هوشمند با Agent‌های پیشرفته
                                        </p>
                                    </button>
                                </div>
                            </div>

                            {/* Model Selection */}
                            <div>
                                <label className="block text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                                    <Cpu className="w-4 h-4 text-purple-600" />
                                    انتخاب مدل هوش مصنوعی
                            </label>
                                <div className="grid grid-cols-1 gap-2 max-h-80 overflow-y-auto border border-gray-200 rounded-lg p-3">
                                    {AVAILABLE_MODELS.map((model) => (
                                        <button
                                            key={model.id}
                                            onClick={() => setSelectedModel(model.id)}
                                            className={`p-3 rounded-lg border transition-all text-right ${
                                                selectedModel === model.id
                                                    ? 'border-purple-500 bg-gradient-to-r from-purple-50 to-blue-50 shadow-sm'
                                                    : 'border-gray-200 hover:border-purple-300 hover:bg-gray-50'
                                            }`}
                                        >
                                            <div className="flex items-start justify-between gap-3">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className={`font-bold text-sm ${
                                                            selectedModel === model.id ? 'text-purple-900' : 'text-gray-800'
                                                        }`}>
                                                            {model.name}
                                                        </span>
                                                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                                                            model.provider === 'Ollama' 
                                                                ? 'bg-green-100 text-green-700'
                                                                : model.provider === 'OpenAI'
                                                                ? 'bg-blue-100 text-blue-700'
                                                                : 'bg-gray-100 text-gray-700'
                                                        }`}>
                                                            {model.provider}
                                                        </span>
                                                    </div>
                                                    <p className="text-xs text-gray-600">{model.description}</p>
                                                </div>
                                                {selectedModel === model.id && (
                                                    <div className="w-5 h-5 bg-purple-600 rounded-full flex items-center justify-center flex-shrink-0">
                                                        <div className="w-2 h-2 bg-white rounded-full" />
                                                    </div>
                                                )}
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Temperature Control */}
                            <div>
                                <label className="block text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                                    <Thermometer className="w-4 h-4 text-purple-600" />
                                    دمای تولید (Temperature): {temperature.toFixed(1)}
                                </label>
                                <div className="space-y-2">
                                <input
                                        type="range"
                                        min="0"
                                        max="2"
                                        step="0.1"
                                        value={temperature}
                                        onChange={(e) => setTemperature(parseFloat(e.target.value))}
                                        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-600"
                                    />
                                    <div className="flex justify-between text-xs text-gray-600">
                                        <span>دقیق (0.0)</span>
                                        <span>متعادل (1.0)</span>
                                        <span>خلاق (2.0)</span>
                                </div>
                                    <p className="text-xs text-gray-500 bg-gray-50 p-3 rounded-lg">
                                        💡 <strong>راهنما:</strong> مقادیر پایین‌تر برای پاسخ‌های دقیق‌تر و مقادیر بالاتر برای پاسخ‌های خلاقانه‌تر
                                    </p>
                        </div>
                            </div>

                            {/* Current Settings Display */}
                            <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-4 rounded-lg border border-purple-200">
                                <h3 className="text-sm font-bold text-purple-900 mb-3">تنظیمات فعلی:</h3>
                                <div className="space-y-2 text-sm">
                                    <div className="flex items-center justify-between">
                                        <span className="text-gray-600">نوع RAG:</span>
                                        <span className="font-bold text-purple-900">
                                            {ragType === 'agentic' ? 'Agentic RAG (پیشرفته)' : 'Simple RAG (ساده)'}
                                        </span>
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <span className="text-gray-600">مدل:</span>
                                        <span className="font-bold text-purple-900">
                                            {AVAILABLE_MODELS.find(m => m.id === selectedModel)?.name || selectedModel}
                                        </span>
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <span className="text-gray-600">Temperature:</span>
                                        <span className="font-bold text-purple-900">{temperature.toFixed(1)}</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Footer */}
                        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 p-4 rounded-b-2xl flex gap-3">
                            <Button
                                onClick={() => setShowSettingsModal(false)}
                                variant="secondary"
                                className="flex-1"
                            >
                                بستن
                            </Button>
                            <Button
                                onClick={() => {
                                    setShowSettingsModal(false)
                                    // تنظیمات ذخیره می‌شوند و در ارسال پیام بعدی استفاده می‌شوند
                                }}
                                className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
                            >
                                ✅ ذخیره تنظیمات
                            </Button>
                        </div>
                    </div>
                </div>
            )}
            
            <div className="flex bg-gray-50 h-[calc(100vh-130px)] relative">
            {/* Mobile Overlay */}
            {isSidebarOpen && (
                <div 
                    className="fixed inset-0 bg-black/50 z-40 lg:hidden"
                    onClick={toggleSidebar}
                />
            )}
            
            {/* Sidebar */}
            <div className={`
                fixed lg:relative z-50 lg:z-0
                w-80 lg:w-80
                h-full lg:h-auto
                ${isSidebarOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'}
                ${isSidebarOpen ? 'lg:w-80' : 'lg:w-0'}
                transition-all duration-300
                bg-white border-l border-gray-200
                flex flex-col overflow-hidden
                top-0 right-0
            `}>
                {/* Header */}
                <div className="p-4 border-b border-gray-200">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                            <Brain className="w-5 h-5 text-purple-600" />
                            چت ادمین ارشد
                        </h2>
                        <Button
                            onClick={toggleSidebar}
                            size="sm"
                            variant="ghost"
                            className="lg:hidden"
                        >
                            <X className="w-5 h-5" />
                        </Button>
                    </div>
                    
                    {/* New Chat Button */}
                    <Button
                        onClick={createNewConversation}
                        className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white shadow-md mb-3"
                    >
                        <Plus className="w-4 h-4 mr-2" />
                        گفتگوی جدید
                    </Button>

                    {/* Settings Button */}
                    <Button
                        onClick={() => setShowSettingsModal(true)}
                        variant="secondary"
                        className="w-full mb-4 flex items-center justify-center gap-2"
                    >
                        <Settings className="w-4 h-4" />
                        تنظیمات پیشرفته
                    </Button>

                    {/* Current Settings Display */}
                    <div className="mb-4 p-3 bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg border border-purple-200">
                        <p className="text-xs text-gray-600 mb-2 font-medium flex items-center gap-1">
                            <Brain className="w-3 h-3" />
                            تنظیمات فعلی:
                        </p>
                        <div className="space-y-1 text-xs text-gray-700">
                            <div className="flex items-center justify-between">
                                <span>RAG:</span>
                                <span className={`font-bold ${
                                    ragType === 'agentic' ? 'text-purple-700' : 'text-blue-700'
                                }`}>
                                    {ragType === 'agentic' ? 'پیشرفته' : 'ساده'}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span>مدل:</span>
                                <span className="font-bold text-purple-700">
                                    {AVAILABLE_MODELS.find(m => m.id === selectedModel)?.name || 'GPT-4o Mini'}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span>Temperature:</span>
                                <span className="font-bold text-purple-700">{temperature.toFixed(1)}</span>
                            </div>
                        </div>
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
                        <div className="p-6 text-center text-gray-500">
                            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
                                <Bot className="w-8 h-8 text-gray-400" />
                            </div>
                            <p className="text-sm">هنوز گفتگویی ندارید</p>
                            <p className="text-xs mt-1">یک گفتگوی جدید شروع کنید</p>
                        </div>
                    ) : (
                        filteredConversations.map((conversation) => (
                            <div
                                key={conversation.id}
                                className={`group p-3 border-b border-gray-100 cursor-pointer transition-all ${
                                    selectedConversation?.id === conversation.id
                                        ? 'bg-gradient-to-r from-purple-50 to-blue-50 border-r-4 border-r-purple-500'
                                        : 'hover:bg-gray-50'
                                }`}
                                onClick={() => handleConversationClick(conversation)}
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                                                conversation.rag_type === 'agentic'
                                                    ? 'bg-gradient-to-r from-purple-100 to-blue-100'
                                                    : 'bg-blue-100'
                                            }`}>
                                            {getRagTypeIcon(conversation.rag_type || 'simple')}
                                            </div>
                                            <h3 className="text-sm font-medium text-gray-900 truncate flex-1">
                                                {conversation.title}
                                            </h3>
                                        </div>
                                        <div className="flex flex-wrap items-center gap-1 mb-1">
                                            <span className={`text-xs ${
                                                conversation.rag_type === 'agentic' ? 'text-purple-600' : 'text-blue-600'
                                            }`}>
                                                {getRagTypeLabel(conversation.rag_type || 'simple')}
                                            </span>
                                            {/* Complexity */}
                                            {conversation.messages.length > 0 && conversation.messages[conversation.messages.length - 1].complexity_fa && (
                                                <span className="text-xs px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded">
                                                    {conversation.messages[conversation.messages.length - 1].complexity_fa === 'ساده' && '🟢'}
                                                    {conversation.messages[conversation.messages.length - 1].complexity_fa === 'متوسط' && '🟡'}
                                                    {conversation.messages[conversation.messages.length - 1].complexity_fa === 'پیچیده' && '🔴'}
                                                    {conversation.messages[conversation.messages.length - 1].complexity_fa}
                                                </span>
                                            )}
                                            {/* Model */}
                                            {conversation.messages.length > 0 && conversation.messages[conversation.messages.length - 1].model && (
                                                <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded truncate max-w-[120px]">
                                                    {AVAILABLE_MODELS.find(m => m.id === conversation.messages[conversation.messages.length - 1].model)?.name || 
                                                     conversation.messages[conversation.messages.length - 1].model?.split('/').pop()}
                                                </span>
                                            )}
                                        </div>
                                        {conversation.messages.length > 0 && (
                                            <p className="text-xs text-gray-500 truncate">
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
                                        className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-red-500 p-1"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </Button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col min-w-0">
                {/* Header */}
                <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white p-3 md:p-4 shadow-lg">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 md:gap-3 min-w-0 flex-1">
                            {/* Mobile Menu Button */}
                            <Button
                                onClick={toggleSidebar}
                                variant="ghost"
                                size="sm"
                                className="lg:hidden text-white hover:bg-white/20"
                            >
                                <Menu className="w-5 h-5" />
                            </Button>
                            
                            {/* Desktop Toggle */}
                            <Button
                                onClick={toggleSidebar}
                                variant="ghost"
                                size="sm"
                                className="hidden lg:flex text-white hover:bg-white/20"
                            >
                                {isSidebarOpen ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
                            </Button>
                            
                            {/* Title */}
                            <div className="flex items-center gap-2 min-w-0 flex-1">
                                <div className="w-8 h-8 md:w-10 md:h-10 bg-white/20 rounded-full flex items-center justify-center flex-shrink-0">
                                    <Bot className="w-4 h-4 md:w-5 md:h-5" />
                                </div>
                                <div className="min-w-0 flex-1">
                                    <h1 className="text-sm md:text-lg font-bold truncate">
                                        {selectedConversation?.title || 'گفتگوی جدید'}
                                    </h1>
                                    <div className="flex items-center gap-1 text-xs md:text-sm text-white/90">
                                        {getRagTypeIcon(ragType)}
                                        <span>{getRagTypeLabel(ragType)}</span>
                                        <span className="hidden md:inline">•</span>
                                        <span className="hidden md:inline">
                                            {AVAILABLE_MODELS.find(m => m.id === selectedModel)?.name || 'GPT-4o Mini'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        {/* Settings Button */}
                        <Button
                            onClick={() => setShowSettingsModal(true)}
                            variant="ghost"
                            size="sm"
                            className="text-white hover:bg-white/20 flex items-center gap-2"
                        >
                            <Settings className="w-4 h-4 md:w-5 md:h-5" />
                            <span className="hidden md:inline text-sm">تنظیمات</span>
                        </Button>
                    </div>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-3 md:p-6 space-y-4">
                    {!selectedConversation ? (
                        <div className="flex flex-col items-center justify-center h-full text-gray-500 p-4">
                            <div className="w-16 h-16 md:w-20 md:h-20 bg-gradient-to-r from-purple-100 to-blue-100 rounded-full flex items-center justify-center mb-4">
                                <Bot className="w-8 h-8 md:w-10 md:h-10 text-purple-600" />
                            </div>
                            <h3 className="text-lg md:text-xl font-bold mb-2 text-gray-900">به چت ادمین ارشد خوش آمدید! 👋</h3>
                            <p className="text-center mb-6 text-sm md:text-base max-w-md">
                                برای شروع، یک گفتگوی جدید ایجاد کنید یا از گفتگوهای موجود انتخاب کنید
                            </p>
                            <div className="grid md:grid-cols-2 gap-4 w-full max-w-2xl">
                                <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 md:p-5 rounded-xl border border-blue-200">
                                    <div className="flex items-center gap-2 mb-3">
                                        <Zap className="w-5 h-5 text-blue-600" />
                                        <h4 className="font-bold text-blue-900">Simple RAG</h4>
                                    </div>
                                    <p className="text-sm text-blue-800">جستجوی ساده و سریع در پایگاه دانش</p>
                                </div>
                                <div className="bg-gradient-to-br from-purple-50 to-blue-100 p-4 md:p-5 rounded-xl border border-purple-200">
                                    <div className="flex items-center gap-2 mb-3">
                                        <Brain className="w-5 h-5 text-purple-600" />
                                        <h4 className="font-bold text-purple-900">Agentic RAG</h4>
                                    </div>
                                    <p className="text-sm text-purple-800">تحلیل هوشمند با Agent‌های پیشرفته</p>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <>
                            {selectedConversation.messages.map((message, messageIndex) => {
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
                                                
                                                {/* Metadata: Complexity & Model */}
                                                {message.role === 'assistant' && (message.complexity_fa || message.model) && (
                                                    <div className="mt-3 pt-3 border-t border-gray-200 flex flex-wrap items-center gap-2 text-xs">
                                                        {message.complexity_fa && (
                                                            <div className="flex items-center gap-1 px-2 py-1 bg-purple-50 rounded-md">
                                                                <Brain className="w-3 h-3 text-purple-600" />
                                                                <span className="text-purple-700 font-medium">
                                                                    {message.complexity_fa === 'ساده' && '🟢 ساده'}
                                                                    {message.complexity_fa === 'متوسط' && '🟡 متوسط'}
                                                                    {message.complexity_fa === 'پیچیده' && '🔴 پیچیده'}
                                                                </span>
                                                            </div>
                                                        )}
                                                        {message.model && (
                                                            <div className="flex items-center gap-1 px-2 py-1 bg-blue-50 rounded-md">
                                                                <Cpu className="w-3 h-3 text-blue-600" />
                                                                <span className="text-blue-700 font-medium">
                                                                    {AVAILABLE_MODELS.find(m => m.id === message.model)?.name || message.model}
                                                                </span>
                                                            </div>
                                                        )}
                                                    </div>
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
                                                
                                                {/* RAG Type Badge */}
                                                    {message.metadata?.rag_type && (
                                                    <div className="mt-2 flex items-center gap-1 text-xs text-gray-600">
                                                            {getRagTypeIcon(message.metadata.rag_type)}
                                                        <span>{getRagTypeLabel(message.metadata.rag_type)}</span>
                                                        </div>
                                                    )}
                                                </div>

                                            {/* Sources */}
                                            {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                                                <div className="mt-2 md:mt-3 space-y-2">
                                                    <p className="text-xs text-gray-600 font-medium flex items-center gap-1">
                                                        <Target className="w-3 h-3" />
                                                        منابع مرتبط:
                                                    </p>
                                                    <div className="flex flex-wrap gap-2">
                                                            {message.sources.map((source, index) => (
                                                                <button
                                                                    key={index}
                                                                    onClick={() => handleSourceClick(source.id, message.id)}
                                                                className="inline-flex items-center gap-1 px-3 py-1.5 bg-gradient-to-r from-blue-50 to-purple-50 hover:from-blue-100 hover:to-purple-100 border border-blue-200 rounded-full text-xs text-blue-700 hover:text-blue-900 transition-all"
                                                                >
                                                                <ExternalLink className="w-3 h-3" />
                                                                {source.title}
                                                                </button>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                            
                                            {/* Get More Details Button */}
                                            {message.role === 'assistant' && message.metadata?.can_get_more_details && message.metadata?.rag_type === 'simple' && (
                                                <div className="mt-3">
                                                    <button
                                                        onClick={async () => {
                                                            // ارسال مجدد همان سوال با rag_type="agentic" برای دریافت جزئیات بیشتر
                                                            if (!userQuery) {
                                                                toast.error('سوال اصلی یافت نشد');
                                                                return;
                                                            }
                                                            
                                                            console.log('🔥 Getting more details for query:', userQuery);
                                                            console.log('🔥 Switching from simple to agentic RAG');
                                                            
                                                            if (!selectedConversation?.id) {
                                                                toast.error('گفتگوی فعال یافت نشد');
                                                                return;
                                                            }
                                                            
                                                            setIsLoading(true);
                                                            
                                                            // ایجاد پیام کاربر جدید با محتوای سوال قبلی
                                                            const userTempId = Date.now().toString();
                                                            const userMsg: Message = {
                                                                id: userTempId,
                                                                content: `🔍 ${userQuery}\n\n(درخواست توضیحات کامل)`,
                                                                role: 'user',
                                                                timestamp: new Date(),
                                                                sender_type: 'SuperAdmin',
                                                            };
                                                            
                                                            // ایجاد پیام موقت پاسخ
                                                            const assistantTempId = (Date.now() + 1).toString();
                                                            const assistantMsg: Message = {
                                                                id: assistantTempId,
                                                                content: '',
                                                                role: 'assistant',
                                                                timestamp: new Date(),
                                                                sender_type: 'AI',
                                                            };
                                                            
                                                            // اضافه کردن پیام‌ها به گفتگو
                                                            setSelectedConversation(prev => {
                                                                if (!prev) return prev;
                                                                return {
                                                                    ...prev,
                                                                    messages: [...prev.messages, userMsg, assistantMsg]
                                                                };
                                                            });
                                                            
                                                            // اسکرول به انتهای صفحه
                                                            setTimeout(() => {
                                                                messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
                                                            }, 100);
                                                            
                                                            try {
                                                                // ارسال درخواست با Agentic RAG
                                                                await chatService.sendAdminMessageStream(
                                                                    selectedConversation.id,
                                                                    userQuery, // سوال اصلی بدون اضافه کردن متن
                                                                    'agentic', // 🔥 فورس به Agentic RAG
                                                                    (evt: any) => {
                                                                        if (!evt) return;
                                                                        
                                                                        if (evt.type === 'chunk') {
                                                                            setSelectedConversation(prev => {
                                                                                if (!prev) return prev;
                                                                                const updated = { ...prev };
                                                                                updated.messages = updated.messages.map(m =>
                                                                                    m.id === assistantTempId
                                                                                        ? { ...m, content: (m.content || '') + (evt.content || '') }
                                                                                        : m
                                                                                );
                                                                                return updated;
                                                                            });
                                                                        }
                                                                        
                                                                        if (evt.type === 'complete') {
                                                                            setSelectedConversation(prev => {
                                                                                if (!prev) return prev;
                                                                                const updated = { ...prev };
                                                                                updated.messages = updated.messages.map(m =>
                                                                                    m.id === assistantTempId
                                                                                        ? {
                                                                                            ...m,
                                                                                            id: evt.message_id || assistantTempId,
                                                                                            content: evt.full_response || m.content,
                                                                                            complexity_fa: evt.complexity_fa,
                                                                                            model: evt.model,
                                                                                            confidence: evt.confidence,
                                                                                            sources: evt.sources,
                                                                                            metadata: {
                                                                                                ...(m.metadata || {}),
                                                                                                rag_type: 'agentic',
                                                                                                can_get_more_details: false // دکمه رو برای پاسخ agentic نشون نده
                                                                                            }
                                                                                        }
                                                                                        : m
                                                                                );
                                                                                return updated;
                                                                            });
                                                                            setIsLoading(false);
                                                                            toast.success('✅ توضیحات کامل دریافت شد');
                                                                            
                                                                            // 🔥 به‌روزرسانی لیست conversations با rag_type جدید
                                                                            if (selectedConversation?.id) {
                                                                                console.log('🔍 DEBUG (Agentic): Starting conversation refresh...');
                                                                                setTimeout(async () => {
                                                                                    try {
                                                                                        console.log('📡 Fetching Agentic conversation from server:', selectedConversation.id);
                                                                                        const updatedConv = await chatService.getConversation(selectedConversation.id);
                                                                                        console.log('📥 Server response (Agentic):', updatedConv);
                                                                                        
                                                                                        // به‌روزرسانی لیست conversations
                                                                                        setConversations(prev => {
                                                                                            console.log('📝 Current conversations before Agentic update:', prev.map(c => ({ id: c.id, title: c.title, rag_type: c.rag_type })));
                                                                                            
                                                                                            const updated = prev.map(c => 
                                                                                                c.id === selectedConversation.id 
                                                                                                    ? { 
                                                                                                        ...c, 
                                                                                                        title: updatedConv.title || c.title,
                                                                                                        rag_type: (updatedConv.rag_type as 'simple' | 'agentic' | 'detailed') || 'agentic', // این مکالمه حالا agentic شده
                                                                                                        updated_at: updatedConv.updated_at
                                                                                                    }
                                                                                                    : c
                                                                                            );
                                                                                            
                                                                                            console.log('📝 Updated conversations (Agentic):', updated.map(c => ({ id: c.id, title: c.title, rag_type: c.rag_type })));
                                                                                            return updated;
                                                                                        });
                                                                                        
                                                                                        // به‌روزرسانی selectedConversation
                                                                                        setSelectedConversation(prev => {
                                                                                            if (!prev) return prev;
                                                                                            const updated = {
                                                                                                ...prev,
                                                                                                rag_type: (updatedConv.rag_type as 'simple' | 'agentic' | 'detailed') || 'agentic'
                                                                                            };
                                                                                            console.log('🎯 Updated selectedConversation (Agentic):', { 
                                                                                                old_rag_type: prev.rag_type,
                                                                                                new_rag_type: updated.rag_type
                                                                                            });
                                                                                            return updated;
                                                                                        });
                                                                                        
                                                                                        console.log('✅ Conversation upgraded to Agentic RAG');
                                                                                    } catch (error) {
                                                                                        console.error('❌ Failed to refresh Agentic conversation:', error);
                                                                                    }
                                                                                }, 300);
                                                                            } else {
                                                                                console.warn('⚠️ No selectedConversation available for Agentic refresh');
                                                                            }
                                                                        }
                                                                        
                                                                        if (evt.type === 'error') {
                                                                            setSelectedConversation(prev => {
                                                                                if (!prev) return prev;
                                                                                const updated = { ...prev };
                                                                                updated.messages = updated.messages.map(m =>
                                                                                    m.id === assistantTempId
                                                                                        ? {
                                                                                            ...m,
                                                                                            content: evt.error || 'خطایی رخ داد',
                                                                                            is_failed: true,
                                                                                            failure_reason: evt.error
                                                                                        }
                                                                                        : m
                                                                                );
                                                                                return updated;
                                                                            });
                                                                            setIsLoading(false);
                                                                            toast.error('خطا در دریافت توضیحات کامل');
                                                                        }
                                                                    },
                                                                    selectedModel,
                                                                    temperature
                                                                );
                                                            } catch (error: any) {
                                                                console.error('❌ Error getting more details:', error);
                                                                setSelectedConversation(prev => {
                                                                    if (!prev) return prev;
                                                                    const updated = { ...prev };
                                                                    updated.messages = updated.messages.map(m =>
                                                                        m.id === assistantTempId
                                                                            ? {
                                                                                ...m,
                                                                                content: error.message || 'خطایی رخ داد',
                                                                                is_failed: true,
                                                                                failure_reason: error.message
                                                                            }
                                                                            : m
                                                                    );
                                                                    return updated;
                                                                });
                                                                setIsLoading(false);
                                                                toast.error('خطا در دریافت توضیحات کامل');
                                                            }
                                                        }}
                                                        disabled={isLoading}
                                                        className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-all shadow-md hover:shadow-lg"
                                                    >
                                                        <Sparkles className="w-4 h-4" />
                                                        <span className="hidden md:inline">توضیحات کامل با Agentic RAG</span>
                                                        <span className="md:hidden">توضیحات کامل</span>
                                                    </button>
                                                </div>
                                            )}
                                            
                                            {/* Timestamp */}
                                            <p className={`text-xs text-gray-500 mt-2 ${message.role === 'user' ? 'text-right' : 'text-left'}`}>
                                                {formatTime(message.timestamp)}
                                            </p>
                                                    </div>
                                            </div>
                                        </div>
                                )
                            })}
                            <div ref={messagesEndRef} />
                        </>
                    )}
                </div>

                {/* Input Area */}
                {selectedConversation && (
                    <div className="bg-white border-t border-gray-200 p-3 md:p-4">
                        <div className="flex items-end gap-2">
                            <Button
                                onClick={handleSendMessage}
                                disabled={!newMessage.trim() || isLoading}
                                className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 h-10 w-10 md:h-12 md:w-12 rounded-xl flex items-center justify-center flex-shrink-0"
                            >
                                {isLoading ? (
                                    <div className="animate-spin rounded-full h-4 w-4 md:h-5 md:w-5 border-2 border-white border-t-transparent"></div>
                                ) : (
                                    <Send className="h-4 w-4 md:h-5 md:h-5" />
                                )}
                            </Button>
                            <VoiceInput
                                onTranscriptionComplete={(text) => {
                                    setNewMessage(prev => prev ? `${prev}\n${text}` : text)
                                }}
                                disabled={isLoading}
                            />
                            <div className="flex-1">
                                <Textarea
                                    value={newMessage}
                                    onChange={(e) => setNewMessage(e.target.value)}
                                    onKeyPress={handleKeyPress}
                                    placeholder="پیام خود را بنویسید..."
                                    className="resize-none min-h-[40px] max-h-[120px] text-sm md:text-base"
                                    rows={1}
                                    disabled={isLoading}
                                />
                            </div>
                        </div>
                        <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
                            <span className="hidden md:inline">Enter برای ارسال، Shift+Enter برای خط جدید</span>
                            <div className="flex items-center gap-1">
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
                            <MarkdownRenderer 
                                content={selectedArticle.content}
                                variant="default"
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
        </>
    )
}

export default SuperAdminChatPage
