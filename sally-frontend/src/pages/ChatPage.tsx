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

import React, { useState } from 'react'
import { ChatHeader } from '../components/chat/ChatHeader'
import { ChatSidebar } from '../components/chat/ChatSidebar'
import { ChatInput } from '../components/chat/ChatInput'
import { WelcomeMessage } from '../components/chat/WelcomeMessage'
import { MarkdownRenderer } from '../components/ui/markdown-renderer'
import { Bot, User } from 'lucide-react'
import { useChatPage } from '../hooks/useChatPage'
import { useAudio } from '../hooks/useAudio'
import blackCatImage from '../assets/Black-Cat.png'
import meowSound from '../assets/meow.mp3'
import type { Message } from '../types/chat'

const ChatPage = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const { play } = useAudio(meowSound)

  const handleAvatarClick = () => {
    play()
  }

  const {
    conversations,
    selectedConversation,
    newMessage,
    isLoading,
    isInitialLoading,
    searchQuery,
    editingTitle,
    newTitle,
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
    formatTime
  } = useChatPage({ isDevelopment: process.env.NODE_ENV === 'development' })

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen)
  }

  const handleExampleClick = (message: string) => {
    setNewMessage(message)
    setTimeout(() => handleSendMessage(), 100)
  }

  const renderMessage = (message: Message) => (
    <div key={message.id} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
      {message.role === 'assistant' && (
        <img
          src={blackCatImage}
          alt="سالی"
          className="h-8 w-8 rounded-full cursor-pointer object-cover flex-shrink-0 hover:scale-105 transition-transform duration-200"
          onClick={handleAvatarClick}
        />
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
    </div>
  )

  return (
    <div className="flex h-[calc(100vh-8rem)] w-full bg-gray-50">
      {/* Main Content Area */}
      <main className={`flex-1 flex flex-col transition-all duration-300 ${isSidebarOpen ? 'ml-80' : 'ml-0'}`}>
        <ChatHeader 
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={toggleSidebar}
        />

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
            <WelcomeMessage onExampleClick={handleExampleClick} />
          ) : selectedConversation ? (
            <div className="space-y-4">
              {selectedConversation.messages.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <p className="text-sm">این گفتگو هنوز پیامی ندارد</p>
                  <p className="text-xs mt-1">پیام خود را در کادر پایین بنویسید</p>
                </div>
              ) : (
                selectedConversation.messages.map(renderMessage)
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <p className="text-gray-500">گفتگویی انتخاب نشده</p>
              </div>
            </div>
          )}
        </div>

        <ChatInput
          newMessage={newMessage}
          isLoading={isLoading}
          onMessageChange={setNewMessage}
          onKeyPress={handleKeyPress}
          onSendMessage={handleSendMessage}
        />
      </main>

      {/* Sidebar */}
      {isSidebarOpen && (
        <ChatSidebar
          conversations={conversations}
          selectedConversation={selectedConversation}
          searchQuery={searchQuery}
          editingTitle={editingTitle}
          newTitle={newTitle}
          isInitialLoading={isInitialLoading}
          onNewChat={handleNewChat}
          onSearchChange={setSearchQuery}
          onSelectConversation={handleSelectConversation}
          onTitleEdit={handleTitleEdit}
          onTitleSave={handleTitleSave}
          onTitleCancel={handleTitleCancel}
          onDeleteConversation={handleDeleteConversation}
          onNewTitleChange={setNewTitle}
          formatTime={formatTime}
        />
      )}
    </div>
  )
}

export default ChatPage
