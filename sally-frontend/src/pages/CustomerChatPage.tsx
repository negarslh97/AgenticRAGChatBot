'use client'

import React, { useRef, useEffect, useState, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'
import { useChatPage } from '../hooks/useChatPage'
import ChatContainer from '../components/chat/ChatContainer'
import ConversationSidebar from '../components/chat/ConversationSidebar'
import SettingsModal from '../components/chat/SettingsModal'
import { chatService } from '../services/chatService'
import { getDefaultModel } from '../config/models'
import { toast } from 'react-hot-toast'

// Skeleton Loader Component
const SkeletonLoader = (): JSX.Element => (
  <div className="flex items-start space-x-2 space-x-reverse p-3">
    <div className="w-8 h-8 md:w-10 md:h-10 rounded-full shimmer dark:shimmer flex-shrink-0"></div>
    <div className="flex-1 space-y-2 min-w-0">
      <div className="h-4 shimmer dark:shimmer rounded w-3/4 animate-pulse"></div>
      <div className="h-4 shimmer dark:shimmer rounded w-1/2 animate-pulse"></div>
      <div className="h-4 shimmer dark:shimmer rounded w-2/3 animate-pulse"></div>
    </div>
  </div>
)

// Typewriter Cursor Component
const TypewriterCursor = (): JSX.Element => (
  <span className="inline-block w-2 h-4 bg-current animate-pulse ml-0.5"></span>
)

const CustomerChatPage = () => {
  const { user } = useAuth()
  
  const FEATURE_FLAGS = {
    SHOW_SETTINGS: true,
    SHOW_VOICE_INPUT: false
  }

  // Use the chat page hook
  const {
    conversations,
    selectedConversation,
    newMessage,
    isLoading,
    isInitialLoading,
    searchQuery,
    editingTitle,
    newTitle,
    guestSessionId,
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
    regenerateMessage
  } = useChatPage()

  // Refs for chat container
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Settings state
  const [selectedModel, setSelectedModel] = useState<string>(() => {
    const saved = localStorage.getItem('customer_selectedModel')
    return saved || getDefaultModel('chat')
  })
  const [temperature, setTemperature] = useState<number>(() => {
    const saved = localStorage.getItem('customer_temperature')
    return saved ? parseFloat(saved) : 0.7
  })
  const [ragType, setRagType] = useState<'simple' | 'agentic'>(() => {
    const saved = localStorage.getItem('customer_ragType')
    return (saved as 'simple' | 'agentic') || 'agentic'
  })
  const [availableModels, setAvailableModels] = useState<any[]>([])
  const [showSettingsModal, setShowSettingsModal] = useState(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)

  // Load available models
  const loadAvailableModels = useCallback(async () => {
    try {
      const modelData = await chatService.getAvailableModels()
      setAvailableModels(modelData.models || [])
      
      const defaultModel = modelData.default_model || getDefaultModel('chat')
      if (!modelData.models.find((m: any) => m.id === selectedModel)) {
        setSelectedModel(defaultModel)
      }
    } catch (error) {
      console.error('Failed to load models:', error)
      setAvailableModels([])
    }
  }, [selectedModel])

  // Save settings to localStorage
  useEffect(() => {
    localStorage.setItem('customer_selectedModel', selectedModel)
  }, [selectedModel])

  useEffect(() => {
    localStorage.setItem('customer_temperature', temperature.toString())
  }, [temperature])

  useEffect(() => {
    localStorage.setItem('customer_ragType', ragType)
  }, [ragType])

  // Load models on mount
  useEffect(() => {
    loadAvailableModels()
  }, [loadAvailableModels])

  // Default values for missing props
  const isThinking = false
  const showGoToBottomBtn = false
  const getRagTypeIcon = () => '🤖'
  const getRagTypeLabel = (type: string) => {
    switch (type) {
      case 'simple': return 'ساده'
      case 'agentic': return 'هوشمند'
      case 'detailed': return 'تفصیلی'
      default: return 'پیش‌فرض'
    }
  }
  const streamContentGradually = () => {}
  const typewriterMessages = {}
  const copiedMessageId = null
  const handleSourceClick = () => {}
  const handleScroll = () => {}
  const handleGoToBottom = () => {}

  // Initialize on mount
  useEffect(() => {
    if (user?.id) {
      loadConversations()
    }
  }, [user?.id, loadConversations])

  // Wrapper for async conversation selection
  const handleConversationSelect = useCallback(async (conv: any) => {
    if (conv) {
      await handleSelectConversation(conv)
    } else {
      handleNewChat()
    }
  }, [handleSelectConversation, handleNewChat])

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-white to-purple-50/30 border-b border-purple-100 px-6 py-4 shadow-sm backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-600 via-blue-600 to-purple-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-purple-500/30 transform hover:scale-105 transition-transform duration-200">
                <span className="text-base font-bold">S</span>
              </div>
              <div className="absolute -bottom-1 -right-1 w-3.5 h-3.5 bg-green-500 border-2 border-white rounded-full shadow-sm"></div>
            </div>
            <div className="flex flex-col">
              <h1 className="text-xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
                چت با Sally
              </h1>
              <p className="text-xs text-gray-500 mt-0.5 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
                دستیار هوشمند پیشرفته
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 px-4 py-2 bg-white/80 backdrop-blur-sm rounded-lg border border-purple-100 shadow-sm">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-sm font-medium text-gray-700">
                {user ? user.full_name : "کاربر مهمان"}
              </span>
            </div>
            {user && user.full_name && (
              <div className="w-9 h-9 bg-gradient-to-br from-purple-100 to-blue-100 rounded-full flex items-center justify-center border-2 border-purple-200">
                <span className="text-xs font-semibold text-purple-700">
                  {user.full_name.charAt(0)}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden flex">
        {/* Sidebar */}
        <ConversationSidebar
          conversations={conversations}
          selectedConversation={selectedConversation}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          isSidebarOpen={isSidebarOpen}
          isSidebarCollapsed={isSidebarCollapsed}
          toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          toggleSidebarCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          deleteConversation={handleDeleteConversation}
          createNewConversation={handleNewChat}
          setSelectedConversation={handleConversationSelect}
          isInitialLoading={isInitialLoading}
          deleteConfirmId={deleteConfirmId}
          setDeleteConfirmId={setDeleteConfirmId}
        />

        {/* Chat Container */}
        <div className="flex-1 overflow-hidden">
          <ChatContainer
          selectedConversation={selectedConversation}
          newMessage={newMessage}
          setNewMessage={setNewMessage}
          isLoading={isLoading}
          isThinking={isThinking}
          ragType={ragType}
          selectedModel={selectedModel}
          temperature={temperature}
          availableModels={availableModels}
          handleSendMessage={handleSendMessage}
          handleKeyPress={handleKeyPress}
          messagesContainerRef={messagesContainerRef}
          messagesEndRef={messagesEndRef}
          handleScroll={handleScroll}
          handleGoToBottom={handleGoToBottom}
          showGoToBottomBtn={showGoToBottomBtn}
          showSettingsModal={showSettingsModal}
          setShowSettingsModal={setShowSettingsModal}
          textareaRef={textareaRef}
          formatTime={formatTime}
          getRagTypeIcon={getRagTypeIcon}
          getRagTypeLabel={getRagTypeLabel}
          SkeletonLoader={SkeletonLoader}
          TypewriterCursor={TypewriterCursor}
          streamContentGradually={streamContentGradually}
          typewriterMessages={typewriterMessages}
          copiedMessageId={copiedMessageId}
          copyMessage={copyMessage}
          retryMessage={retryMessage}
          regenerateMessage={regenerateMessage}
          handleSourceClick={handleSourceClick}
          FEATURE_FLAGS={FEATURE_FLAGS}
        />
        </div>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={showSettingsModal}
        onClose={() => setShowSettingsModal(false)}
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
        temperature={temperature}
        onTemperatureChange={setTemperature}
        ragType={ragType}
        onRagTypeChange={setRagType}
        availableModels={availableModels}
      />
    </div>
  )
}

export default CustomerChatPage
