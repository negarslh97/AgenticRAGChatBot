'use client'

import React, { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { useAuth } from '../context/AuthContext';
import { chatService, Conversation as ApiConversation } from '../services/chatService';
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
  ExternalLink
} from 'lucide-react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import ArticleHighlightModal from './ArticleHighlightModal';

// Define component-specific types
interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  sender_type?: 'Customer' | 'Admin' | 'SuperAdmin' | 'Guest' | 'AI';
  is_failed?: boolean;
  failure_reason?: string;
  rating?: {
    rating: number;
    comment?: string;
    rated_by?: string;
    rated_at?: string;
  };
  metadata?: {
    model_name?: string;
    provider?: string;
    confidence?: number;
    sources?: Array<{
      id: string;
      title: string;
      score: number;
      category?: string;
      tags?: string[];
    }>;
    token_usage?: {
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
    };
  };
}

interface Conversation extends ApiConversation {
  messages: Message[]; // Add messages array to the conversation type
}

const Chat: React.FC = () => {
  const { user } = useAuth();
  const [conversations, setConversations] = useState<ApiConversation[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [newMessage, setNewMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // 🔥 State برای Article Highlight Modal
  const [highlightModal, setHighlightModal] = useState<{
    isOpen: boolean;
    articleId: string;
    userQuery: string;
  }>({ isOpen: false, articleId: '', userQuery: '' });

  // Helper: Dedupe sources by ID (backend should already do this, but double-check)
  const dedupeSourcesById = (sources?: any[]) => {
    if (!sources) return [] as any[];
    const seen = new Set<string>();
    const unique: any[] = [];
    for (const s of sources) {
      const id = s?.id?.toString?.() || '';
      if (id && !seen.has(id)) {
        seen.add(id);
        unique.push(s);
      }
    }
    return unique;
  };

  // 1. Fetch conversation list on mount
  useEffect(() => {
    const fetchConversations = async () => {
      try {
        const fetchedConversations = await chatService.getConversations();
        setConversations(fetchedConversations);
      } catch (error) {
        console.error('Failed to fetch conversations:', error);
      }
    };
    fetchConversations();
  }, []);

  // 2. Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [selectedConversation?.messages]);


  // 3. Simplified "New Chat" handler
  const handleNewChat = () => {
    setSelectedConversation(null);
    setNewMessage('');
  };

  // 4. Simplified "Conversation Select" handler
  const handleSelectConversation = async (conversation: ApiConversation) => {
    // Prevent re-fetching if already selected
    if (selectedConversation?.id === conversation.id) return;

    setIsLoading(true);
    try {
      const fetchedMessages = await chatService.getConversationMessages(conversation.id);
      const transformedMessages: Message[] = fetchedMessages.map(msg => ({
        id: msg.id,
        content: msg.content,
        role: msg.sender_type === 'AI' ? 'assistant' : 'user',
        timestamp: new Date(msg.created_at),
        sender_type: msg.sender_type,
        is_failed: msg.is_failed,
        failure_reason: msg.failure_reason,
        rating: msg.rating,
        metadata: msg.metadata,
      }));

      setSelectedConversation({
        ...conversation,
        messages: transformedMessages,
      });
    } catch (error) {
      console.error('Failed to load conversation messages:', error);
    } finally {
      setIsLoading(false);
    }
  };


  // 5. Streaming "Send Message" handler
  const handleSendMessage = async () => {
    if (!newMessage.trim() || isLoading) return;

    const optimisticUserMessage: Message = {
      id: `temp-${Date.now()}`,
      content: newMessage,
      role: 'user',
      timestamp: new Date(),
    };

    // Optimistic UI update
    if (selectedConversation) {
      setSelectedConversation(prev => ({
        ...prev!,
        messages: [...prev!.messages, optimisticUserMessage],
      }));
    } else {
      // For a new chat, create a temporary conversation shell
      setSelectedConversation({
        id: 'new-chat',
        title: newMessage.slice(0, 30),
        tags: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        messages: [optimisticUserMessage],
      });
    }
    
    setNewMessage('');
    setIsLoading(true);

    try {
      // Add a streaming assistant placeholder
      const assistantTempId = `ai-temp-${Date.now()}`;
      const addAssistantPlaceholder = () => setSelectedConversation(prev => ({
        ...prev!,
        messages: [...(prev?.messages || []), {
          id: assistantTempId,
          content: '',
          role: 'assistant',
          timestamp: new Date(),
          metadata: { sources: [] }
        } as Message]
      } as Conversation));

      addAssistantPlaceholder();

      const currentConvId = selectedConversation?.id === 'new-chat' ? undefined : selectedConversation?.id;

      await chatService.sendMessageStream(
        optimisticUserMessage.content,
        currentConvId,
        undefined,
        (evt: any) => {
          if (!evt || !selectedConversation) return;

          if (evt.type === 'init') {
            // Set conversation id if it was a new chat and add to list
            if (!currentConvId && evt.conversation_id) {
              const newConv: ApiConversation = {
                id: evt.conversation_id,
                title: optimisticUserMessage.content.slice(0, 30),
                tags: [],
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString()
              };
              setConversations(prev => [newConv, ...prev]);
              setSelectedConversation(prev => prev ? ({ ...prev, id: evt.conversation_id }) : prev);
            }
          }

          if (evt.type === 'sources') {
            const unique = dedupeSourcesById(evt.sources);
            console.log('📚 Sources received:', unique);
            unique.forEach((s: any, i: number) => {
              console.log(`   Source ${i+1}: ID="${s.id}", Title="${s.title}"`);
            });
            
            setSelectedConversation(prev => {
              if (!prev) return prev;
              const next = { ...prev } as Conversation;
              next.messages = next.messages.map(m => m.id === assistantTempId ? ({
                ...m,
                metadata: {
                  ...(m.metadata || {}),
                  sources: unique
                }
              }) : m);
              return next;
            });
          }

          if (evt.type === 'chunk') {
            setSelectedConversation(prev => {
              if (!prev) return prev;
              const next = { ...prev } as Conversation;
              next.messages = next.messages.map(m => m.id === assistantTempId ? ({
                ...m,
                content: (m.content || '') + (evt.content || '')
              }) : m);
              return next;
            });
          }

          if (evt.type === 'complete') {
            setSelectedConversation(prev => {
              if (!prev) return prev;
              const next = { ...prev } as Conversation;
              next.messages = next.messages.map(m => m.id === assistantTempId ? ({
                ...m,
                id: evt.message_id || assistantTempId,
                content: evt.full_response || m.content || '',
                metadata: {
                  ...(m.metadata || {}),
                  confidence: evt.confidence
                }
              }) : m);
              return next;
            });
            setIsLoading(false);
            
            // 🔥 Fetch updated conversation with new title
            if (evt.conversation_id) {
              setTimeout(async () => {
                try {
                  const updatedConv = await chatService.getConversation(evt.conversation_id);
                  if (updatedConv && updatedConv.title) {
                    // Update conversations list
                    setConversations(prev => prev.map(c => 
                      c.id === evt.conversation_id ? updatedConv : c
                    ));
                    // Update selected conversation
                    setSelectedConversation(prev => prev && prev.id === evt.conversation_id ? 
                      { ...prev, ...updatedConv } : prev
                    );
                  }
                } catch (error) {
                  console.error('Failed to fetch updated conversation:', error);
                }
              }, 1500); // Wait 1.5s for backend to generate title
            }
          }

          if (evt.type === 'error') {
            setSelectedConversation(prev => {
              if (!prev) return prev;
              const next = { ...prev } as Conversation;
              next.messages = next.messages.map(m => m.id === assistantTempId ? ({
                ...m,
                is_failed: true,
                failure_reason: evt.message
              }) : m);
              return next;
            });
            setIsLoading(false);
          }
        }
      );

    } catch (error) {
      console.error('Failed to send message (stream):', error);
      setIsLoading(false);
    }
  };
  
  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('fa-IR', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

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
      
      <div className="flex h-screen w-full bg-gray-50">
      {/* =============================================================== */}
      {/* Main Content Area (CORRECTED for RTL) */}
      {/* =============================================================== */}
      <main className={`flex-1 flex flex-col transition-all duration-300 ${isSidebarOpen ? 'mr-80' : 'mr-0'}`}>
        <header className="flex items-center justify-between p-4 bg-white shadow-sm">
            {/* ... Header content remains the same ... */}
            <div className="flex items-center gap-3"> {/* For RTL, remove mr-4 */}
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
                onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                variant="ghost"
                size="icon"
            >
                {isSidebarOpen ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            </Button>
        </header>

        {/* Chat messages area */}
        <div className="flex-1 p-4 overflow-y-auto">
          {!selectedConversation ? (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-6">
                {/* ... Welcome screen content remains the same ... */}
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
                            onClick={() => setNewMessage('به من درباره هوش مصنوعی بگو')}
                        >
                            <HelpCircle className="h-4 w-4 ml-2 text-gray-500" />
                            به من درباره هوش مصنوعی بگو
                        </Button>
                        <Button
                            variant="outline"
                            className="flex items-center justify-start text-right p-2"
                            onClick={() => setNewMessage('یک برنامه ساده به پایتون بنویس')}
                        >
                            <Lightbulb className="h-4 w-4 ml-2 text-gray-500" />
                            یک برنامه ساده به پایتون بنویس
                        </Button>
                        <Button
                            variant="outline"
                            className="flex items-center justify-start text-right p-2"
                            onClick={() => setNewMessage('چطور می‌توانم یادگیری ماشین را شروع کنم؟')}
                        >
                            <Sparkles className="h-4 w-4 ml-2 text-gray-500" />
                            چطور می‌توانم یادگیری ماشین را شروع کنم؟
                        </Button>
                    </div>
                </div>
            </div>
          ) : (
            <div className="space-y-4">
              {selectedConversation.messages.map((message) => (
                <div key={message.id} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {message.role === 'assistant' && (
                    <div className="h-8 w-8 rounded-full bg-blue-600 flex-shrink-0 flex items-center justify-center">
                      <Bot className="h-4 w-4 text-white" />
                    </div>
                  )}
                  <div className={`max-w-[70%]`}>
                    <div className={`p-4 rounded-lg shadow-sm ${message.role === 'user' ? 'bg-white text-slate-800' : message.is_failed ? 'bg-red-100 text-red-800 border border-red-200' : 'bg-blue-600 text-white'}`}>
                      <p className="text-right whitespace-pre-wrap">{message.content}</p>
                      {/* 🔥 Streaming indicator */}
                      {message.role === 'assistant' && !message.content && isLoading && (
                        <div className="flex items-center gap-2 text-white/70">
                          <div className="animate-pulse">در حال نوشتن</div>
                          <div className="flex gap-1">
                            <div className="w-2 h-2 bg-white/70 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                            <div className="w-2 h-2 bg-white/70 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                            <div className="w-2 h-2 bg-white/70 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                          </div>
                        </div>
                      )}
                      {message.is_failed && message.failure_reason && (
                        <p className="text-xs text-red-600 mt-2 text-right">
                          خطا: {message.failure_reason}
                        </p>
                      )}
                      {message.metadata && message.role === 'assistant' && (
                        <div className="mt-2 space-y-2">
                          {/* Sources section - clickable with highlighting */}
                          {message.metadata.sources && message.metadata.sources.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-white/20">
                              <p className="text-xs font-medium opacity-90 mb-2 flex items-center gap-1">
                                <Sparkles className="h-3 w-3" />
                                📚 منابع مرتبط (کلیک کنید برای مشاهده با highlight):
                              </p>
                              <div className="space-y-2">
                                {message.metadata.sources.map((source: any, index: number) => {
                                  // 🔥 پیدا کردن سوال اصلی کاربر (پیام قبلی)
                                  const messageIndex = selectedConversation?.messages.findIndex(m => m.id === message.id);
                                  const userMessage = messageIndex !== undefined && messageIndex > 0 
                                    ? selectedConversation?.messages[messageIndex - 1] 
                                    : null;
                                  const userQuery = userMessage?.role === 'user' ? userMessage.content : '';
                                  
                                  return (
                                    <button
                                      key={source.id || index}
                                      onClick={() => {
                                        console.log('🖱️ Source clicked!');
                                        console.log('   Article ID:', source.id);
                                        console.log('   User Query:', userQuery);
                                        console.log('   Source:', source);
                                        
                                        if (!source.id) {
                                          console.error('❌ No article ID!');
                                          alert('خطا: شناسه مقاله موجود نیست!');
                                          return;
                                        }
                                        
                                        setHighlightModal({
                                          isOpen: true,
                                          articleId: source.id,
                                          userQuery: userQuery
                                        });
                                      }}
                                      className="text-xs opacity-80 hover:opacity-100 transition-all w-full text-right p-2 rounded hover:bg-white/10 flex items-center gap-2 group"
                                    >
                                      <ExternalLink className="h-3 w-3 opacity-50 group-hover:opacity-100" />
                                      <span className="flex-1">
                                        {index + 1}. {source.title}
                                      </span>
                                      {/* 🔥 Debug info */}
                                      <span className="text-xs opacity-50">
                                        (ID: {source.id ? source.id.substring(0, 8) + '...' : 'N/A'})
                                      </span>
                                    </button>
                                  );
                                })}
                              </div>
                            </div>
                          )}

                          {/* Model info */}
                          <div className="text-xs opacity-75 text-left">
                            {message.metadata.model_name && (
                              <span>مدل: {message.metadata.model_name}</span>
                            )}
                            {message.metadata.confidence && (
                              <span className="mr-2">دقت: {Math.round(message.metadata.confidence * 100)}%</span>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                    <div className={`text-xs text-gray-500 mt-1 ${message.role === 'user' ? 'text-right' : 'text-left'}`}>
                      {formatTime(message.timestamp)}
                      {message.sender_type && message.sender_type !== 'AI' && message.sender_type !== 'Guest' && (
                        <span className="mr-2">({message.sender_type})</span>
                      )}
                      <span className="mr-2">
                        {message.role === 'user' ? 'کاربر' : 'AI'}
                      </span>
                    </div>
                  </div>
                  {message.role === 'user' && (
                    <div className="h-8 w-8 rounded-full bg-gray-300 flex-shrink-0 flex items-center justify-center">
                      <User className="h-4 w-4 text-gray-600" />
                    </div>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <footer className="p-4 bg-white shadow-[0_-2px_4px_-2px_rgba(0,0,0,0.05)]">
            {/* ... Footer content remains the same ... */}
            <div className="flex gap-2">
                <Button
                    onClick={handleSendMessage}
                    disabled={!newMessage.trim() || isLoading}
                    size="icon"
                    className="flex-shrink-0 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300"
                >
                    {isLoading ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    ) : (
                        <Send className="h-4 w-4" />
                    )}
                </Button>
                <Textarea
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="پیام خود را بنویسید..."
                    className="flex-1 resize-none text-right bg-white rounded-lg p-3 border-2 border-slate-200 focus-visible:border-blue-500 focus-visible:ring-0 focus-visible:outline-none transition-colors"
                    rows={1}
                    disabled={isLoading}
                />
            </div>
        </footer>
      </main>

      {/* Sidebar (CORRECTED for RTL) */}
      <aside className={`flex flex-col bg-white shadow-lg transition-all duration-300 ${isSidebarOpen ? 'w-80' : 'w-0'} overflow-hidden`}>
          <div className="p-4 bg-white shadow-sm">
              <Button onClick={handleNewChat} className="w-full justify-end flex items-center gap-2 bg-blue-600 hover:bg-blue-700">
                  <Plus className="h-4 w-4" />
                  گفتگوی جدید
              </Button>
          </div>
          <div className="flex-1 overflow-auto">
              <div className="p-2 space-y-2">
                  {conversations.map((conversation) => (
                      <div
                          key={conversation.id}
                          className={`cursor-pointer transition-colors p-3 rounded-lg ${selectedConversation?.id === conversation.id ? 'bg-slate-100' : 'hover:bg-slate-50'}`}
                          onClick={() => handleSelectConversation(conversation)}
                      >
                          <div className="flex items-start gap-2">
                              <div className="flex-1 min-w-0">
                                  <h4 className="font-medium text-gray-900 truncate text-right">
                                      {conversation.title}
                                  </h4>
                                  {/* 🆕 نمایش metadata */}
                                  <div className="flex flex-wrap gap-1 mt-1 text-right">
                                    {conversation.rag_type && (
                                      <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-800 rounded-full">
                                        {conversation.rag_type === 'agentic' ? '🧠 Agentic RAG' : '📚 Simple RAG'}
                                      </span>
                                    )}
                                    {conversation.model_name && (
                                      <span className="px-2 py-0.5 text-xs bg-green-100 text-green-800 rounded-full" title={conversation.model_name}>
                                        🤖 {conversation.model_name.split('/').pop()?.split(':')[0] || conversation.model_name}
                                      </span>
                                    )}
                                  </div>
                                  {conversation.tags && conversation.tags.length > 0 && (
                                    <div className="flex flex-wrap gap-1 mt-1">
                                      {conversation.tags.slice(0, 2).map((tag, index) => (
                                        <span key={index} className="px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded-full">
                                          {tag}
                                        </span>
                                      ))}
                                      {conversation.tags.length > 2 && (
                                        <span className="text-xs text-gray-500">
                                          +{conversation.tags.length - 2}
                                        </span>
                                      )}
                                    </div>
                                  )}
                                  <p className="text-xs text-gray-500 text-right mt-1">
                                      {formatTime(new Date(conversation.created_at))}
                                  </p>
                              </div>
                              {/* Icon logic can be improved later if needed */}
                          </div>
                      </div>
                  ))}
              </div>
          </div>
      </aside>
    </div>
    </>
  )
};

export default Chat;