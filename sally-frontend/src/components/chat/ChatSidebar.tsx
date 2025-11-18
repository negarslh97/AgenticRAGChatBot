import React from 'react'
import { Button } from '../ui/button'
import { Plus, Search, User, Bot, Trash2 } from 'lucide-react'
import type { Conversation } from '../../types/chat'

interface ChatSidebarProps {
  conversations: Conversation[]
  selectedConversation: Conversation | null
  searchQuery: string
  editingTitle: string | null
  newTitle: string
  isInitialLoading: boolean
  onNewChat: () => void
  onSearchChange: (query: string) => void
  onSelectConversation: (conversation: Conversation) => void
  onTitleEdit: (conversationId: string, currentTitle: string) => void
  onTitleSave: (conversationId: string) => void
  onTitleCancel: () => void
  onDeleteConversation: (conversationId: string) => void
  onNewTitleChange: (title: string) => void
  formatTime: (date: Date) => string
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  conversations,
  selectedConversation,
  searchQuery,
  editingTitle,
  newTitle,
  isInitialLoading,
  onNewChat,
  onSearchChange,
  onSelectConversation,
  onTitleEdit,
  onTitleSave,
  onTitleCancel,
  onDeleteConversation,
  onNewTitleChange,
  formatTime
}) => {
  const filteredConversations = conversations.filter(conversation =>
    conversation.title.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <aside className="flex flex-col bg-white shadow-lg transition-all duration-300 w-80 overflow-hidden">
      <div className="p-4 bg-white shadow-sm">
        <Button 
          onClick={onNewChat} 
          className="w-full justify-end flex items-center gap-2 bg-blue-600 hover:bg-blue-700"
        >
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
            onChange={(e) => onSearchChange(e.target.value)}
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
              onClick={() => onSelectConversation(conversation)}
            >
              <div className="flex items-start gap-2">
                <div className="flex-1 min-w-0">
                  {editingTitle === conversation.id ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={newTitle}
                        onChange={(e) => onNewTitleChange(e.target.value)}
                        onKeyPress={(e) => {
                          if (e.key === 'Enter') onTitleSave(conversation.id)
                          if (e.key === 'Escape') onTitleCancel()
                        }}
                        className="flex-1 text-sm border border-gray-300 rounded px-2 py-1 text-right"
                        autoFocus
                      />
                      <button
                        onClick={() => onTitleSave(conversation.id)}
                        className="text-green-600 hover:text-green-800"
                      >
                        ✓
                      </button>
                      <button
                        onClick={onTitleCancel}
                        className="text-red-600 hover:text-red-800"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <h4
                      className="font-medium text-gray-900 truncate text-right cursor-pointer hover:text-blue-600"
                      onDoubleClick={() => onTitleEdit(conversation.id, conversation.title)}
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
                        onDeleteConversation(conversation.id)
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
  )
}