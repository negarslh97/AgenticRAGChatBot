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
  Sparkles,
  Copy,
  Check,
  RotateCcw,
  AlertCircle,
  HelpCircle
} from 'lucide-react'
import { Button } from '../components/ui/button'
import { Textarea } from '../components/ui/textarea'
import { MarkdownRenderer } from '../components/ui/markdown-renderer'
import { VoiceInput } from '../components/ui/voice-input'
import { chatService } from '../services/chatService'
import { useAuth } from '../context/AuthContext'
import { toast } from 'react-hot-toast'
import ArticleHighlightModal from '../components/ArticleHighlightModal'
import BlackCatImage from '../assets/Black-Cat.png'

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
  ragType?: 'simple' | 'agentic' | 'detailed'  // 🔥 فیلد جدید برای ذخیره rag_type استخراج شده
}

interface Conversation {
  id: string
  title: string
  messages: Message[]
  created_at?: string
  updated_at?: string
  rag_type?: 'simple' | 'agentic' | 'detailed'
  type?: string // From backend API: "Simple RAG" or "Agentic"
}

type RAGType = 'simple' | 'agentic' | 'detailed'
type AdminRAGType = 'simple' | 'agentic'

// 🤖 Interface for model data
interface ModelInfo {
    id: string
    name: string
    provider: string
    description: string
    detailed_description?: string  // 🔥 توضیحات تفصیلی مدل
    category?: string
    speed?: string
    empty_chunks?: string
}

// 🔥 Fallback models list (used if API fails)
const FALLBACK_MODELS: ModelInfo[] = [
    {
        id: 'google/gemini-2.5-flash',
        name: '🏆 Gemini 2.5 Flash',
        provider: 'Google',
        description: '✅ سریع‌ترین - 264 ch/s، رایگان',
        detailed_description: 'سریع‌ترین مدل گوگل با سرعت 264 کاراکتر در ثانیه و رایگان.'
    },
    {
        id: 'qwen/qwen3-235b-a22b-2507',
        name: 'Qwen 3',
        provider: 'Alibaba',
        description: '✅ سریع‌ترین - 264 ch/s',
        detailed_description: 'مدل قدرتمند علی‌بابا با 235 میلیارد پارامتر و عملکرد عالی در فارسی.'
    },
    {
        id: 'minimax/minimax-m2:free',
        name: 'MINIMAX M2',
        provider: 'minimax',
        description: 'مدل جدید و قدرتمند Minimax',
        detailed_description: 'مدل جدید Minimax با تکنولوژی پیشرفته و عملکرد بالا در پردازش زبان طبیعی.'
    },
    {
        id: 'tngtech/deepseek-r1t2-chimera:free',
        name: '⭐ DeepSeek R1T2 Chimera (Free)',
        provider: 'DeepSeek',
        description: '✅ 117 ch/s، 0% empty، رایگان',
        detailed_description: 'مدل رایگان DeepSeek با سرعت 117 ch/s و بدون قطعات خالی.'
    },
    {
        id: 'gpt-4o-mini',
        name: '⭐ GPT-4o Mini',
        provider: 'OpenAI',
        description: '✅ 89 ch/s، پایدار، کیفیت بالا',
        detailed_description: 'نسخه بهینه‌شده GPT-4 با تعادل عالی بین سرعت و کیفیت. با سرعت 89 کاراکتر در ثانیه و پایداری بالا، تعادل مناسبی بین سرعت و کیفیت ارائه می‌دهد.'
    },
    {
        id: 'gpt-4o',
        name: 'GPT-4o',
        provider: 'OpenAI',
        description: 'قدرتمندترین OpenAI',
        detailed_description: 'قدرتمندترین مدل OpenAI با قابلیت‌های چندحالته و بالاترین کیفیت.'
    },
    {
        id: 'gpt-5-mini',
        name: '⭐ GPT-5 Mini',
        provider: 'OpenAI',
        description: 'جدیدترین و قدرتمندترین مدل OpenAI با تعادل عالی بین سرعت و کیفیت',
        detailed_description: 'نسخه بهینه‌شده GPT-5 جدیدترین و پیشرفته‌ترین مدل OpenAI با قابلیت‌های فوق‌العاده و کیفیت بالا در پاسخگویی.'
    },
    {
        id: 'gpt-5',
        name: '🏆 GPT-5',
        provider: 'OpenAI',
        description: 'جدیدترین و پیشرفته‌ترین مدل OpenAI',
        detailed_description: 'جدیدترین و پیشرفته‌ترین مدل OpenAI با بالاترین کیفیت، قابلیت‌های فوق‌العاده و تعامل طبیعی با کاربران.'
    },
    {
        id: 'x-ai/grok-4-fast',
        name: 'Grok 4 Fast ⚠️',
        provider: 'xAI',
        description: '143 ch/s، اما 70% empty chunks',
        detailed_description: 'سریع اما با 70% قطعات خالی که ممکن است بر کیفیت تأثیر بگذارد.'
    },
    {
        id: 'ollama:gpt-oss:20b',
        name: 'GPT-OSS 20B',
        provider: 'Ollama',
        description: 'مدل محلی OpenAI',
        detailed_description: 'مدل متن‌باز محلی با 20 میلیارد پارامتر و حریم خصوصی کامل.'
    },
    {
        id: 'ollama:gemma3n:e4b',
        name: 'Gemma 3N E4B',
        provider: 'Ollama',
        description: 'مدل محلی قدرتمند Google',
        detailed_description: 'نسخه بهینه‌شده Gemma گوگل برای اجرای محلی با مصرف منابع کم.'
    },
    {
        id: 'ollama:llama3.1:8b-instruct-q4_0',
        name: 'Llama 3.1 8B',
        provider: 'Ollama',
        description: 'مدل محلی Meta',
        detailed_description: 'جدیدترین مدل متن‌باز Meta با 8 میلیارد پارامتر و عملکرد بالا.'
    },
]

// 🔥 Elegant Skeleton Loader Component
const SkeletonLoader = () => (
  <div className="flex items-start space-x-2 space-x-reverse p-3">
    {/* Avatar Skeleton */}
    <div className="w-8 h-8 md:w-10 md:h-10 rounded-full shimmer dark:shimmer flex-shrink-0"></div>
    
    {/* Message Content Skeleton */}
    <div className="flex-1 space-y-2 min-w-0">
      {/* First line */}
      <div className="h-4 shimmer dark:shimmer rounded w-3/4 animate-pulse"></div>
      {/* Second line */}
      <div className="h-4 shimmer dark:shimmer rounded w-1/2 animate-pulse"></div>
      {/* Optional third line for longer content */}
      <div className="h-4 shimmer dark:shimmer rounded w-2/3 animate-pulse"></div>
    </div>
  </div>
)

