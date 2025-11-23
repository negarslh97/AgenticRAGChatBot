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

  const handleAvatarClick = () => {
    play()
  }

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
    copiedMessageId,
    deleteConfirmId,
    showSettingsModal,
    showGoToBottomBtn,
    highlightModal,
    closeHighlightModal,
    isSidebarOpen,
    isSidebarCollapsed,
    setIsSidebarOpen,
    messagesEndRef,
    messagesContainerRef,
    textareaRef,

    // Actions
    handleSendMessage,
    handleSelectConversation,
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
    setSearchQuery,
    setSelectedConversation,
    setDeleteConfirmId,
    setNewMessage,
    setShowSettingsModal,
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

  console.log('🎯 SuperAdminChatPage - selectedConversation:', selectedConversation)

  // Wrapper function for ConversationSidebar
  const handleSetSelectedConversation = async (conv: any) => {
    handleSelectConversation(conv)
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
    <div className="flex flex-col h-[calc(100vh-170px)] bg-gray-50">
      {/* Header with Black Cat Avatar */}
      <div className="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="relative">
            <img
              src={BlackCatImage}
              alt="سالی"
              className="h-8 w-8 rounded-full cursor-pointer object-cover hover:scale-105 transition-transform duration-200"
              onClick={handleAvatarClick}
            />
            <div className="absolute -bottom-1 -right-1 h-3 w-3 bg-green-500 border-2 border-white rounded-full"></div>
          </div>
          <div>
            <h1 className="font-semibold text-gray-900">سالی</h1>
            <p className="text-xs text-gray-500">آنلاین</p>
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
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
          copiedMessageId={copiedMessageId}
          copyMessage={copyMessage}
          retryMessage={retryMessage}
          regenerateMessage={regenerateMessage}
          handleSourceClick={handleSourceClick}
          FEATURE_FLAGS={FEATURE_FLAGS}
        />
      </div>

      {/* Article Highlight Modal */}
      {highlightModal.isOpen && (
        <ArticleHighlightModal
          articleId={highlightModal.articleId}
          userQuery={highlightModal.userQuery}
          onClose={closeHighlightModal}
        />
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
