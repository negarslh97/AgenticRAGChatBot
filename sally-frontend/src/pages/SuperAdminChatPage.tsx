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
import { useAudio } from '../hooks/useAudio'
import { X } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Textarea } from '../components/ui/textarea'
import { MarkdownRenderer } from '../components/ui/markdown-renderer'
import { VoiceInput } from '../components/ui/voice-input'
import { chatService } from '../services/chatService'
import { useAuth } from '../context/AuthContext'
import { toast } from 'react-hot-toast'
import ArticleHighlightModal from '../components/ArticleHighlightModal'
import BlackCatImage from '../assets/Black-Cat.png'
import meowSound from '../assets/meow.mp3'
import { MODELS_CONFIG, getDefaultModel, getModelById } from '../config/models'
import { useSuperAdminChat } from '../hooks/useSuperAdminChat'
import MessageBubble from '../components/chat/MessageBubble'
import ConversationSidebar from '../components/chat/ConversationSidebar'
import ChatContainer from '../components/chat/ChatContainer'
import SettingsModal from '../components/chat/SettingsModal'

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

const SuperAdminChatPage = () => {
  const { play } = useAudio(meowSound)
  
  const FEATURE_FLAGS = {
    SHOW_SETTINGS: true,
    SHOW_VOICE_INPUT: false
  }

  const { user } = useAuth()
  
  // Custom hook for chat functionality
  const {
    conversations,
    selectedConversation,
    newMessage,
    isLoading,
    isInitialLoading,
    searchQuery,
    modelSearchQuery,
    ragType,
    selectedModel,
    availableModels,
    temperature,
    isThinking,
    typewriterMessages,
    copiedMessageId,
    deleteConfirmId,
    showSettingsModal,
    showGoToBottomBtn,
    highlightModal,
    isSidebarOpen,
    isSidebarCollapsed,
    setIsSidebarOpen,
    messagesEndRef,
    messagesContainerRef,
    textareaRef,
    selectedArticle,
    
    // Actions
    handleSendMessage,
    handleKeyPress,
    deleteConversation,
    copyMessage,
    retryMessage,
    regenerateMessage,
    createNewConversation,
    toggleSidebar,
    toggleSidebarCollapse,
    handleScroll,
    handleGoToBottom,
    loadConversations,
    loadAvailableModels,
    formatTime,
    getRagTypeIcon,
    getRagTypeLabel,
    handleSourceClick,
    streamContentGradually,
    setSearchQuery,
    setSelectedConversation,
    setDeleteConfirmId,
    setNewMessage,
    setShowSettingsModal,
    setSelectedArticle,
    setSelectedModel,
    setTemperature,
    setRagType
  } = useSuperAdminChat({
    user,
    FEATURE_FLAGS,
    MODELS_CONFIG,
    getDefaultModel,
    getModelById,
    toast,
    chatService
  })

  // Wrapper function for ConversationSidebar
  const handleSetSelectedConversation = async (conv: any) => {
    setSelectedConversation(conv)
  }

  // Keyboard shortcuts handler
  useEffect(() => {
    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return
      }

      if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
        e.preventDefault()
        toggleSidebar()
      }

      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault()
        createNewConversation()
      }

      if (FEATURE_FLAGS.SHOW_SETTINGS && (e.ctrlKey || e.metaKey) && e.key === ',') {
        e.preventDefault()
        setShowSettingsModal(true)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [toggleSidebar, createNewConversation, setShowSettingsModal, FEATURE_FLAGS.SHOW_SETTINGS])

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

  // Focus management for settings modal
  useEffect(() => {
    if (showSettingsModal && FEATURE_FLAGS.SHOW_SETTINGS) {
      const firstInput = document.querySelector('button, input, select') as HTMLElement
      if (firstInput) {
        setTimeout(() => firstInput.focus(), 100)
      }
    }
  }, [showSettingsModal, FEATURE_FLAGS.SHOW_SETTINGS])

  // Load data on mount
  useEffect(() => {
    if (user?.id) {
      loadConversations()
      loadAvailableModels()
    }
  }, [user?.id, loadConversations, loadAvailableModels])

  return (
    <div className="flex h-[calc(100vh-170px)] bg-gray-50">
      {/* Sidebar */}
      <ConversationSidebar
        conversations={conversations}
        selectedConversation={selectedConversation}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        isSidebarOpen={isSidebarOpen}
        isSidebarCollapsed={isSidebarCollapsed}
        toggleSidebar={toggleSidebar}
        toggleSidebarCollapse={toggleSidebarCollapse}
        deleteConversation={deleteConversation}
        createNewConversation={createNewConversation}
        setSelectedConversation={handleSetSelectedConversation}
        isInitialLoading={isInitialLoading}
        deleteConfirmId={deleteConfirmId}
        setDeleteConfirmId={setDeleteConfirmId}
      />

      {/* Main Chat Area */}
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

      {/* Article Modal */}
      {selectedArticle && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-4xl max-h-[80vh] w-full flex flex-col">
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
            
            <div className="flex-1 overflow-y-auto p-4">
              <MarkdownRenderer 
                content={selectedArticle.content}
                variant="default"
              />
            </div>
            
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

export default SuperAdminChatPage