const SuperAdminChatPage = () => {
    // 🔧 Feature Flags - برای مخفی کردن موقت برخی قابلیت‌ها
    const FEATURE_FLAGS = {
        SHOW_SETTINGS: true, // نمایش تنظیمات مدل و RAG
        SHOW_VOICE_INPUT: false // مخفی کردن ویس
    }

    const { user } = useAuth()
    const [isSidebarOpen, setIsSidebarOpen] = useState(false) // ✅ Default: closed on mobile
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false) // 🔥 New: Sidebar collapsed state
    const [conversations, setConversations] = useState<Conversation[]>([])
    const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)
    const [newMessage, setNewMessage] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [isInitialLoading, setIsInitialLoading] = useState(true)
    const [searchQuery, setSearchQuery] = useState('')
    const [modelSearchQuery, setModelSearchQuery] = useState('') // 🔍 Separate search for models
    const [ragType, setRagType] = useState<AdminRAGType>(() => {
        const saved = localStorage.getItem('superAdmin_ragType')
        return (saved as AdminRAGType) || 'simple'
    })
    const [selectedArticle, setSelectedArticle] = useState<{id: string, title: string, content: string} | null>(null)
    const [showSettingsModal, setShowSettingsModal] = useState(false)
    const [selectedModel, setSelectedModel] = useState<string>(() => {
        const saved = localStorage.getItem('superAdmin_selectedModel')
        return saved || 'google/gemini-2.5-flash'
    })
    const [availableModels, setAvailableModels] = useState<ModelInfo[]>(FALLBACK_MODELS)  // 🔥 Load models from API
    const [temperature, setTemperature] = useState<number>(() => {
        const saved = localStorage.getItem('superAdmin_temperature')
        return saved ? parseFloat(saved) : 0.7
    })
    const [isThinking, setIsThinking] = useState(false)  // 🔥 State for "thinking" indicator
    const [typewriterMessages, setTypewriterMessages] = useState<{[key: string]: string}>({})  // 🔥 Typewriter effect state
    const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null)  // 🔥 Copy feedback state
    const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)  // 🔥 Delete confirmation state
    const [showKeyboardShortcuts, setShowKeyboardShortcuts] = useState(false)  // 🔥 Keyboard shortcuts modal
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const messagesContainerRef = useRef<HTMLDivElement>(null)
    const initializationRef = useRef(false)
    const settingsModalRef = useRef<HTMLDivElement>(null)  // 🔥 Ref for settings modal focus
    const textareaRef = useRef<HTMLTextAreaElement>(null)  // 🔥 Ref for textarea auto-resize
    const conversationIdRef = useRef<string | undefined>(undefined)  // 🔥 Store conversation_id from init event
    const refreshInProgressRef = useRef<Set<string>>(new Set())  // 🔥 Track refresh operations to prevent duplicates
    const assistantTempIdRef = useRef<string>('')  // 🔥 Store assistantTempId in ref
    const streamingTimeoutsRef = useRef<{[key: string]: NodeJS.Timeout}>({})  // 🔥 Track streaming timeouts

    // Smart scroll state - using useRef for better performance
    const userHasScrolledUp = useRef(false)
    const [showGoToBottomBtn, setShowGoToBottomBtn] = useState(false)

    // 🔥 Article Highlight Modal state
    const [highlightModal, setHighlightModal] = useState<{
        isOpen: boolean;
        articleId: string;
        userQuery: string;
    }>({ isOpen: false, articleId: '', userQuery: '' })

    // 🔥 Define functions before useEffect to avoid hoisting issues
    const toggleSidebar = useCallback(() => {
        setIsSidebarOpen(prev => !prev)
    }, [])

    const createNewConversation = useCallback(() => {
        const newConv: Conversation = {
            id: `new-${Date.now()}`,
            title: 'گفتگوی جدید',
            messages: [],
            rag_type: ragType
        }
        setConversations(prev => [newConv, ...prev])
        setSelectedConversation(newConv)
    }, [ragType])

    // 🔥 Save settings to localStorage whenever they change
    useEffect(() => {
        localStorage.setItem('superAdmin_ragType', ragType)
    }, [ragType])

    useEffect(() => {
        localStorage.setItem('superAdmin_selectedModel', selectedModel)
    }, [selectedModel])

    useEffect(() => {
        localStorage.setItem('superAdmin_temperature', temperature.toString())
    }, [temperature])

    // 🔥 Keyboard shortcuts handler
    useEffect(() => {
        const handleKeyDown = (e: globalThis.KeyboardEvent) => {
            // Don't trigger shortcuts when typing in inputs
            if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
                return
            }

            // Ctrl/Cmd + B: Toggle sidebar
            if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
                e.preventDefault()
                toggleSidebar()
            }

            // Ctrl/Cmd + N: New conversation
            if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
                e.preventDefault()
                createNewConversation()
            }

            // Ctrl/Cmd + ,: Open settings (only if settings are enabled)
            if (FEATURE_FLAGS.SHOW_SETTINGS && (e.ctrlKey || e.metaKey) && e.key === ',') {
                e.preventDefault()
                setShowSettingsModal(true)
            }
        }

        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
        // FEATURE_FLAGS.SHOW_SETTINGS is a constant, no need to include in dependencies
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [toggleSidebar, createNewConversation, setShowSettingsModal])

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

    // 🔥 Focus management for settings modal
    useEffect(() => {
        if (showSettingsModal && FEATURE_FLAGS.SHOW_SETTINGS && settingsModalRef.current) {
            const firstInput = settingsModalRef.current.querySelector('button, input, select') as HTMLElement
            if (firstInput) {
                setTimeout(() => firstInput.focus(), 100)
            }
        }
    }, [showSettingsModal, FEATURE_FLAGS.SHOW_SETTINGS])

    // 🔥 Auto-resize textarea based on content
    useEffect(() => {
        if (textareaRef.current) {
            const textarea = textareaRef.current
            // Reset height to auto to get accurate scrollHeight
            textarea.style.height = 'auto'
            // Calculate new height (min: 40px, max: 200px)
            const scrollHeight = Math.min(textarea.scrollHeight, 200) // max-height: 200px
            const newHeight = scrollHeight > 40 ? scrollHeight : 40 // min-height: 40px
            textarea.style.height = `${newHeight}px`
            
            // Show scrollbar only if content exceeds max-height
            if (textarea.scrollHeight > 200) {
                textarea.style.overflowY = 'auto'
            } else {
                textarea.style.overflowY = 'hidden'
            }
        }
    }, [newMessage])

    // Development mode: API might not be available
    const isDevelopment = process.env.NODE_ENV === 'development'

    const scrollToBottom = useCallback(() => {
            // Only auto-scroll if user hasn't scrolled up
            if (!userHasScrolledUp.current && messagesContainerRef.current) {
                messagesContainerRef.current.scrollTo({
                    top: messagesContainerRef.current.scrollHeight,
                    behavior: 'smooth'
                })
            }
        }, [])
        
        // 🔥 Typewriter Cursor Component
        const TypewriterCursor = () => (
            <span className="inline-block w-2 h-4 bg-current animate-pulse ml-0.5"></span>
        )

        // 🔥 Gradual streaming function for typewriter effect
        const streamContentGradually = useCallback((messageId: string, content: string, delay: number = 30) => {
            // Clear any existing timeout for this message
            if (streamingTimeoutsRef.current[messageId]) {
                clearTimeout(streamingTimeoutsRef.current[messageId]);
            }

            let currentIndex = 0;
            const streamNext = () => {
                if (currentIndex < content.length) {
                    // Add next character
                    setTypewriterMessages(prev => ({
                        ...prev,
                        [messageId]: content.substring(0, currentIndex + 1)
                    }));
                    currentIndex++;
                    
                    // Schedule next character with variable delay for natural feel
                    const nextDelay = Math.random() * 20 + 20; // 20-40ms delay
                    streamingTimeoutsRef.current[messageId] = setTimeout(streamNext, nextDelay);
                } else {
                    // Cleanup timeout when done
                    delete streamingTimeoutsRef.current[messageId];
                }
            };
            
            // Start streaming
            streamNext();
        }, []);

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

    useEffect(() => {
        // Always auto-scroll smoothly when messages change, but respect user scroll preference
        if (!userHasScrolledUp.current) {
            setTimeout(() => scrollToBottom(), 100)
        }
    }, [selectedConversation?.messages])

    // 🔥 Cleanup streaming timeouts on unmount
    useEffect(() => {
        return () => {
            // Clear all streaming timeouts to prevent memory leaks
            Object.values(streamingTimeoutsRef.current).forEach(timeout => {
                clearTimeout(timeout);
            });
            streamingTimeoutsRef.current = {};
        };
    }, []);
    
    // 🔥 Toggle sidebar collapse/expand
    const toggleSidebarCollapse = () => {
        setIsSidebarCollapsed(!isSidebarCollapsed)
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
                rag_type: conv.type === 'Agentic' ? 'agentic' : 'simple', // Map backend type to rag_type
                model_name: conv.model_name,
                temperature: conv.temperature
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

    // 🔥 Load available models from API
    const loadAvailableModels = useCallback(async () => {
        try {
            const modelData = await chatService.getAvailableModels()
            
            // Convert API models to our format and merge with fallback data
            const formattedModels: ModelInfo[] = modelData.models.map(model => {
                // Find matching fallback model to get detailed_description, speed, and empty_chunks
                const fallbackModel = FALLBACK_MODELS.find(fm => fm.id === model.id)
                
                // 🔥 Detect provider based on model ID if provider is incorrect
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
                    provider: provider, // Use detected provider
                    description: model.description,
                    detailed_description: (model as any).detailed_description || fallbackModel?.detailed_description || model.description, // Use fallback detailed_description if available
                    category: model.category,
                    speed: model.speed || fallbackModel?.speed, // Use fallback speed if API doesn't provide it
                    empty_chunks: model.empty_chunks || fallbackModel?.empty_chunks // Use fallback empty_chunks if API doesn't provide it
                }
            })
            
            setAvailableModels(formattedModels)
            
            // Set default model if current selection is not available
            const defaultModel = modelData.default_model || 'google/gemini-2.5-flash'
            if (!formattedModels.find(m => m.id === selectedModel)) {
                setSelectedModel(defaultModel)
            }
        } catch (error: any) {
            console.error('Failed to load models from API, using fallback:', error)
            // Keep fallback models
            setAvailableModels(FALLBACK_MODELS)
        }
    }, [selectedModel])

    useEffect(() => {
        if (user?.id) {
            loadConversations()
            loadAvailableModels()  // 🔥 Load models from API
        }
    }, [user?.id, loadConversations, loadAvailableModels])

    const handleSendMessage = async () => {
        if (newMessage.trim() === '') return

        // 🔥 Auto-create conversation if none selected
        let currentConversation = selectedConversation
        if (!currentConversation) {
            const newConv: Conversation = {
                id: `new-${Date.now()}`,
                title: newMessage.trim().slice(0, 30) + (newMessage.trim().length > 30 ? '...' : ''),
                messages: [],
                rag_type: ragType
            }
            setConversations(prev => [newConv, ...prev])
            setSelectedConversation(newConv)
            currentConversation = newConv
        }

        setIsLoading(true)
        setIsThinking(true)  // 🔥 Start thinking state
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
                ...currentConversation,
                messages: [...currentConversation.messages, userMessage],
                title: currentConversation.messages.length === 0
                    ? messageContent.slice(0, 30) + (messageContent.length > 30 ? '...' : '')
                    : currentConversation.title,
                rag_type: ragType
            }

            setSelectedConversation(tempConversation)
            setNewMessage('')

            // 🔥 استفاده از streaming API برای admin
            const assistantTempId = `ai-temp-${Date.now()}`;
            assistantTempIdRef.current = assistantTempId;  // 🔥 Store in ref
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

            const currentConvId = currentConversation.id.startsWith('new-') ? undefined : currentConversation.id;
            const currentConvTempId = currentConversation.id; // 🔥 Store temp ID for callback use
            conversationIdRef.current = undefined; // 🔥 Reset for this message
            
            // 🔥 Initialize typewriterMessages for the new assistant message
            setTypewriterMessages(prev => ({
                ...prev,
                [assistantTempId]: ''
            }));

            await chatService.sendAdminMessageStream(
                            currentConvId,
                            messageContent,
                            ragType,
                            (evt: any) => {
                                if (!evt) return;
            
                                if (evt.type === 'init') {
                                    // Set conversation ID if it was a new chat
                                    if (evt.conversation_id) {
                                        conversationIdRef.current = evt.conversation_id; // 🔥 Store for later use
                                        if (!currentConvId) {
                                            setConversations(prev =>
                                                prev.map(conv =>
                                                    conv.id === currentConvTempId
                                                        ? { ...conv, id: evt.conversation_id }
                                                        : conv
                                                )
                                            );
                                            setSelectedConversation(prev => prev ? ({ ...prev, id: evt.conversation_id }) : prev);
                                        }
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
                                    // 🔥 Hide thinking indicator when first chunk arrives
                                    setIsThinking(false);
                                    
                                    setSelectedConversation(prev => {
                                        if (!prev) return prev;
                                        const updated = { ...prev };
                                        const currentMessage = updated.messages.find(m => m.id === assistantTempId);
                                        
                                        if (currentMessage) {
                                            // Accumulate content from chunks
                                            const newContent = (currentMessage.content || '') + (evt.content || '');
                                            
                                            // 🔥 Real-time streaming: Use gradual streaming for typewriter effect
                                            if (evt.content) {
                                                streamContentGradually(assistantTempId, newContent);
                                            }
                                            
                                            // Update message content
                                            updated.messages = updated.messages.map(m =>
                                                m.id === assistantTempId
                                                    ? { ...m, content: newContent }
                                                    : m
                                            );
                                        }
                                        return updated;
                                    });
                                    
                                    // Auto-scroll to bottom during streaming
                                    setTimeout(() => scrollToBottom(), 50);
                                }
            
                                if (evt.type === 'complete') {
                                    setSelectedConversation(prev => {
                                        if (!prev) return prev;
                                        const updated = { ...prev };
                                        const finalContent = evt.full_response || updated.messages.find(m => m.id === assistantTempId)?.content || '';
                                        
                                        // 🔥 Update typewriterMessages with final content only if streaming hasn't completed
                                        setTypewriterMessages(prev => {
                                            const currentContent = prev[assistantTempId] || '';
                                            // Only update if current content is less than final content (streaming in progress)
                                            if (currentContent.length < finalContent.length) {
                                                return {
                                                    ...prev,
                                                    [assistantTempId]: finalContent
                                                };
                                            }
                                            return prev; // Keep current content to preserve typing effect
                                        });
                                        
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
                                        );
                                        return updated;
                                    });
                                    setIsLoading(false);
                                    
                                    // 🔥 Refresh conversations list after completion
                                    // Use conversation_id from complete event, or from init event (stored in ref), or currentConvId
                                    const finalConvId = evt.conversation_id || conversationIdRef.current || currentConvId;
                                    
                                    if (finalConvId) {
                                        // 🔥 Prevent duplicate refresh calls using ref
                                        if (refreshInProgressRef.current.has(finalConvId)) {
                                            return;
                                        }
                                        
                                        refreshInProgressRef.current.add(finalConvId);
                                        
                                        setTimeout(async () => {
                                            try {
                                                const updatedConv = await chatService.getConversation(finalConvId);
                                                
                                                // 🔥 Update both conversations list and selectedConversation in a single batch
                                                setConversations((prev: Conversation[]) => {
                                                    const exists = prev.some(c => c.id === finalConvId);
                                                    
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
                                                        );
                                                        return updated;
                                                    } else {
                                                        return [...prev, {
                                                            id: finalConvId,
                                                            title: updatedConv.title || 'مکالمه جدید',
                                                            rag_type: evt.rag_type,
                                                            created_at: updatedConv.created_at,
                                                            updated_at: updatedConv.updated_at,
                                                            tags: updatedConv.tags || [],
                                                            messages: [] // Add required messages property
                                                        }];
                                                    }
                                                });
                                                
                                                // Update selectedConversation
                                                setSelectedConversation(prev => {
                                                    if (!prev) return prev;
                                                    // Only update if this is the current conversation
                                                    if (prev.id === finalConvId || prev.id === currentConvTempId) {
                                                        const updated = {
                                                            ...prev,
                                                            id: finalConvId, // Ensure we use the final ID
                                                            title: updatedConv.title || prev.title,
                                                            rag_type: updatedConv.rag_type || evt.rag_type
                                                        };
                                                        return updated;
                                                    }
                                                    return prev;
                                                });
                                                
                                                // Remove from in-progress set after completion
                                                refreshInProgressRef.current.delete(finalConvId);
                                            } catch (error) {
                                                console.error('❌ Failed to refresh conversation:', error);
                                                // Remove from in-progress set on error
                                                refreshInProgressRef.current.delete(finalConvId);
                                            }
                                        }, 500);
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
        } finally {
            setIsLoading(false)
            setIsThinking(false)  // 🔥 Always stop thinking state
        }
    }

    const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSendMessage()
        }
    }

    const deleteConversation = async (convId: string) => {
        // 🔥 Show confirmation first
        if (deleteConfirmId !== convId) {
            setDeleteConfirmId(convId)
            return
        }

        // Reset confirmation state
        setDeleteConfirmId(null)

        if (convId.startsWith('new-')) {
            // Just remove from local state if it's a new conversation
            setConversations(prev => prev.filter(c => c.id !== convId))
            if (selectedConversation?.id === convId) {
                setSelectedConversation(null)
            }
            toast.success('گفتگو حذف شد')
            return
        }

        try {
            // Try to delete from API, but if it fails (405), just delete locally
            try {
                await chatService.deleteConversation(convId)
            } catch (apiError: any) {
                // If API doesn't support DELETE (405 Method Not Allowed), just delete locally
                if (apiError.response?.status === 405) {
                    console.warn('Delete conversation endpoint not available, deleting locally only')
                } else {
                    throw apiError // Re-throw other errors
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

    // 🔥 Copy message to clipboard
    const copyMessage = async (content: string, messageId: string) => {
        try {
            await navigator.clipboard.writeText(content)
            setCopiedMessageId(messageId)
            toast.success('پیام کپی شد')
            setTimeout(() => setCopiedMessageId(null), 2000)
        } catch (error) {
            console.error('Failed to copy message:', error)
            toast.error('خطا در کپی پیام')
        }
    }

    // 🔥 Retry failed message
    const retryMessage = async (messageId: string) => {
        if (!selectedConversation) return
        
        const message = selectedConversation.messages.find(m => m.id === messageId)
        if (!message || message.role !== 'user') return

        // Find the previous user message
        const messageIndex = selectedConversation.messages.findIndex(m => m.id === messageId)
        const userMessage = messageIndex >= 0 ? selectedConversation.messages[messageIndex] : null
        
        if (!userMessage || userMessage.role !== 'user') return

        // Remove the failed assistant message if exists
        const failedAssistantIndex = messageIndex + 1
        if (failedAssistantIndex < selectedConversation.messages.length) {
            const updatedMessages = selectedConversation.messages.filter((_, idx) => idx !== failedAssistantIndex)
            setSelectedConversation({ ...selectedConversation, messages: updatedMessages })
        }

        // Resend the message
        setNewMessage(userMessage.content)
        setTimeout(() => {
            handleSendMessage()
        }, 100)
    }

    const loadConversationMessages = async (conversationId: string) => {
        try {
            const messages = await chatService.getConversationMessages(conversationId)
            
            // Assume 'apiResponse.messages' is the array of messages received from the API.
            // In our case, messages is the array from the API response
            
            // Step A: Map the incoming API data to the structure needed for the state.
            // This MUST explicitly extract `rag_type` from the metadata.
            const processedMessages = messages.map(msg => ({
                id: msg.id,
                content: msg.content,
                role: msg.sender_type === 'AI' ? ('assistant' as const) : ('user' as const),
                timestamp: new Date(msg.created_at),
                sender_type: msg.sender_type as any,
                is_failed: msg.is_failed,
                failure_reason: msg.failure_reason,
                rating: msg.rating,
                metadata: msg.metadata,
                sources: msg.metadata?.sources || [],
                confidence: msg.metadata?.confidence,
                suggested_actions: msg.metadata?.suggested_actions || [],
                ragType: msg.metadata?.rag_type || 'simple' // Add ragType field
            }));

            // Step B: *** THIS IS THE MOST IMPORTANT STEP ***
            // Add this exact console.log to print the processed data.
            console.log('--- RAG TYPE DIAGNOSTIC DATA ---', processedMessages);

            // Step C: Update the state with the processed data.
            // Update the selected conversation with messages
            setSelectedConversation(prev => prev ? {
                ...prev,
                messages: processedMessages
            } : null)

            // Also update in conversations list
            setConversations(prev =>
                prev.map(conv =>
                    conv.id === conversationId
                        ? { ...conv, messages: processedMessages }
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
        
        // 🔥 Load conversation details to get model_name and temperature
        try {
            const convDetails = await chatService.getConversation(conversation.id)
            if (convDetails.model_name) {
                setSelectedModel(convDetails.model_name)
            }
            if (convDetails.temperature !== undefined) {
                setTemperature(convDetails.temperature)
            }
            if (convDetails.rag_type) {
                setRagType(convDetails.rag_type as AdminRAGType)
            }
        } catch (error) {
            console.error('Failed to load conversation details:', error)
        }
        
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
            
            {/* 🔥 Keyboard Shortcuts Modal */}
            {showKeyboardShortcuts && (
                <div 
                    className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" 
                    onClick={() => setShowKeyboardShortcuts(false)}
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="shortcuts-modal-title"
                >
                    <div 
                        className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-y-auto" 
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="sticky top-0 bg-gradient-to-r from-purple-600 to-blue-600 text-white p-6 rounded-t-2xl">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <HelpCircle className="w-6 h-6" />
                                    <h2 id="shortcuts-modal-title" className="text-xl font-bold">راهنمای کیبورد شورتکات</h2>
                                </div>
                                <button
                                    onClick={() => setShowKeyboardShortcuts(false)}
                                    className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                                    aria-label="بستن راهنما"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                        </div>
                        <div className="p-6 space-y-4">
                            <div className="space-y-3">
                                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                    <span className="text-sm text-gray-700">ارسال پیام</span>
                                    <kbd className="px-2 py-1 bg-white border border-gray-300 rounded text-xs font-mono">Enter</kbd>
                                </div>
                                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                    <span className="text-sm text-gray-700">خط جدید</span>
                                    <kbd className="px-2 py-1 bg-white border border-gray-300 rounded text-xs font-mono">Shift + Enter</kbd>
                                </div>
                                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                    <span className="text-sm text-gray-700">باز/بستن سایدبار</span>
                                    <kbd className="px-2 py-1 bg-white border border-gray-300 rounded text-xs font-mono">Ctrl + B</kbd>
                                </div>
                                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                    <span className="text-sm text-gray-700">گفتگوی جدید</span>
                                    <kbd className="px-2 py-1 bg-white border border-gray-300 rounded text-xs font-mono">Ctrl + N</kbd>
                                </div>
                                {/* 🔧 Settings shortcut - به صورت موقت مخفی شده */}
                                {FEATURE_FLAGS.SHOW_SETTINGS && (
                                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                        <span className="text-sm text-gray-700">باز کردن تنظیمات</span>
                                        <kbd className="px-2 py-1 bg-white border border-gray-300 rounded text-xs font-mono">Ctrl + ,</kbd>
                                    </div>
                                )}
                            </div>
                        </div>
                        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 p-4 rounded-b-2xl">
                            <Button
                                onClick={() => setShowKeyboardShortcuts(false)}
                                className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
                            >
                                بستن
                            </Button>
                        </div>
                    </div>
                </div>
            )}
            
            {/* 🔧 ⚙️ Settings Modal - به صورت موقت مخفی شده */}
            {FEATURE_FLAGS.SHOW_SETTINGS && showSettingsModal && (
                <div 
                    className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" 
                    onClick={() => setShowSettingsModal(false)}
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="settings-modal-title"
                >
                    <div 
                        ref={settingsModalRef}
                        className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[92vh] overflow-y-auto overflow-x-hidden flex flex-col" 
                        onClick={(e) => e.stopPropagation()}
                        tabIndex={-1}
                    >
                {/* Header */}
                        <div className="sticky top-0 bg-gradient-to-r from-purple-600 to-blue-600 text-white p-4 md:p-6 rounded-t-2xl z-10">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2 md:gap-3">
                                    <Settings className="w-5 h-5 md:w-6 md:h-6" />
                                    <h2 id="settings-modal-title" className="text-lg md:text-xl font-bold">تنظیمات پیشرفته چت</h2>
                                </div>
                                <button
                                    onClick={() => setShowSettingsModal(false)}
                                    className="p-1.5 md:p-2 hover:bg-white/20 rounded-lg transition-colors"
                                    aria-label="بستن تنظیمات"
                                >
                                    <X className="w-4 h-4 md:w-5 md:h-5" />
                                </button>
                            </div>
                    </div>

                        {/* Content */}
                        <div className="p-4 md:p-6 space-y-5 md:space-y-6 overflow-x-hidden flex-1">
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

                            {/* Model Selection - 🎨 Improved UI */}
                            <div>
                                <label className="block text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                                    <Cpu className="w-4 h-4 text-purple-600" />
                                    انتخاب مدل هوش مصنوعی
                                </label>
                                
                                {/* Search Box */}
                                <div className="mb-3">
                                    <div className="relative">
                                        <Search className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                                        <input
                                            type="text"
                                            placeholder="جستجو در مدل‌ها..."
                                            value={modelSearchQuery}
                                            onChange={(e) => setModelSearchQuery(e.target.value)}
                                            className="w-full pr-10 pl-4 py-2.5 md:py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
                                        />
                                    </div>
                                </div>

                                {/* Models Grid */}
                                <div className="grid grid-cols-1 gap-2.5 md:gap-3 max-h-[280px] md:max-h-[300px] overflow-y-auto overflow-x-hidden p-0.5 md:p-1 scrollbar-thin scrollbar-thumb-purple-200 scrollbar-track-gray-100">
                                    {availableModels
                                        .filter(model => 
                                            !modelSearchQuery || 
                                            model.name.toLowerCase().includes(modelSearchQuery.toLowerCase()) ||
                                            model.provider.toLowerCase().includes(modelSearchQuery.toLowerCase()) ||
                                            model.description.toLowerCase().includes(modelSearchQuery.toLowerCase()) ||
                                            (model.detailed_description && model.detailed_description.toLowerCase().includes(modelSearchQuery.toLowerCase()))
                                        )
                                        .map((model) => {
                                            const isSelected = selectedModel === model.id
                                            const getProviderColor = (provider: string) => {
                                                const providerLower = provider.toLowerCase().trim()
                                                switch(providerLower) {
                                                    case 'ollama': return 'bg-orange-100 text-orange-800 border-orange-300'
                                                    case 'openai': return 'bg-blue-100 text-blue-800 border-blue-300'
                                                    case 'openrouter': return 'bg-violet-100 text-violet-800 border-violet-300'
                                                    default: return 'bg-slate-100 text-slate-700 border-slate-300'
                                                }
                                            }
                                            
                                            return (
                                                <button
                                                    key={model.id}
                                                    onClick={() => setSelectedModel(model.id)}
                                                    className={`group relative p-3 md:p-4 rounded-lg md:rounded-xl border-2 transition-all duration-200 text-right w-full ${
                                                        isSelected
                                                            ? 'border-purple-500 bg-gradient-to-br from-purple-50 via-blue-50 to-purple-50 shadow-md shadow-purple-200/40 ring-2 ring-purple-200 ring-offset-1'
                                                            : 'border-gray-200 bg-white hover:border-purple-300 hover:bg-gradient-to-br hover:from-gray-50 hover:to-purple-50/30 hover:shadow-sm'
                                                    }`}
                                                >
                                                    {/* Selected Indicator */}
                                                    {isSelected && (
                                                        <div className="absolute top-2.5 left-2.5 flex flex-col items-center gap-1 z-10">
                                                            <div className="w-5 h-5 md:w-6 md:h-6 bg-gradient-to-br from-purple-600 to-blue-600 rounded-full flex items-center justify-center shadow-sm">
                                                                <Check className="w-3 h-3 md:w-4 md:h-4 text-white" />
                                                            </div>
                                                            <span className={`text-[9px] md:text-[10px] font-medium px-1.5 py-0.5 rounded-md whitespace-nowrap ${
                                                                getProviderColor(model.provider)
                                                            }`}>
                                                                {model.provider}
                                                            </span>
                                                        </div>
                                                    )}
                                                    
                                                    <div className="flex items-start justify-between gap-2.5 md:gap-3 pr-0.5 md:pr-1">
                                                        <div className="flex-1 min-w-0 overflow-hidden">
                                                            {/* Model Name and Provider */}
                                                            <div className="flex items-center gap-1.5 md:gap-2 mb-1.5 md:mb-2 flex-wrap">
                                                                <div className="flex items-center gap-1.5 md:gap-2 flex-1 min-w-0">
                                                                    <Bot className={`w-3.5 h-3.5 md:w-4 md:h-4 flex-shrink-0 ${
                                                                        isSelected ? 'text-purple-600' : 'text-gray-400'
                                                                    }`} />
                                                                    <span className={`font-bold text-sm md:text-base break-words leading-tight ${
                                                                        isSelected ? 'text-purple-900' : 'text-gray-900'
                                                                    }`}>
                                                                        {model.name}
                                                                    </span>
                                                                </div>
                                                                {!isSelected && (
                                                                    <span className={`text-[10px] md:text-xs px-2 md:px-2.5 py-0.5 md:py-1 rounded-full font-medium border flex-shrink-0 ${
                                                                        getProviderColor(model.provider)
                                                                    }`}>
                                                                        {model.provider}
                                                                    </span>
                                                                )}
                                                            </div>
                                                            
                                                            {/* Description */}
                                                            {/* {model.description && (
                                                                <p className={`text-[11px] md:text-xs mb-1.5 md:mb-2 break-words leading-relaxed ${
                                                                    isSelected ? 'text-gray-700' : 'text-gray-600'
                                                                }`}>
                                                                    {model.description}
                                                                </p>
                                                            )} */}
                                                            
                                                            {/* Detailed Description */}
                                                            {model.detailed_description && (
                                                                <div className={`mt-2 pt-2 border-t border-gray-200 ${isSelected ? 'border-purple-200' : ''}`}>
                                                                    <div className="flex items-start gap-1.5 md:gap-2">
                                                                        <Sparkles className={`w-3 h-3 md:w-3.5 md:h-3.5 mt-0.5 flex-shrink-0 ${
                                                                            isSelected ? 'text-purple-500' : 'text-gray-400'
                                                                        }`} />
                                                                        <p className={`text-[10px] md:text-xs break-words leading-relaxed flex-1 ${
                                                                            isSelected ? 'text-gray-600' : 'text-gray-500'
                                                                        }`}>
                                                                            {model.detailed_description}
                                                                        </p>
                                                                    </div>
                                                                </div>
                                                            )}
                                                            
                                                            {/* Speed and Empty Chunks Info */}
                                                            {((model.speed && model.speed !== 'N/A' && model.speed.trim() !== '') || 
                                                              (model.empty_chunks && model.empty_chunks !== 'N/A' && model.empty_chunks.trim() !== '')) && (
                                                                <div className="flex items-center gap-2 md:gap-3 mt-1.5 md:mt-2 flex-wrap">
                                                                    {model.speed && model.speed !== 'N/A' && model.speed.trim() !== '' && (
                                                                        <div className="flex items-center gap-1">
                                                                            <Zap className="w-2.5 h-2.5 md:w-3 md:h-3 text-yellow-500" />
                                                                            <span className="text-[10px] md:text-xs text-gray-600">{model.speed}</span>
                                                                        </div>
                                                                    )}
                                                                    {model.empty_chunks && model.empty_chunks !== 'N/A' && model.empty_chunks.trim() !== '' && (
                                                                        <div className="flex items-center gap-1">
                                                                            <AlertCircle className={`w-2.5 h-2.5 md:w-3 md:h-3 ${
                                                                                model.empty_chunks.includes('0%') ? 'text-green-500' : 'text-orange-500'
                                                                            }`} />
                                                                            <span className={`text-[10px] md:text-xs ${
                                                                                model.empty_chunks.includes('0%') ? 'text-green-600' : 'text-orange-600'
                                                                            }`}>
                                                                                {model.empty_chunks}
                                                                            </span>
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            )}
                                                        </div>
                                                        
                                                        {/* Radio Button Indicator */}
                                                        {!isSelected && (
                                                            <div className="w-4 h-4 md:w-5 md:h-5 border-2 border-gray-300 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 group-hover:border-purple-400 transition-colors">
                                                                <div className="w-1.5 h-1.5 md:w-2 md:h-2 bg-transparent rounded-full group-hover:bg-purple-400 transition-colors" />
                                                            </div>
                                                        )}
                                                    </div>
                                                </button>
                                            )
                                        })}
                                </div>
                                
                                {/* Empty State */}
                                {availableModels.filter(model => 
                                    !modelSearchQuery || 
                                    model.name.toLowerCase().includes(modelSearchQuery.toLowerCase()) ||
                                    model.provider.toLowerCase().includes(modelSearchQuery.toLowerCase()) ||
                                    model.description.toLowerCase().includes(modelSearchQuery.toLowerCase()) ||
                                    (model.detailed_description && model.detailed_description.toLowerCase().includes(modelSearchQuery.toLowerCase()))
                                ).length === 0 && (
                                    <div className="text-center py-8 text-gray-500">
                                        <AlertCircle className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                                        <p className="text-sm">مدلی یافت نشد</p>
                                    </div>
                                )}
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
                                        <span className="font-bold text-purple-900" title={(() => {
                                            const modelInfo = availableModels.find(m => m.id === selectedModel);
                                            return modelInfo?.detailed_description || modelInfo?.description || selectedModel;
                                        })()}>
                                            {(() => {
                                                const modelInfo = availableModels.find(m => m.id === selectedModel);
                                                if (modelInfo) {
                                                    return `${modelInfo.name} (${modelInfo.provider})`;
                                                }
                                                return selectedModel;
                                            })()}
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
                        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 p-3 md:p-4 rounded-b-2xl flex gap-2 md:gap-3 z-10">
                            <Button
                                onClick={() => setShowSettingsModal(false)}
                                variant="secondary"
                                className="flex-1 text-sm md:text-base"
                            >
                                بستن
                            </Button>
                            <Button
                                onClick={() => {
                                    setShowSettingsModal(false)
                                    // تنظیمات ذخیره می‌شوند و در ارسال پیام بعدی استفاده می‌شوند
                                }}
                                className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-sm md:text-base"
                            >
                                ✅ ذخیره تنظیمات
                            </Button>
                        </div>
                    </div>
                </div>
            )}
            
            <div className="flex bg-gray-50 h-[calc(100vh-170px)] relative">
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
                ${isSidebarOpen ? (isSidebarCollapsed ? 'lg:w-16' : 'lg:w-80') : 'lg:w-0'}
                transition-all duration-300
                bg-white border-l border-gray-200
                flex flex-col overflow-hidden
                top-0 right-0
            `}>
                {/* Header */}
                <div className="p-4 border-b border-gray-200">
                    <div className="flex items-center justify-between mb-4">
                        {/* 🔥 Show title only when not collapsed */}
                        {!isSidebarCollapsed && (
                            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                                <Brain className="w-5 h-5 text-purple-600" />
                                چت ادمین ارشد
                            </h2>
                        )}
                        
                        <div className="flex items-center gap-1">
                            {/* 🔥 Collapse/Expand Toggle Button */}
                            <Button
                                onClick={toggleSidebarCollapse}
                                size="sm"
                                variant="ghost"
                                className="p-1.5 hover:bg-gray-100"
                                title={isSidebarCollapsed ? 'باز کردن سایدبار' : 'جمع کردن سایدبار'}
                            >
                                <ChevronLeft className={`w-4 h-4 transition-transform duration-200 ${isSidebarCollapsed ? 'rotate-180' : ''}`} />
                            </Button>
                            
                            {/* Close button for mobile */}
                            <Button
                                onClick={toggleSidebar}
                                size="sm"
                                variant="ghost"
                                className="lg:hidden"
                            >
                                <X className="w-5 h-5" />
                            </Button>
                        </div>
                    </div>
                    
                    {/* 🔥 Show buttons only when not collapsed */}
                    {!isSidebarCollapsed && (
                        <>
                            {/* New Chat Button */}
                            <Button
                                onClick={createNewConversation}
                                className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white shadow-md mb-3"
                                aria-label="ایجاد گفتگوی جدید"
                            >
                                <Plus className="w-4 h-4 mr-2" />
                                گفتگوی جدید
                            </Button>

                            {/* 🔧 Settings Button - به صورت موقت مخفی شده */}
                            {FEATURE_FLAGS.SHOW_SETTINGS && (
                                <>
                                    <Button
                                        onClick={() => setShowSettingsModal(true)}
                                        variant="secondary"
                                        className="w-full mb-4 flex items-center justify-center gap-2"
                                        aria-label="باز کردن تنظیمات پیشرفته"
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
                                                <span className="font-bold text-purple-700" title={(() => {
                                                    const modelInfo = availableModels.find(m => m.id === selectedModel);
                                                    return modelInfo?.detailed_description || modelInfo?.description || 'GPT-4o Mini';
                                                })()}>
                                                    {availableModels.find(m => m.id === selectedModel)?.name || 'GPT-4o Mini'}
                                                </span>
                                            </div>
                                            <div className="flex items-center justify-between">
                                                <span>Temperature:</span>
                                                <span className="font-bold text-purple-700">{temperature.toFixed(1)}</span>
                                            </div>
                                        </div>
                                    </div>
                                </>
                            )}

                            {/* Search */}
                            <div className="relative">
                                <Search className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                                <input
                                    type="text"
                                    placeholder="جستجو در گفتگوها..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="w-full pr-10 pl-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                                    aria-label="جستجو در گفتگوها"
                                />
                            </div>
                        </>
                    )}
                </div>

                {/* 🔥 Conversations List - Only show when not collapsed */}
                {!isSidebarCollapsed && (
                    <div className="conversation-list flex-1 overflow-y-auto">
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
                                    className={`conversation-item group p-3 border-b border-gray-100 cursor-pointer transition-all pointer-events-auto ${
                                        selectedConversation?.id === conversation.id
                                            ? 'bg-gradient-to-r from-purple-50 to-blue-50 border-r-4 border-r-purple-500'
                                            : 'hover:bg-gray-50'
                                    }`}
                                    onClick={() => handleConversationClick(conversation)}
                                >
                                    <div className="flex items-start justify-between gap-2">
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <div className={`w-6 h-6 rounded-full flex items-center justify-center overflow-hidden ${
                                                    conversation.rag_type === 'agentic'
                                                        ? 'bg-gradient-to-r from-purple-100 to-blue-100'
                                                        : 'bg-blue-100'
                                                }`}>
                                                    <img
                                                        src={BlackCatImage}
                                                        alt="AI Assistant"
                                                        className="w-full h-full object-cover"
                                                        onError={(e) => {
                                                            e.currentTarget.style.display = 'none';
                                                            const nextElement = e.currentTarget.nextElementSibling as HTMLElement;
                                                            if (nextElement) {
                                                                nextElement.style.display = 'block';
                                                            }
                                                        }}
                                                    />
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
                                                    <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded truncate max-w-[120px]" title={(() => {
                                                        const modelInfo = availableModels.find(m => m.id === conversation.messages[conversation.messages.length - 1].model);
                                                        return modelInfo?.detailed_description || modelInfo?.description || conversation.messages[conversation.messages.length - 1].model;
                                                    })()}>
                                                        {(() => {
                                                            const modelInfo = availableModels.find(m => m.id === conversation.messages[conversation.messages.length - 1].model);
                                                            if (modelInfo) {
                                                                return `${modelInfo.name} (${modelInfo.provider})`;
                                                            }
                                                            return conversation.messages[conversation.messages.length - 1].model?.split('/').pop() || 'مدل نامشخص';
                                                        })()}
                                                    </span>
                                                )}
                                            </div>
                                            {conversation.messages.length > 0 && (
                                                <p className="text-xs text-gray-500 truncate">
                                                    {conversation.messages[conversation.messages.length - 1].content}
                                                </p>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-1">
                                            {deleteConfirmId === conversation.id ? (
                                                <>
                                                    <Button
                                                        onClick={(e) => {
                                                            e.stopPropagation()
                                                            deleteConversation(conversation.id)
                                                        }}
                                                        variant="ghost"
                                                        size="sm"
                                                        className="text-red-600 hover:text-red-700 hover:bg-red-50 p-1"
                                                        aria-label="تأیید حذف"
                                                    >
                                                        <Check className="w-4 h-4" />
                                                    </Button>
                                                    <Button
                                                        onClick={(e) => {
                                                            e.stopPropagation()
                                                            setDeleteConfirmId(null)
                                                        }}
                                                        variant="ghost"
                                                        size="sm"
                                                        className="text-gray-600 hover:text-gray-700 p-1"
                                                        aria-label="لغو حذف"
                                                    >
                                                        <X className="w-4 h-4" />
                                                    </Button>
                                                </>
                                            ) : (
                                                <Button
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        deleteConversation(conversation.id)
                                                    }}
                                                    variant="ghost"
                                                    size="sm"
                                                    className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-red-500 p-1"
                                                    aria-label="حذف گفتگو"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </Button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                )}
                
                {/* 🔥 Collapsed State - Show minimal info or just icons */}
                {isSidebarCollapsed && (
                    <div className="conversation-list flex-1 overflow-y-auto p-2 space-y-2">
                        {filteredConversations.slice(0, 5).map((conversation) => (
                            <button
                                key={conversation.id}
                                onClick={() => handleConversationClick(conversation)}
                                className={`conversation-item w-full p-2 rounded-lg transition-all pointer-events-auto ${
                                    selectedConversation?.id === conversation.id
                                        ? 'bg-purple-100 border-r-2 border-purple-500'
                                        : 'hover:bg-gray-100'
                                }`}
                                title={conversation.title}
                            >
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center mx-auto overflow-hidden relative ${
                                    conversation.rag_type === 'agentic'
                                        ? 'bg-gradient-to-r from-purple-100 to-blue-100'
                                        : 'bg-blue-100'
                                }`}>
                                    <img
                                        src={BlackCatImage}
                                        alt="AI Assistant"
                                        className="w-full h-full object-cover"
                                        onError={(e) => {
                                            e.currentTarget.style.display = 'none';
                                            const nextElement = e.currentTarget.nextElementSibling as HTMLElement;
                                            if (nextElement) {
                                                nextElement.style.display = 'block';
                                            }
                                        }}
                                    />
                                </div>
                            </button>
                        ))}
                        {filteredConversations.length > 5 && (
                            <div className="text-xs text-gray-400 text-center p-2">
                                +{filteredConversations.length - 5} more
                            </div>
                        )}
                    </div>
                )}
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
                                aria-label="باز/بستن منوی گفتگوها"
                            >
                                <Menu className="w-5 h-5" />
                            </Button>
                            
                            {/* Desktop Toggle */}
                            <Button
                                onClick={toggleSidebar}
                                variant="ghost"
                                size="sm"
                                className="hidden lg:flex text-white hover:bg-white/20"
                                aria-label={isSidebarOpen ? "بستن سایدبار" : "باز کردن سایدبار"}
                            >
                                {isSidebarOpen ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
                            </Button>
                            
                            {/* Title */}
                            <div className="flex items-center gap-2 min-w-0 flex-1">
                                <div className="w-8 h-8 md:w-10 md:h-10 bg-white/20 rounded-full flex items-center justify-center flex-shrink-0 overflow-hidden">
                                    <img
                                        src={BlackCatImage}
                                        alt="AI Assistant"
                                        className="w-full h-full object-cover"
                                        onError={(e) => {
                                            e.currentTarget.style.display = 'none';
                                            const nextElement = e.currentTarget.nextElementSibling as HTMLElement;
                                            if (nextElement) {
                                                nextElement.style.display = 'block';
                                            }
                                        }}
                                    />
                                    <Bot className="w-4 h-4 md:w-5 md:h-5 text-white hidden" />
                                </div>
                                <div className="min-w-0 flex-1">
                                    <h1 className="text-sm md:text-lg font-bold truncate">
                                        {selectedConversation?.title || 'گفتگوی جدید'}
                                    </h1>
                                    <div className="flex items-center gap-1 text-xs md:text-sm text-white/90">
                                        {getRagTypeIcon(ragType)}
                                        <span>{getRagTypeLabel(ragType)}</span>
                                        <span className="hidden md:inline">•</span>
                                        <span className="hidden md:inline" title={(() => {
                                            const modelInfo = availableModels.find((m: ModelInfo) => m.id === selectedModel);
                                            return modelInfo?.detailed_description || modelInfo?.description || 'GPT-4o Mini';
                                        })()}>
                                            {availableModels.find((m: ModelInfo) => m.id === selectedModel)?.name || 'GPT-4o Mini'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        {/* 🔧 Settings Button - به صورت موقت مخفی شده */}
                        {FEATURE_FLAGS.SHOW_SETTINGS && (
                            <Button
                                onClick={() => setShowSettingsModal(true)}
                                variant="ghost"
                                size="sm"
                                className="text-white hover:bg-white/20 flex items-center gap-2"
                                aria-label="باز کردن تنظیمات"
                            >
                                <Settings className="w-4 h-4 md:w-5 md:h-5" />
                                <span className="hidden md:inline text-sm">تنظیمات</span>
                            </Button>
                        )}
                    </div>
                </div>

                {/* Messages */}
                <div
                    ref={messagesContainerRef}
                    id="messages-container"
                    className="flex-1 overflow-y-auto p-3 md:p-6 space-y-4"
                    onScroll={handleScroll}
                >
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
                                        <div className={`w-8 h-8 md:w-10 md:h-10 rounded-full flex items-center justify-center flex-shrink-0 overflow-hidden ${
                                            message.role === 'user'
                                                ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white'
                                                : message.is_failed
                                                ? 'bg-red-100 text-red-600'
                                                : 'bg-gradient-to-r from-green-100 to-blue-100'
                                        }`}>
                                            {message.role === 'user' ? (
                                                <User className="w-4 h-4 md:w-5 md:h-5" />
                                            ) : (
                                                <>
                                                    <img
                                                        src={BlackCatImage}
                                                        alt="AI Assistant"
                                                        className="w-full h-full object-cover"
                                                        onError={(e) => {
                                                            // Fallback to Bot icon if image fails to load
                                                            e.currentTarget.style.display = 'none';
                                                            const nextElement = e.currentTarget.nextElementSibling as HTMLElement;
                                                            if (nextElement) {
                                                                nextElement.style.display = 'block';
                                                            }
                                                        }}
                                                    />
                                                    <Bot className="w-4 h-4 md:w-5 md:h-5 text-green-700 hidden" />
                                                </>
                                            )}
                                        </div>

                                        {/* Message Content */}
                                        <div className={`flex-1 min-w-0 ${message.role === 'user' ? 'text-right' : ''}`}>
                                            <div className={`group/message rounded-2xl px-3 py-2 md:px-5 md:py-3 relative ${message.role === 'user'
                                                    ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white'
                                                    : message.is_failed
                                                    ? 'bg-red-50 border border-red-200 text-red-900'
                                                    : 'bg-white border border-gray-200 text-gray-900'
                                            }`}>
                                                {/* 🔥 Message Actions */}
                                                <div className="absolute top-2 left-2 opacity-0 group-hover/message:opacity-100 transition-opacity flex gap-1">
                                                    {message.role === 'assistant' && message.is_failed && (
                                                        <button
                                                            onClick={() => retryMessage(message.id)}
                                                            className="p-1.5 bg-white hover:bg-gray-100 rounded-lg shadow-sm border border-gray-200 transition-colors"
                                                            aria-label="تلاش مجدد"
                                                            title="تلاش مجدد"
                                                        >
                                                            <RotateCcw className="w-3.5 h-3.5 text-blue-600" />
                                                        </button>
                                                    )}
                                                    <button
                                                        onClick={() => copyMessage(message.content, message.id)}
                                                        className="p-1.5 bg-white hover:bg-gray-100 rounded-lg shadow-sm border border-gray-200 transition-colors"
                                                        aria-label="کپی پیام"
                                                        title="کپی پیام"
                                                    >
                                                        {copiedMessageId === message.id ? (
                                                            <Check className="w-3.5 h-3.5 text-green-600" />
                                                        ) : (
                                                            <Copy className="w-3.5 h-3.5 text-gray-600" />
                                                        )}
                                                    </button>
                                                </div>
                                                {message.role === 'assistant' ? (
                                                    <div className="text-xs md:text-sm leading-relaxed">
                                                        {/* 🔥 Use typewriter content if available, otherwise use full content */}
                                                        {typewriterMessages[message.id] ? (
                                                            <div>
                                                                <MarkdownRenderer
                                                                    content={typewriterMessages[message.id]}
                                                                    variant="compact"
                                                                />
                                                                {/* Show cursor if still typing */}
                                                                {typewriterMessages[message.id].length < message.content.length && <TypewriterCursor />}
                                                            </div>
                                                        ) : (
                                                            <MarkdownRenderer
                                                                content={message.content}
                                                                variant="compact"
                                                            />
                                                        )}
                                                    </div>
                                                ) : (
                                                    <p className="text-xs md:text-sm leading-relaxed whitespace-pre-wrap break-words">{message.content}</p>
                                                )}
                                                
                                                {/* 🔥 Error Message with Retry */}
                                                {message.role === 'assistant' && message.is_failed && (
                                                    <div className="mt-3 pt-3 border-t border-red-200 flex items-center gap-2 text-red-600">
                                                        <AlertCircle className="w-4 h-4 flex-shrink-0" />
                                                        <div className="flex-1">
                                                            <p className="text-sm font-medium">خطا در ارسال پاسخ</p>
                                                            {message.failure_reason && (
                                                                <p className="text-xs text-red-500 mt-1">{message.failure_reason}</p>
                                                            )}
                                                        </div>
                                                        <button
                                                            onClick={() => {
                                                                // Find the user message before this failed assistant message
                                                                const messageIndex = selectedConversation?.messages.findIndex(m => m.id === message.id) ?? -1
                                                                if (messageIndex > 0) {
                                                                    const userMsg = selectedConversation?.messages[messageIndex - 1]
                                                                    if (userMsg && userMsg.role === 'user') {
                                                                        retryMessage(userMsg.id)
                                                                    }
                                                                }
                                                            }}
                                                            className="flex items-center gap-1 px-3 py-1.5 bg-red-100 hover:bg-red-200 rounded-lg text-sm font-medium transition-colors"
                                                            aria-label="تلاش مجدد"
                                                        >
                                                            <RotateCcw className="w-4 h-4" />
                                                            تلاش مجدد
                                                        </button>
                                                    </div>
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
                                                            <div className="flex items-center gap-1 px-2 py-1 bg-blue-50 rounded-md" title={(() => {
                                                                const modelInfo = availableModels.find(m => m.id === message.model);
                                                                return modelInfo?.detailed_description || modelInfo?.description || message.model;
                                                            })()}>
                                                                <Cpu className="w-3 h-3 text-blue-600" />
                                                                <span className="text-blue-700 font-medium">
                                                                    {(() => {
                                                                        const modelInfo = availableModels.find(m => m.id === message.model);
                                                                        if (modelInfo) {
                                                                            return `${modelInfo.name} (${modelInfo.provider})`;
                                                                        }
                                                                        return message.model;
                                                                    })()}
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
                                                
                                                {/* RAG Type Badge -- CORRECTED */}
                                                    {message.ragType && ( // ✅ از فیلد جدید و صحیح استفاده کن
                                                    <div className="mt-2 flex items-center gap-1 text-xs text-gray-600">
                                                            {getRagTypeIcon(message.ragType as RAGType)}
                                                        <span>{getRagTypeLabel(message.ragType as RAGType)}</span>
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
                                                                            setIsThinking(false);
                                                                            
                                                                            setSelectedConversation(prev => {
                                                                                if (!prev) return prev;
                                                                                const updated = { ...prev };
                                                                                const currentMessage = updated.messages.find(m => m.id === assistantTempId);
                                                                                
                                                                                if (currentMessage) {
                                                                                    // Accumulate content from chunks
                                                                                    const newContent = (currentMessage.content || '') + (evt.content || '');
                                                                                    
                                                                                    // 🔥 Real-time streaming: Use gradual streaming for typewriter effect
                                                                                    if (evt.content) {
                                                                                        streamContentGradually(assistantTempId, newContent);
                                                                                    }
                                                                                    
                                                                                    // Update message content
                                                                                    updated.messages = updated.messages.map(m =>
                                                                                        m.id === assistantTempId
                                                                                            ? { ...m, content: newContent }
                                                                                            : m
                                                                                    );
                                                                                }
                                                                                return updated;
                                                                            });
                                                                            
                                                                            // Auto-scroll during streaming
                                                                            setTimeout(() => scrollToBottom(), 50);
                                                                        }
                                                                        
                                                                        if (evt.type === 'complete') {
                                                                            setSelectedConversation(prev => {
                                                                                if (!prev) return prev;
                                                                                const updated = { ...prev };
                                                                                const finalContent = evt.full_response || updated.messages.find(m => m.id === assistantTempId)?.content || '';
                                                                                
                                                                                // 🔥 Update typewriterMessages with final content only if streaming hasn't completed
                                                                                setTypewriterMessages(prev => {
                                                                                    const currentContent = prev[assistantTempId] || '';
                                                                                    // Only update if current content is less than final content (streaming in progress)
                                                                                    if (currentContent.length < finalContent.length) {
                                                                                        return {
                                                                                            ...prev,
                                                                                            [assistantTempId]: finalContent
                                                                                        };
                                                                                    }
                                                                                    return prev; // Keep current content to preserve typing effect
                                                                                });
                                                                                
                                                                                updated.messages = updated.messages.map(m =>
                                                                                    m.id === assistantTempId
                                                                                        ? {
                                                                                            ...m,
                                                                                            id: evt.message_id || assistantTempId,
                                                                                            content: finalContent,
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
                                    
                                    {/* 🔥 Elegant Skeleton Loader */}
                                    {isThinking && <SkeletonLoader />}
                            
                            <div ref={messagesEndRef} />

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
                        </>
                    )}
                </div>

                {/* Input Area - 🔥 Always visible for better UX */}
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
                            {/* 🔧 Voice Input - به صورت موقت مخفی شده */}
                            {FEATURE_FLAGS.SHOW_VOICE_INPUT && (
                                <VoiceInput
                                    onTranscriptionComplete={(text) => {
                                        setNewMessage(prev => prev ? `${prev}\n${text}` : text)
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
                                <button
                                    onClick={() => setShowSettingsModal(true)}
                                    className="flex items-center gap-1 text-purple-600 hover:text-purple-700 transition-colors"
                                    aria-label="نمایش راهنمای کیبورد شورتکات"
                                    title="راهنمای کیبورد شورتکات"
                                >
                                    <HelpCircle className="w-3.5 h-3.5" />
                                    <span className="hidden lg:inline">راهنما</span>
                                </button>
                            </div>
                            <div className="flex items-center gap-1">
                                {getRagTypeIcon(ragType)}
                                <span className="mr-1">حالت فعال: {getRagTypeLabel(ragType)}</span>
                            </div>
                        </div>
                    </div>
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

