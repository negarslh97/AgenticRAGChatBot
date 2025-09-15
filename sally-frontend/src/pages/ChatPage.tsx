'use client'

import React, { useState, useRef, useEffect, KeyboardEvent } from 'react'
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
} from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { Avatar, AvatarFallback } from '../components/ui/avatar'
import { Textarea } from '../components/ui/textarea'

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
}

interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
}

const ChatPage = () => {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)

    const [conversations, setConversations] = useState<Conversation[]>([
        {
            id: '1',
            title: 'درباره هوش مصنوعی',
            messages: [
                {
                    id: '1',
                    content: 'هوش مصنوعی چیست و چگونه کار می‌کند؟',
                    role: 'user',
                    timestamp: new Date(Date.now() - 3600000)
                },
                {
                    id: '2',
                    content: 'هوش مصنوعی (AI) شاخه‌ای از علوم کامپیوتر است که به ماشین‌ها این قابلیت را می‌دهد که کارهایی را انجام دهند که معمولاً به هوش انسانی نیاز دارند. این شامل یادگیری، استدلال، حل مسئله، درک زبان طبیعی و تشخیص الگو می‌شود.',
                    role: 'assistant',
                    timestamp: new Date(Date.now() - 3500000)
                }
            ],
            createdAt: new Date(Date.now() - 3600000)
        },
        {
            id: '2',
            title: 'پرسش در مورد برنامه‌نویسی',
            messages: [
                {
                    id: '1',
                    content: 'بهترین زبان برای شروع یادگیری برنامه‌نویسی چیست؟',
                    role: 'user',
                    timestamp: new Date(Date.now() - 86400000)
                },
                {
                    id: '2',
                    content: 'انتخاب بهترین زبان برنامه‌نویسی برای مبتدیان بستگی به اهداف شما دارد. برای شروع عمومی، پایتون گزینه عالی است به دلیل خوانایی بالا و کاربردهای گسترده. اگر به وب‌سایت‌ها علاقه دارید، جاوااسکریپت انتخاب خوبی است.',
                    role: 'assistant',
                    timestamp: new Date(Date.now() - 86300000)
                }
            ],
            createdAt: new Date(Date.now() - 86400000)
        },
        {
            id: '3',
            title: 'مشاوره شغلی',
            messages: [
                {
                    id: '1',
                    content: 'چگونه می‌توانم در رشته فناوری اطلاعات موفق باشم؟',
                    role: 'user',
                    timestamp: new Date(Date.now() - 172800000)
                }
            ],
            createdAt: new Date(Date.now() - 172800000)
        }
    ])

    const [selectedConversation, setSelectedConversation] = useState<Conversation>(conversations[0])
    const [newMessage, setNewMessage] = useState('')
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const toggleSidebar = () => {
        setIsSidebarOpen(!isSidebarOpen)
    }

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => {
        scrollToBottom()
    }, [selectedConversation.messages])

    const handleSendMessage = () => {
        if (newMessage.trim() === '') return

        const userMessage: Message = {
            id: Date.now().toString(),
            content: newMessage,
            role: 'user',
            timestamp: new Date()
        }

        const updatedConversation = {
            ...selectedConversation,
            messages: [...selectedConversation.messages, userMessage],
            title: selectedConversation.messages.length === 0 
                ? newMessage.slice(0, 30) + (newMessage.length > 30 ? '...' : '')
                : selectedConversation.title
        }

        setSelectedConversation(updatedConversation)
        setConversations(prev => 
            prev.map(conv => conv.id === selectedConversation.id ? updatedConversation : conv)
        )
        setNewMessage('')

        setTimeout(() => {
            const aiMessage: Message = {
                id: (Date.now() + 1).toString(),
                content: 'این یک پاسخ نمونه از Sally است. من در اینجا هستم تا به سؤالات شما پاسخ دهم.',
                role: 'assistant',
                timestamp: new Date()
            }

            const updatedWithAi = {
                ...updatedConversation,
                messages: [...updatedConversation.messages, aiMessage]
            }

            setSelectedConversation(updatedWithAi)
            setConversations(prev => 
                prev.map(conv => conv.id === selectedConversation.id ? updatedWithAi : conv)
            )
        }, 1000)
    }

    const handleNewChat = () => {
        const newConversation: Conversation = {
            id: Date.now().toString(),
            title: 'گفتگوی جدید',
            messages: [],
            createdAt: new Date()
        }
        setConversations(prev => [newConversation, ...prev])
        setSelectedConversation(newConversation)
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
        <div className="flex h-screen w-full bg-gray-50">
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
                    {selectedConversation.messages.length === 0 ? (
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
                                    <div className={`max-w-[70%] ${message.role === 'user' ? 'order-2' : 'order-1'}`}>
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

                {/* Message input form */}
                <footer className="p-4 bg-white shadow-[0_-2px_4px_-2px_rgba(0,0,0,0.05)]">
                    <div className="flex gap-2">
                        <Button
                            onClick={handleSendMessage}
                            disabled={!newMessage.trim()}
                            size="icon"
                            className="flex-shrink-0 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300"
                        >
                            <Send className="h-4 w-4" />
                        </Button>
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
                <div className="flex-1 overflow-auto">
                    <div className="p-2 space-y-2">
                        {conversations.map((conversation) => (
                            <div
                                key={conversation.id}
                                className={`cursor-pointer transition-colors p-3 rounded-lg ${
                                    selectedConversation.id === conversation.id
                                        ? 'bg-slate-100'
                                        : 'hover:bg-slate-50'
                                }`}
                                onClick={() => setSelectedConversation(conversation)}
                            >
                                <div className="flex items-start gap-2">
                                    <div className="flex-1 min-w-0">
                                        <h4 className="font-medium text-gray-900 truncate text-right">
                                            {conversation.title}
                                        </h4>
                                        <p className="text-xs text-gray-500 text-right">
                                            {conversation.messages.length > 0
                                                ? formatTime(conversation.messages[conversation.messages.length - 1].timestamp)
                                                : formatTime(conversation.createdAt)}
                                        </p>
                                    </div>
                                    {conversation.messages.length > 0 && (
                                        <div className="flex-shrink-0">
                                            {conversation.messages[conversation.messages.length - 1].role === 'user' ? (
                                                <User className="h-3 w-3 text-gray-500" />
                                            ) : (
                                                <Bot className="h-3 w-3 text-gray-500" />
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </aside>
        </div>
    )
}

export default ChatPage
