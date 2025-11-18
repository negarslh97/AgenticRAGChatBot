export interface ChatMessage {
  id: string
  content: string
  sender_type: 'Customer' | 'Admin' | 'SuperAdmin' | 'Guest' | 'AI'
  sender_id?: string
  is_failed?: boolean
  failure_reason?: string
  rating?: {
    rating: number
    comment?: string
    rated_by?: string
    rated_at?: string
  }
  created_at: string
  metadata?: {
    sources?: Array<{
      id: string
      title: string
      score: number
      category?: string
      tags?: string[]
    }>
    confidence?: number
    suggested_actions?: string[]
    rag_type?: 'simple' | 'agentic'
    can_get_more_details?: boolean
    model_name?: string
    provider?: string
    token_usage?: {
      prompt_tokens?: number
      completion_tokens?: number
      total_tokens?: number
    }
    processing_details?: {
      retrieval_method?: string
      knowledge_base_used?: boolean
      fallback_used?: boolean
    }
  }
}

export interface ChatResponse {
  conversation_id: string
  message: string
  sources: Array<{
    id: string
    title: string
    score: number
    category?: string
    tags?: string[]
  }>
  confidence: number
  suggested_actions: string[]
  message_id: string
  metadata?: {
    rag_type?: 'simple' | 'agentic'
    model_name?: string
    provider?: string
    token_usage?: {
      prompt_tokens?: number
      completion_tokens?: number
      total_tokens?: number
    }
  }
}

export interface Conversation {
  id: string
  title: string
  tags?: string[]
  created_at?: string
  updated_at?: string
  rag_type?: 'simple' | 'agentic'
  model_name?: string
  temperature?: number
  type?: string
}

export interface StreamEvent {
  type: 'conversation_id' | 'chunk' | 'metadata' | 'done' | 'error' | 'init' | 'complete'
  content?: string
  conversation_id?: string
  message_id?: string
  sources?: Array<{
    id: string
    title: string
    score: number
    category?: string
    tags?: string[]
    snippet?: string
  }>
  confidence?: number
  actions_taken?: string[]
  suggested_actions?: string[]
  message?: string
  complexity?: string
  metadata?: {
    rag_type?: 'simple' | 'agentic'
    [key: string]: any
  }
}

export interface SendMessageData {
  content: string
  conversation_id?: string | null
  guest_session_id?: string | null
  rag_type?: 'simple' | 'agentic'
  model?: string
  temperature?: number
}

export interface AdvancedAgenticMessageData {
  query: string
  conversation_id?: string | null
  max_iterations?: number
  min_confidence?: number
}

export interface ModelInfo {
  id: string
  name: string
  provider: string
  description: string
  category: string
  speed?: string
  empty_chunks?: string
  max_tokens: number
  temperature: number
  supports_streaming: boolean
  supports_json: boolean
}

export interface AvailableModelsResponse {
  models: ModelInfo[]
  categories: {
    fastest: ModelInfo[]
    free: ModelInfo[]
    openai: ModelInfo[]
    heavy: ModelInfo[]
    ollama: ModelInfo[]
    other: ModelInfo[]
  }
  default_model: string
  total_count: number
}

export interface RatingStats {
  conversation_id: string
  rating_stats: {
    total_rated_messages: number
    average_rating: number
    rating_distribution: { [key: number]: number }
    total_ratings: number
  }
}

export interface AdvancedAgenticResponse {
  conversation_id: string
  response: string
  sources: Array<{
    id: string
    title: string
    score: number
    category?: string
    tags?: string[]
    snippet?: string
  }>
  confidence: number
  suggested_actions: string[]
  complexity: string
  actions_taken: string[]
  conversation_context?: any
  final_state?: any
}