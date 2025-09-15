import axios from "axios"
import api from "./authService"

const API_BASE_URL = "http://localhost:8000"

export interface ChatMessage {
  id: string
  content: string
  is_from_user: boolean
  created_at: string
  metadata?: {
    sources?: Array<{ title: string; id: string }>
    confidence?: number
    suggested_actions?: string[]
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
      const response = await api.post("/chat/message", requestData)
      return response.data
    } catch (error: any) {
      console.error("Chat request failed:", error)
      console.error("Error response:", error.response)
      throw error
    }
  },

  async getConversations(): Promise<Conversation[]> {
    const response = await api.get("/chat/conversations")
    return response.data.conversations
  },

  async updateConversationTitle(conversationId: string, title: string): Promise<void> {
    await api.put(`/chat/conversations/${conversationId}/title`, { title })
  },

  async getConversationMessages(conversationId: string, guestSessionId?: string): Promise<ChatMessage[]> {
    const params = guestSessionId ? { guest_session_id: guestSessionId } : {}
    const response = await api.get(`/chat/conversations/${conversationId}/messages`, { params })
    return response.data.messages
  },

  createWebSocketConnection(onMessage: (data: any) => void): WebSocket {
    const ws = new WebSocket("ws://localhost:8000/chat/ws")

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
}
