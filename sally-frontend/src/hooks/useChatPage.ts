// useChatPage hook – manages chat UI state and streaming interactions
import { useState, useRef, useEffect, useCallback } from 'react';
import { chatService } from '../services/chatService';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-hot-toast';
import type { Conversation, Message, ChatState, ChatActions } from '../types/chat';

interface UseChatPageProps {
  isDevelopment?: boolean;
}

export const useChatPage = ({ isDevelopment = false }: UseChatPageProps = {}): ChatState & ChatActions => {
  const { user } = useAuth();

  // ----- State -----
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [newMessage, setNewMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingTitle, setEditingTitle] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState('');
  const [guestSessionId, setGuestSessionId] = useState<string | null>(null);

  // ----- Refs -----
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const initializationRef = useRef(false);
  const displayedLengthsRef = useRef<Map<string, number>>(new Map()); // for streaming chunk tracking

  // ----- Helper: guest session -----
  const initializeGuestSession = useCallback(() => {
    if (!user) {
      const sessionId =
        localStorage.getItem('guest_session_id') ||
        `guest_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('guest_session_id', sessionId);
      setGuestSessionId(sessionId);
      console.log('👤 Guest session initialized:', sessionId);
    }
  }, [user]);

  // ----- Load conversations -----
  const loadConversations = useCallback(async () => {
    try {
      console.log('🔄 Loading conversations from API...');
      const response = await chatService.getConversations();
      if (Array.isArray(response)) {
        const formatted: Conversation[] = response.map((c) => ({
          id: c.id,
          title: c.title,
          messages: [],
          created_at: c.created_at,
          updated_at: c.updated_at,
        }));
        setConversations(formatted);
      } else {
        console.warn('⚠️ Unexpected conversations format', response);
        setConversations([]);
      }
    } catch (e) {
      console.error('❌ Error loading conversations', e);
      setConversations([]);
    }
  }, []);

  // ----- Load messages for a conversation -----
  const loadConversationMessages = useCallback(async (conversationId: string): Promise<Message[]> => {
    try {
      const raw = await chatService.getConversationMessages(conversationId, guestSessionId || undefined);
      if (Array.isArray(raw)) {
        return raw.map((msg) => ({
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
          metadata: msg.metadata,
        }));
      }
      console.warn('⚠️ Unexpected messages format', raw);
      return [];
    } catch (e) {
      console.error('❌ Error loading messages', e);
      return [];
    }
  }, [guestSessionId]);

  // ----- Send message (streaming) -----
  const handleSendMessage = async (): Promise<void> => {
    const conversation = selectedConversation;
    if (!conversation) return;
    const trimmed = newMessage.trim();
    if (!trimmed) return;

    setIsLoading(true);
    // Add user message locally
    const userMsg: Message = {
      id: `temp-${Date.now()}`,
      content: trimmed,
      role: 'user',
      timestamp: new Date(),
    };
    setSelectedConversation((prev) => {
      if (!prev) return prev;
      const updated = {
        ...prev,
        messages: [...prev.messages, userMsg],
        title: prev.messages.length === 0 ? trimmed.slice(0, 30) + (trimmed.length > 30 ? '...' : '') : prev.title,
      };
      return updated;
    });
    setNewMessage('');

    // Placeholder AI (thinking) message
    const placeholderId = `thinking-${Date.now()}`;
    const thinkingMsg: Message = {
      id: placeholderId,
      content: '',
      role: 'assistant',
      timestamp: new Date(),
      isThinking: true,
    };
    setSelectedConversation((prev) => {
      if (!prev) return prev;
      return { ...prev, messages: [...prev.messages, thinkingMsg] };
    });
    setConversations((prev) =>
      prev.map((c) => (c.id === conversation.id ? { ...c, messages: [...c.messages, thinkingMsg] } : c))
    );

    // Start streaming request
    chatService.sendMessageStream(
      trimmed,
      conversation.id.startsWith('new-') ? undefined : conversation.id,
      guestSessionId || undefined,
      async (evt: any) => {
        if (evt.type === 'init') {
          if (evt.conversation_id && conversation.id.startsWith('new-')) {
            const newId = evt.conversation_id;
            setConversations((prev) => prev.map((c) => (c.id === conversation.id ? { ...c, id: newId } : c)));
            setSelectedConversation((prev) => (prev ? { ...prev, id: newId } : null));
          }
        } else if (evt.type === 'chunk') {
          const added = evt.content ?? '';
          const prevLen = displayedLengthsRef.current.get(placeholderId) || 0;
          displayedLengthsRef.current.set(placeholderId, prevLen + added.length);
          setSelectedConversation((prev) => {
            if (!prev) return prev;
            const updatedMsgs = prev.messages.map((m) => {
              if (m.id === placeholderId) {
                const currentContent = m.content || '';
                // اطمینان از وجود فضای خالی بین چانک‌ها اگر لازم باشد
                let newContent = currentContent + added;

                // اگر چانک جدید با حرف شروع می‌شود و محتوای قبلی با حرف تمام می‌شود، فضای خالی اضافه کن
                if (currentContent && added &&
                    !currentContent.endsWith(' ') && !currentContent.endsWith('\n') && !currentContent.endsWith('\t') &&
                    !added.startsWith(' ') && !added.startsWith('\n') && !added.startsWith('\t') &&
                    /\w/.test(currentContent.slice(-1)) && /\w/.test(added[0])) {
                  newContent = currentContent + ' ' + added;
                }

                return { ...m, content: newContent, isThinking: false };
              }
              return m;
            });
            return { ...prev, messages: updatedMsgs };
          });
        } else if (evt.type === 'complete') {
          const finalMsg: Message = {
            id: evt.message_id,
            content: evt.full_response,
            role: 'assistant',
            timestamp: new Date(),
            sources: evt.sources,
            confidence: evt.confidence,
            suggested_actions: evt.suggested_actions,
            metadata: {
              rag_type: evt.rag_type,
              model: evt.model,
              temperature: evt.temperature,
            },
          };
          setSelectedConversation((prev) => {
            if (!prev) return prev;
            const filtered = prev.messages.filter((m) => m.id !== placeholderId);
            return { ...prev, messages: [...filtered, finalMsg] };
          });
          setConversations((prev) =>
            prev.map((c) => {
              if (c.id === conversation.id || c.id === evt.conversation_id) {
                const filtered = c.messages.filter((m) => m.id !== placeholderId);
                return { ...c, messages: [...filtered, finalMsg] };
              }
              return c;
            })
          );
        } else if (evt.type === 'error') {
          console.error('Streaming error:', evt.message);
          const errMsg: Message = {
            id: `error-${Date.now()}`,
            content: 'خطا در دریافت پاسخ',
            role: 'assistant',
            timestamp: new Date(),
            is_failed: true,
            failure_reason: evt.message,
          };
          setSelectedConversation((prev) => {
            if (!prev) return prev;
            const filtered = prev.messages.filter((m) => m.id !== placeholderId);
            return { ...prev, messages: [...filtered, errMsg] };
          });
        }
      },
      undefined,
      undefined
    );
    setIsLoading(false);
  };

  // ----- New chat -----
  const handleNewChat = () => {
    if (selectedConversation?.id.startsWith('new-') && selectedConversation.messages.length === 0) return;
    const uniqueId = `new-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const newConv: Conversation = { id: uniqueId, title: 'گفتگوی جدید', messages: [] };
    setConversations((prev) => [newConv, ...prev]);
    setSelectedConversation(newConv);
  };

  // ----- Select conversation -----
  const handleSelectConversation = async (conversation: Conversation) => {
    setSelectedConversation(conversation);
    if (!conversation.id.startsWith('new-')) {
      const msgs = await loadConversationMessages(conversation.id);
      const updated = { ...conversation, messages: msgs };
      setSelectedConversation(updated);
      setConversations((prev) => prev.map((c) => (c.id === conversation.id ? updated : c)));
    }
  };

  // ----- Title editing -----
  const handleTitleEdit = (conversationId: string, currentTitle: string) => {
    setEditingTitle(conversationId);
    setNewTitle(currentTitle);
  };

  const handleTitleSave = async (conversationId: string) => {
    if (!newTitle.trim()) return;
    try {
      if (!conversationId.startsWith('new-') && user) {
        await chatService.updateConversationTitle(conversationId, newTitle.trim());
      }
      setConversations((prev) =>
        prev.map((c) => (c.id === conversationId ? { ...c, title: newTitle.trim() } : c))
      );
      if (selectedConversation?.id === conversationId) {
        setSelectedConversation((prev) => (prev ? { ...prev, title: newTitle.trim() } : null));
      }
    } catch (e) {
      console.warn('API not available for updating title:', e);
    }
    if (!user) {
      // Guest fallback – same update logic already applied above
    }
    setEditingTitle(null);
    setNewTitle('');
  };

  const handleTitleCancel = () => {
    setEditingTitle(null);
    setNewTitle('');
  };

  // ----- Delete conversation -----
  const handleDeleteConversation = async (conversationId: string) => {
    if (window.confirm('آیا مطمئن هستید که می‌خواهید این گفتگو را حذف کنید؟')) {
      try {
        setConversations((prev) => prev.filter((c) => c.id !== conversationId));
        if (selectedConversation?.id === conversationId) setSelectedConversation(null);
        toast.success('گفتگو حذف شد');
      } catch (e) {
        console.error('Error deleting conversation:', e);
        toast.error('خطا در حذف گفتگو');
      }
    }
  };

  // ----- Utility functions -----
  const formatTime = (date: Date) =>
    date.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // ----- Copy message -----
  const copyMessage = useCallback(async (messageId: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      toast.success('پیام کپی شد');
    } catch (e) {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = content;
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand('copy');
        toast.success('پیام کپی شد');
      } catch (fallback) {
        console.error('Fallback copy failed:', fallback);
        toast.error('خطا در کپی کردن');
      }
      document.body.removeChild(textarea);
    }
  }, []);

  // ----- Retry failed user message -----
  const retryMessage = useCallback(
    (messageId: string) => {
      if (!selectedConversation) return;
      const idx = selectedConversation.messages.findIndex((m) => m.id === messageId);
      if (idx === -1) return;
      const msg = selectedConversation.messages[idx];
      if (msg.role !== 'user') return;
      const updated = selectedConversation.messages.slice(0, idx);
      setSelectedConversation((prev) => (prev ? { ...prev, messages: updated } : null));
      setNewMessage(msg.content);
      setTimeout(() => handleSendMessage(), 100);
    },
    [selectedConversation]
  );

  // ----- Regenerate assistant response -----
  const regenerateMessage = useCallback(
    async (messageId: string) => {
      if (!selectedConversation) return;
      const idx = selectedConversation.messages.findIndex((m) => m.id === messageId);
      if (idx === -1) return;
      const assistantMsg = selectedConversation.messages[idx];
      if (assistantMsg.role !== 'assistant') return;
      const userIdx = idx - 1;
      if (userIdx < 0) return;
      const userMsg = selectedConversation.messages[userIdx];
      if (userMsg.role !== 'user') return;
      const updated = selectedConversation.messages.slice(0, userIdx + 1);
      setSelectedConversation((prev) => (prev ? { ...prev, messages: updated } : null));
      setNewMessage(userMsg.content);
      setTimeout(() => handleSendMessage(), 100);
    },
    [selectedConversation]
  );

  // ----- Initialization effect -----
  useEffect(() => {
    if (initializationRef.current) return;
    initializationRef.current = true;
    const init = async () => {
      if (isDevelopment) console.log('🔧 Development mode – using real API');
      initializeGuestSession();
      await loadConversations();
      setIsInitialLoading(false);
      // Ensure at least one conversation exists
      setConversations((prev) => {
        if (prev.length === 0 || prev[0].id.startsWith('new-')) {
          const uid = `new-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
          const conv: Conversation = { id: uid, title: 'گفتگوی جدید', messages: [] };
          setSelectedConversation(conv);
          return [conv, ...prev];
        }
        setSelectedConversation(prev[0]);
        return prev;
      });
    };
    init();
  }, []);

  // ----- Scroll on new messages -----
  useEffect(() => {
    if (selectedConversation?.messages) scrollToBottom();
  }, [selectedConversation?.messages]);

  // ----- Return state and actions -----
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
    copyMessage,
    retryMessage,
    regenerateMessage,
  };
};