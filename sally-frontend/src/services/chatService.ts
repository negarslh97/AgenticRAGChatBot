import api from "./authService"

export interface ChatMessage {
  id: string
  content: string
  sender_type: 'Customer' | 'Admin' | 'SuperAdmin' | 'Guest' | 'customer' | 'admin' | 'super_admin' | 'guest' | 'ai'
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
    sources?: Array<{ title: string; id: string }>
    confidence?: number
    suggested_actions?: string[]
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
  sources: Array<{ title: string; id: string }>
  confidence: number
  suggested_actions: string[]
  message_id: string
}

export interface Conversation {
  id: string
  title: string
  tags: string[]
  created_at: string
  updated_at: string
}

export const chatService = {
  async sendMessage(content: string, conversationId?: string, guestSessionId?: string): Promise<ChatResponse> {
    // Use the same api instance that has the Authorization interceptor
    const requestData = {
      content,
      conversation_id: conversationId,
      guest_session_id: guestSessionId,
    }
    
    try {
      const response = await api.post("/api/message", requestData)
      return response.data
    } catch (error: any) {
      console.error("Chat request failed:", error)
      console.error("Error response:", error.response)
      throw error
    }
  },

  async getConversations(): Promise<Conversation[]> {
    const response = await api.get("/api/conversations")
    return response.data.conversations
  },

  async updateConversationTitle(conversationId: string, title: string): Promise<void> {
    await api.put(`/api/conversations/${conversationId}/title`, { title })
  },

  async getConversationMessages(conversationId: string, guestSessionId?: string): Promise<ChatMessage[]> {
    const params: any = {}
    if (guestSessionId) {
      params.guest_session_id = guestSessionId
    }
    const response = await api.get(`/api/conversations/${conversationId}/messages`, { params })
    return response.data.messages
  },

  // WebSocket functionality - currently disabled
  // TODO: Implement real-time chat features when needed
  /*
  createWebSocketConnection(onMessage: (data: any) => void): WebSocket {
    const ws = new WebSocket("ws://localhost:8000/api/ws")

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      onMessage(data)
    }

    ws.onerror = (error) => {
      console.error("WebSocket error:", error)
    }

    return ws
  },

  sendWebSocketMessage(ws: WebSocket, message: any) {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message))
    }
  },
  */

  async rateMessage(messageId: string, rating: number, comment?: string): Promise<void> {
    await api.post(`/api/messages/${messageId}/rate`, {
      rating,
      comment
    })
  },

  async getConversationRatingStats(conversationId: string): Promise<{
    conversation_id: string
    rating_stats: {
      total_rated_messages: number
      average_rating: number
      rating_distribution: { [key: number]: number }
      total_ratings: number
    }
  }> {
    const response = await api.get(`/api/conversations/${conversationId}/rating-stats`)
    return response.data
  },
}
