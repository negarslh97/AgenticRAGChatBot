import React, { useState, useRef, useEffect } from 'react'
import { Search, Plus, Trash2, ChevronLeft, ChevronRight, BookOpen, Brain, X } from 'lucide-react'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Conversation as BaseConversation } from '../../types/chat'

// Extended conversation type that includes API properties
interface ExtendedConversation extends BaseConversation {
  rag_type?: 'simple' | 'agentic'
  model_name?: string
  temperature?: number
  type?: string
}

interface ConversationSidebarProps {
  conversations: ExtendedConversation[]
  selectedConversation: ExtendedConversation | null
  searchQuery: string
  setSearchQuery: (query: string) => void
  isSidebarOpen: boolean
  isSidebarCollapsed: boolean
  toggleSidebar: () => void
  toggleSidebarCollapse: () => void
  deleteConversation: (convId: string) => void
  createNewConversation: () => void
  setSelectedConversation: (conv: ExtendedConversation | null) => Promise<void>
  isInitialLoading: boolean
  deleteConfirmId: string | null
  setDeleteConfirmId: (id: string | null) => void
}

const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  conversations,
  selectedConversation,
  searchQuery,
  setSearchQuery,
  isSidebarOpen,
  isSidebarCollapsed,
  toggleSidebar,
  toggleSidebarCollapse,
  deleteConversation,
  createNewConversation,
  setSelectedConversation,
  isInitialLoading,
  deleteConfirmId,
  setDeleteConfirmId
}) => {
  const sidebarRef = useRef<HTMLDivElement>(null)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024)
    }
    
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  const filteredConversations = conversations.filter(conv =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getRagTypeIcon = (type?: string) => {
    switch (type) {
      case 'simple':
        return <BookOpen className="w-4 h-4 text-green-600" />
      case 'agentic':
        return <Brain className="w-4 h-4 text-purple-600" />
      default:
        return <BookOpen className="w-4 h-4 text-gray-600" />
    }
  }

  const formatTime = (dateString?: string) => {
    if (!dateString) return ''
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('fa-IR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date)
  }

  const handleDeleteClick = (convId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (deleteConfirmId === convId) {
      deleteConversation(convId)
    } else {
      setDeleteConfirmId(convId)
    }
  }

  if (!isSidebarOpen && isMobile) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden" onClick={toggleSidebar}>
        <div className="absolute left-0 top-0 h-full w-80 bg-white shadow-xl" onClick={e => e.stopPropagation()}>
          <ConversationSidebar
            conversations={conversations}
            selectedConversation={selectedConversation}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            isSidebarOpen={true}
            isSidebarCollapsed={isSidebarCollapsed}
            toggleSidebar={toggleSidebar}
            toggleSidebarCollapse={toggleSidebarCollapse}
            deleteConversation={deleteConversation}
            createNewConversation={createNewConversation}
            setSelectedConversation={setSelectedConversation}
            isInitialLoading={isInitialLoading}
            deleteConfirmId={deleteConfirmId}
            setDeleteConfirmId={setDeleteConfirmId}
          />
        </div>
      </div>
    )
  }

  return (
    <div
      ref={sidebarRef}
      className={`
        ${isSidebarCollapsed ? 'w-16' : 'w-80'} 
        ${isMobile && !isSidebarOpen ? '-translate-x-full' : 'translate-x-0'}
        transition-all duration-300 ease-in-out
        bg-white border-r border-gray-200
        flex flex-col
        h-full
        z-30
        relative
      `}
    >
      {/* Sidebar Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-white" />
            </div>
            {!isSidebarCollapsed && (
              <h1 className="text-lg font-semibold text-gray-900">گفتگوها</h1>
            )}
          </div>
          
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleSidebarCollapse}
              className="p-1.5 h-8 w-8"
              title={isSidebarCollapsed ? "باز کردن" : "بستن"}
            >
              {isSidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
            </Button>
            
            {isMobile && (
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleSidebar}
                className="p-1.5 h-8 w-8"
                title="بستن"
              >
                <X className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>

        {/* Search */}
        {!isSidebarCollapsed && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <Input
              type="text"
              placeholder="جستجوی گفتگوها..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-4 py-2 text-sm border-gray-200 focus:border-purple-500 focus:ring-purple-500"
            />
          </div>
        )}

        {/* New Chat Button */}
        <Button
          onClick={createNewConversation}
          className={`
            mt-4 w-full 
            ${isSidebarCollapsed ? 'justify-center p-2' : 'justify-start px-3 py-2'}
            bg-gradient-to-r from-purple-600 to-blue-600 
            hover:from-purple-700 hover:to-blue-700
            text-white
            transition-all duration-200
            flex items-center gap-2
          `}
        >
          <Plus className="w-4 h-4" />
          {!isSidebarCollapsed && <span>گفتگوی جدید</span>}
        </Button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto">
        {isInitialLoading ? (
          <div className="p-4 space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        ) : filteredConversations.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            {searchQuery ? 'هیچ گفتگویی یافت نشد' : 'هنوز گفتگویی وجود ندارد'}
          </div>
        ) : (
          <div className="p-2 space-y-1">
            {filteredConversations.map((conversation) => (
              <div
                key={conversation.id}
                onClick={async () => {
                  try {
                    await setSelectedConversation(conversation)
                  } catch (error) {
                    console.error('Error selecting conversation:', error)
                  }
                }}
                className={`
                  group relative p-3 rounded-lg cursor-pointer transition-all duration-200
                  ${selectedConversation?.id === conversation.id
                    ? 'bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200'
                    : 'hover:bg-gray-50'
                  }
                `}
              >
                {/* Conversation Content */}
                <div className="flex items-start gap-2">
                  <div className="flex-shrink-0 mt-0.5">
                    {getRagTypeIcon(conversation.rag_type)}
                  </div>
                  
                  <div className={`flex-1 min-w-0 ${isSidebarCollapsed ? 'hidden' : 'block'}`}>
                    <div className="flex items-center justify-between mb-1">
                      <h3 className={`text-sm font-medium truncate ${
                        selectedConversation?.id === conversation.id
                          ? 'text-purple-900'
                          : 'text-gray-900'
                      }`}>
                        {conversation.title || 'گفتگوی بدون عنوان'}
                      </h3>
                      {conversation.updated_at && (
                        <span className="text-xs text-gray-500 whitespace-nowrap">
                          {formatTime(conversation.updated_at)}
                        </span>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        conversation.rag_type === 'agentic'
                          ? 'bg-purple-100 text-purple-700'
                          : 'bg-green-100 text-green-700'
                      }`}>
                        {conversation.rag_type === 'agentic' ? 'عامل' : 'ساده'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Delete Button */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => handleDeleteClick(conversation.id, e)}
                  className={`
                    absolute top-2 right-2 p-1 h-6 w-6
                    opacity-0 group-hover:opacity-100 transition-opacity
                    ${deleteConfirmId === conversation.id ? 'text-red-600' : 'text-gray-400 hover:text-red-600'}
                  `}
                  title={deleteConfirmId === conversation.id ? 'تأیید حذف' : 'حذف'}
                >
                  <Trash2 className="w-3 h-3" />
                </Button>

                {/* Delete Confirmation */}
                {deleteConfirmId === conversation.id && (
                  <div className="absolute top-8 right-2 bg-red-50 border border-red-200 rounded-md p-2 shadow-lg z-10">
                    <p className="text-xs text-red-700 mb-1">برای تأیید دوباره کلیک کنید</p>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDeleteConfirmId(null)}
                      className="text-xs text-red-600 hover:text-red-700"
                    >
                      انصراف
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Sidebar Footer */}
      {!isSidebarCollapsed && (
        <div className="p-4 border-t border-gray-200">
          <div className="text-xs text-gray-500 text-center">
            {conversations.length} گفتگو
          </div>
        </div>
      )}
    </div>
  )
}

export default ConversationSidebar