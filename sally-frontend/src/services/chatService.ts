import api from "./authService"

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
    rag_type?: 'simple' | 'detailed' | 'agentic'
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
  tags: string[]
  created_at: string
  updated_at: string
  // 🆕 Conversation metadata
  rag_type?: string  // "simple" or "agentic"
  model_name?: string  // LLM model used
  temperature?: number  // Temperature setting
  type?: string  // From backend API: "Simple RAG" or "Agentic"
}

export const chatService = {
  // Base URL for API (needed for some direct fetch calls)
  API_BASE_URL: '',  // Will use relative URLs with api interceptor
  
  async sendMessage(data: { content: string; conversation_id?: string | null; guest_session_id?: string | null; rag_type?: 'simple' | 'detailed'; model?: string; temperature?: number }): Promise<ChatResponse> {
    // Use the same api instance that has the Authorization interceptor
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
  },

  async sendMessageStream(
    content: string,
    conversationId: string | undefined,
    guestSessionId: string | undefined,
    onEvent: (evt: any) => void,
    model?: string,
    temperature?: number
  ): Promise<{ abort: () => void }> {
    const controller = new AbortController()

    const payload = {
      content,
      conversation_id: conversationId,
      guest_session_id: guestSessionId,
      ...(model && { model }),
      ...(temperature !== undefined && { temperature }),
    }

    const token = localStorage.getItem("token")

    const response = await fetch("/api/message/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    })

    if (!response.ok || !response.body) {
      onEvent({ type: "error", message: `HTTP ${response.status}` })
      return { abort: () => controller.abort() }
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder("utf-8")
    let buffer = ""

    ;(async () => {
      try {
        while (true) {
          const { value, done } = await reader.read()
          if (done) break
          
          // 🔥 DEBUG: Log chunks as they arrive
          console.log("📦 Received chunk:", value?.length, "bytes")
          
          buffer += decoder.decode(value, { stream: true })

          // SSE frames are separated by \n\n and prefixed with 'data: '
          const parts = buffer.split("\n\n")
          buffer = parts.pop() || ""

          for (const part of parts) {
            const line = part.trim()
            if (!line.startsWith("data:")) continue
            const json = line.replace(/^data:\s*/, "")
            if (!json) continue
            try {
              const evt = JSON.parse(json)
              console.log("🎯 Parsed event:", evt.type, evt.content?.length || 0)
              onEvent(evt)
            } catch {
              // ignore parse errors for keep-alives
            }
          }
        }
      } catch (e: any) {
        onEvent({ type: "error", message: e?.message || String(e) })
      }
    })()

    return { abort: () => controller.abort() }
  },

  async sendAdminMessage(content: string, conversationId?: string, ragType: 'simple' | 'agentic' = 'simple', model?: string, temperature?: number): Promise<ChatResponse> {
    // Admin-specific message sending with RAG type selection (non-streaming)
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
  },

  async sendAdminMessageStream(
    conversationId: string | undefined,
    content: string,
    ragType: 'simple' | 'agentic',
    onEvent: (evt: any) => void,
    model?: string,
    temperature?: number
  ): Promise<{ abort: () => void }> {
    const controller = new AbortController()

    const payload = {
      content,
      conversation_id: conversationId,
      rag_type: ragType,
      ...(model && { model }),
      ...(temperature !== undefined && { temperature }),
    }

    console.log('🚀 Sending admin message:', { conversationId, content: content.substring(0, 50), ragType, model, temperature })

    const token = localStorage.getItem("token")

    const response = await fetch("/api/admin/message/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    })

    if (!response.ok || !response.body) {
      onEvent({ type: "error", message: `HTTP ${response.status}` })
      return { abort: () => controller.abort() }
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder("utf-8")
    let buffer = ""

    ;(async () => {
      try {
        while (true) {
          const { value, done } = await reader.read()
          if (done) break
          
          console.log("📦 Admin received chunk:", value?.length, "bytes")
          buffer += decoder.decode(value, { stream: true })

          const parts = buffer.split("\n\n")
          buffer = parts.pop() || ""

          for (const part of parts) {
            const line = part.trim()
            if (!line.startsWith("data:")) continue
            const json = line.replace(/^data:\s*/, "")
            if (!json) continue
            try {
              const evt = JSON.parse(json)
              console.log("🎯 Admin parsed event:", evt.type, evt.content?.length || 0)
              onEvent(evt)
            } catch {
              // ignore parse errors
            }
          }
        }
      } catch (e: any) {
        onEvent({ type: "error", message: e?.message || String(e) })
      }
    })()

    return { abort: () => controller.abort() }
  },

  async getConversations(): Promise<Conversation[]> {
    const response = await api.get("/api/conversations")
    return response.data.conversations
  },

  async getConversation(conversationId: string): Promise<Conversation> {
    const response = await api.get(`/api/conversations/${conversationId}`)
    return response.data
  },

  async deleteConversation(conversationId: string): Promise<void> {
    await api.delete(`/api/conversations/${conversationId}`)
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

  async sendAdvancedAgenticMessage(data: { 
    query: string; 
    conversation_id?: string | null;
    max_iterations?: number;
    min_confidence?: number;
  }): Promise<{
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
  }> {
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
  },

  async sendAdvancedAgenticMessageStream(
    query: string,
    conversationId: string | undefined,
    onEvent: (evt: any) => void
  ): Promise<{ abort: () => void }> {
    const controller = new AbortController()

    const payload = {
      query,
      conversation_id: conversationId,
    }

    const token = localStorage.getItem("token")

    ;(async () => {
      try {
        const response = await fetch("/api/advanced-agentic/stream", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(payload),
          signal: controller.signal,
        })

        if (!response.ok || !response.body) {
          onEvent({ type: "error", message: `HTTP ${response.status}` })
          return
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder("utf-8")
        let buffer = ""

        while (true) {
          const { value, done } = await reader.read()
          if (done) break
          
          buffer += decoder.decode(value, { stream: true })

          // SSE frames are separated by \n\n and prefixed with 'data: '
          const parts = buffer.split("\n\n")
          buffer = parts.pop() || ""

          for (const part of parts) {
            if (part.trim() === "") continue
            if (!part.startsWith("data: ")) continue

            const jsonStr = part.substring(6) // Remove 'data: ' prefix
            try {
              const parsed = JSON.parse(jsonStr)
              onEvent(parsed)
            } catch (err) {
              console.error("Failed to parse SSE chunk:", jsonStr, err)
            }
          }
        }
      } catch (error: any) {
        if (error.name === "AbortError") {
          console.log("Stream aborted")
        } else {
          console.error("Stream error:", error)
          onEvent({ type: "error", message: error.message })
        }
      }
    })()

    return { abort: () => controller.abort() }
  },

  async getAvailableModels(): Promise<{
    models: Array<{
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
    }>
    categories: {
      fastest: any[]
      free: any[]
      openai: any[]
      heavy: any[]
      ollama: any[]
      other: any[]
    }
    default_model: string
    total_count: number
  }> {
    try {
      const response = await api.get("/api/system/models")
      return response.data.data
    } catch (error: any) {
      console.error("Failed to get available models:", error)
      // Fallback to hardcoded models if API fails
      return {
        models: [
          { id: 'google/gemini-2.5-flash', name: 'Gemini 2.5 Flash', provider: 'Google', description: '✅ سریع‌ترین - 264 ch/s، رایگان', category: 'fastest', max_tokens: 8192, temperature: 0.2, supports_streaming: true, supports_json: true },
          { id: 'qwen/qwen3-235b-a22b:free', name: 'Qwen 3', provider: 'Alibaba', description: '✅ سریع‌ترین - 264 ch/s، رایگان', category: 'fastest', max_tokens: 8192, temperature: 0.7, supports_streaming: true, supports_json: true },
          { id: 'minimax/minimax-m2:free', name: 'MINIMAX M2', provider: 'minimax', description: 'مدل سریع MINIMAX', category: 'fastest', max_tokens: 8192, temperature: 0.7, supports_streaming: true, supports_json: true },
          { id: 'deepseek/deepseek-chat-v3.1:free', name: 'DeepSeek V3.1 (Free)', provider: 'DeepSeek', description: '✅ 117 ch/s، 0% empty، رایگان', category: 'free', max_tokens: 8192, temperature: 0.7, supports_streaming: true, supports_json: true },
          { id: 'gpt-4o-mini', name: 'GPT-4o Mini', provider: 'OpenAI', description: '✅ 89 ch/s، پایدار، کیفیت بالا', category: 'openai', max_tokens: 8192, temperature: 0.7, supports_streaming: true, supports_json: true },
          { id: 'gpt-4o', name: 'GPT-4o', provider: 'OpenAI', description: 'قدرتمندترین OpenAI', category: 'openai', max_tokens: 8192, temperature: 0.7, supports_streaming: true, supports_json: true },
          { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', provider: 'OpenAI', description: 'نسخه توربو GPT-4', category: 'openai', max_tokens: 8192, temperature: 0.7, supports_streaming: true, supports_json: true },
          { id: 'x-ai/grok-4-fast', name: 'Grok 4 Fast ⚠️', provider: 'xAI', description: '143 ch/s، اما 70% empty chunks', category: 'heavy', max_tokens: 8192, temperature: 0.7, supports_streaming: true, supports_json: true },
          { id: 'x-ai/grok-3-mini-beta', name: 'Grok 3 Mini Beta ⚠️', provider: 'xAI', description: '149 ch/s، اما 65% empty chunks', category: 'heavy', max_tokens: 8192, temperature: 0.7, supports_streaming: true, supports_json: true },
          { id: 'deepseek/deepseek-r1-0528', name: 'DeepSeek R1', provider: 'DeepSeek', description: 'مدل قدرتمند DeepSeek', category: 'other', max_tokens: 8192, temperature: 0.7, supports_streaming: true, supports_json: true },
          { id: 'qwen/qwen3-235b-a22b-2507', name: 'Qwen 3', provider: 'Qwen', description: 'مدل Alibaba', category: 'other', max_tokens: 8192, temperature: 0.7, supports_streaming: true, supports_json: true },
          { id: 'ollama:gpt-oss:20b', name: 'GPT-OSS 20B', provider: 'Ollama', description: 'مدل محلی OpenAI', category: 'ollama', max_tokens: 4096, temperature: 0.7, supports_streaming: true, supports_json: true },
          { id: 'ollama:gemma3n:e4b', name: 'Gemma 3N E4B', provider: 'Ollama', description: 'مدل محلی قدرتمند Google', category: 'ollama', max_tokens: 4096, temperature: 0.7, supports_streaming: true, supports_json: true },
          { id: 'ollama:llama3.1:8b-instruct-q4_0', name: 'Llama 3.1 8B', provider: 'Ollama', description: 'مدل محلی Meta', category: 'ollama', max_tokens: 4096, temperature: 0.7, supports_streaming: true, supports_json: true }
        ],
        categories: {
          fastest: [],
          free: [],
          openai: [],
          heavy: [],
          ollama: [],
          other: []
        },
        default_model: 'google/gemini-2.5-flash',
        total_count: 14
      }
    }
  },
}
