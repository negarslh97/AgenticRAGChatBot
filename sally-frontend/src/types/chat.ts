// Chat types shared across SallyBot frontend

/** Represents a single chat message. */
export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  // Optional classification of the sender (used for UI badges, etc.)
  sender_type?:
  | 'Customer'
  | 'Admin'
  | 'SuperAdmin'
  | 'Guest'
  | 'customer'
  | 'admin'
  | 'super_admin'
  | 'guest'
  | 'ai'
  | 'AI';
  // UI flags for error handling and thinking state
  is_failed?: boolean;
  failure_reason?: string;
  isThinking?: boolean;
  // Rating information (if the user rates the response)
  rating?: {
    rating: number;
    comment?: string;
    rated_by?: string;
    rated_at?: string;
  };
  // Rich metadata returned from the backend (model, sources, etc.)
  metadata?: {
    model_name?: string;
    provider?: string;
    confidence?: number;
    rag_type?: 'simple' | 'agentic';
    can_get_more_details?: boolean;
    sources?: Array<{
      id: string;
      title: string;
      score: number;
      category?: string;
      tags?: string[];
    }>;
    suggested_actions?: string[];
    token_usage?: {
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
    };
    // Additional fields used by the streaming UI
    model?: string;
    temperature?: number;
  };
  // Convenience shortcuts for UI rendering (duplicate of metadata fields for easier access)
  sources?: Array<{ title: string; id: string }>;
  confidence?: number;
  suggested_actions?: string[];
}

/** Stream events emitted by the backend streaming endpoint. */
export type StreamEvent =
  | { type: 'init'; conversation_id: string }
  | { type: 'chunk'; content?: string }
  | {
    type: 'complete';
    message_id: string;
    full_response: string;
    sources?: any;
    confidence?: number;
    suggested_actions?: string[];
    rag_type?: 'simple' | 'agentic';
    model?: string;
    temperature?: number;
    conversation_id?: string;
  }
  | { type: 'error'; message: string };

/** A conversation aggregates a list of messages under a title. */
export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  created_at?: string;
  updated_at?: string;
}

/** Global state exposed by the useChatPage hook. */
export interface ChatState {
  conversations: Conversation[];
  selectedConversation: Conversation | null;
  newMessage: string;
  isLoading: boolean;
  isInitialLoading: boolean;
  searchQuery: string;
  editingTitle: string | null;
  newTitle: string;
  guestSessionId: string | null;
}

/** Actions (functions) exposed by the useChatPage hook. */
export interface ChatActions {
  handleSendMessage: () => Promise<void>;
  handleNewChat: () => void;
  handleSelectConversation: (conversation: Conversation) => Promise<void>;
  handleTitleEdit: (conversationId: string, currentTitle: string) => void;
  handleTitleSave: (conversationId: string) => Promise<void>;
  handleTitleCancel: () => void;
  handleDeleteConversation: (conversationId: string) => Promise<void>;
  handleKeyPress: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  setNewMessage: (message: string | ((prev: string) => string)) => void;
  setSearchQuery: (query: string) => void;
  setEditingTitle: (id: string | null) => void;
  setNewTitle: (title: string) => void;
  loadConversations: () => Promise<void>;
  loadConversationMessages: (conversationId: string) => Promise<Message[]>;
  formatTime: (date: Date) => string;
  scrollToBottom: () => void;
  copyMessage: (messageId: string, content: string) => void;
  retryMessage: (messageId: string) => void;
  regenerateMessage: (messageId: string) => void;
}
