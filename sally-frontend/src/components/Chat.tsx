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
  HelpCircle
} from 'lucide-react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';

// Define component-specific types
interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
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
        role: msg.is_from_user ? 'user' : 'assistant',
        timestamp: new Date(msg.created_at),
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


  // 5. Refactored "Send Message" handler
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
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        messages: [optimisticUserMessage],
      });
    }
    
    setNewMessage('');
    setIsLoading(true);

    try {
      const response = await chatService.sendMessage(
        newMessage,
        selectedConversation?.id === 'new-chat' ? undefined : selectedConversation?.id || undefined
      );
      
      const assistantMessage: Message = {
        id: response.message_id,
        content: response.message,
        role: 'assistant',
        timestamp: new Date(),
      };

      // If it was a new chat, update the conversation list and the selected conversation
      if (!selectedConversation || selectedConversation.id === 'new-chat') {
        const newConvFromServer = { id: response.conversation_id, title: newMessage.slice(0, 30), created_at: new Date().toISOString(), updated_at: new Date().toISOString() };
        setConversations(prev => [newConvFromServer, ...prev]);
        setSelectedConversation({
            ...newConvFromServer,
            messages: [optimisticUserMessage, assistantMessage]
        });
      } 
      else {
        // Otherwise, just add the new message
        setSelectedConversation(prev => ({
          ...prev!,
          messages: [...prev!.messages, assistantMessage],
        }));
      }

    } catch (error) {
      console.error('Failed to send message:', error);
      // Optional: Add logic to remove the optimistic message on error
    } finally {
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
                    <div className={`p-4 rounded-lg shadow-sm ${message.role === 'user' ? 'bg-white text-slate-800' : 'bg-blue-600 text-white'}`}>
                      <p className="text-right whitespace-pre-wrap">{message.content}</p>
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
                                  <p className="text-xs text-gray-500 text-right">
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
  )
};

export default Chat;