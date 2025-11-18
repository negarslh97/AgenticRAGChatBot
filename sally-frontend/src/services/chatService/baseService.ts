import api from "../authService"
import { 
  ChatResponse, 
  Conversation, 
  ChatMessage, 
  SendMessageData,
  RatingStats,
  AdvancedAgenticMessageData,
  AdvancedAgenticResponse
} from './types'

export class ChatBaseService {
  async sendMessage(data: SendMessageData): Promise<ChatResponse> {
    const requestData = {
      content: data.content,
      conversation_id: data.conversation_id,
      guest_session_id: data.guest_session_id,
      rag_type: data.rag_type || 'simple',
      ...(data.model && { model: data.model }),
      ...(data.temperature !== undefined && { temperature: data.temperature }),
    }
    
    try {
      const response = await api.post("/api/message", requestData)
      return response.data
    } catch (error: any) {
      console.error("Chat request failed:", error)
      console.error("Error response:", error.response)
      throw error
    }
  }

  async sendAdminMessage(content: string, conversationId?: string, ragType: 'simple' | 'agentic' = 'simple', model?: string, temperature?: number): Promise<ChatResponse> {
    const requestData = {
      content,
      conversation_id: conversationId,
      rag_type: ragType,
      ...(model && { model }),
      ...(temperature !== undefined && { temperature }),
    }
    
    try {
      const response = await api.post("/api/admin/message", requestData)
      return response.data
    } catch (error: any) {
      console.error("Admin chat request failed:", error)
      console.error("Error response:", error.response)
      throw error
    }
  }

  async getConversations(): Promise<Conversation[]> {
    const response = await api.get("/api/conversations")
    return response.data.conversations
  }

  async getConversation(conversationId: string): Promise<Conversation> {
    const response = await api.get(`/api/conversations/${conversationId}`)
    return response.data
  }

  async deleteConversation(conversationId: string): Promise<void> {
    await api.delete(`/api/conversations/${conversationId}`)
  }

  async updateConversationTitle(conversationId: string, title: string): Promise<void> {
    await api.put(`/api/conversations/${conversationId}/title`, { title })
  }

  async getConversationMessages(conversationId: string, guestSessionId?: string): Promise<ChatMessage[]> {
    const params: any = {}
    if (guestSessionId) {
      params.guest_session_id = guestSessionId
    }
    const response = await api.get(`/api/conversations/${conversationId}/messages`, { params })
    return response.data.messages
  }

  async rateMessage(messageId: string, rating: number, comment?: string): Promise<void> {
    await api.post(`/api/messages/${messageId}/rate`, {
      rating,
      comment
    })
  }

  async getConversationRatingStats(conversationId: string): Promise<RatingStats> {
    const response = await api.get(`/api/conversations/${conversationId}/rating-stats`)
    return response.data
  }

  async sendAdvancedAgenticMessage(data: AdvancedAgenticMessageData): Promise<AdvancedAgenticResponse> {
    const requestData = {
      query: data.query,
      conversation_id: data.conversation_id,
      max_iterations: data.max_iterations || 3,
      min_confidence: data.min_confidence || 0.7,
    }
    
    try {
      const response = await api.post("/api/advanced-agentic", requestData)
      return response.data
    } catch (error: any) {
      console.error("Advanced Agentic RAG request failed:", error)
      console.error("Error response:", error.response)
      throw error
    }
  }
}