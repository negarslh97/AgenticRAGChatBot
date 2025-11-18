// Chat types shared across chat components

export interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
  sender_type?: 'Customer' | 'Admin' | 'SuperAdmin' | 'Guest' | 'customer' | 'admin' | 'super_admin' | 'guest' | 'ai' | 'AI'
  is_failed?: boolean
  failure_reason?: string
  rating?: {
    rating: number
    comment?: string
    rated_by?: string
    rated_at?: string
  }
  metadata?: {
    model_name?: string
    provider?: string
    confidence?: number
    rag_type?: 'simple' | 'agentic'
    can_get_more_details?: boolean
    sources?: Array<{
      id: string
      title: string
      score: number
      category?: string
      tags?: string[]
    }>
    suggested_actions?: string[]
    token_usage?: {
      prompt_tokens?: number
      completion_tokens?: number
      total_tokens?: number
    }
  }
  sources?: Array<{ title: string; id: string }>
  confidence?: number
  suggested_actions?: string[]
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  created_at?: string
  updated_at?: string
}

export interface ChatState {
  conversations: Conversation[]
  selectedConversation: Conversation | null
  newMessage: string
  isLoading: boolean
  isInitialLoading: boolean
  searchQuery: string
  editingTitle: string | null
  newTitle: string
  guestSessionId: string | null
}

export interface ChatActions {
  handleSendMessage: () => Promise<void>
  handleNewChat: () => void
  handleSelectConversation: (conversation: Conversation) => Promise<void>
  handleTitleEdit: (conversationId: string, currentTitle: string) => void
  handleTitleSave: (conversationId: string) => Promise<void>
  handleTitleCancel: () => void
  handleDeleteConversation: (conversationId: string) => Promise<void>
  handleKeyPress: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void
  setNewMessage: (message: string | ((prev: string) => string)) => void
  setSearchQuery: (query: string) => void
  setEditingTitle: (id: string | null) => void
  setNewTitle: (title: string) => void
  loadConversations: () => Promise<void>
  loadConversationMessages: (conversationId: string) => Promise<Message[]>
  formatTime: (date: Date) => string
  scrollToBottom: () => void
  copyMessage: (messageId: string, content: string) => void
  retryMessage: (messageId: string) => void
  regenerateMessage: (messageId: string) => void
}