import { StreamEvent } from './types'

export class ChatStreamingService {
  // rate limiting variables removed because they caused data loss for non-chunk events

  async sendMessageStream(
    content: string,
    conversationId: string | undefined,
    guestSessionId: string | undefined,
    onEvent: (evt: StreamEvent) => void,
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

    return this._handleStreamRequest("/api/message/stream", payload, controller, onEvent)
  }

  async sendAdminMessageStream(
    conversationId: string | undefined,
    content: string,
    ragType: 'simple' | 'agentic',
    onEvent: (evt: StreamEvent) => void,
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


    return this._handleStreamRequest("/api/admin/message/stream", payload, controller, onEvent)
  }

  async sendAdvancedAgenticMessageStream(
    query: string,
    conversationId: string | undefined,
    onEvent: (evt: StreamEvent) => void
  ): Promise<{ abort: () => void }> {
    const controller = new AbortController()

    const payload = {
      query,
      conversation_id: conversationId,
    }

    return this._handleStreamRequest("/api/advanced-agentic/stream", payload, controller, onEvent)
  }

  // 🔥 Shared helper method to handle SSE logic correctly without code duplication
  private async _handleStreamRequest(
    url: string,
    payload: any,
    controller: AbortController,
    onEvent: (evt: StreamEvent) => void
  ): Promise<{ abort: () => void }> {
    const token = localStorage.getItem("token")

    try {
      const response = await fetch(url, {
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

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })

        // Split by double newline (standard SSE delimiter)
        const parts = buffer.split("\n\n")
        // Keep the last part in buffer as it might be incomplete
        buffer = parts.pop() || ""

        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith("data:")) continue
          
          // Safe regex replacement to handle "data:" or "data: "
          const jsonStr = line.replace(/^data:\s*/, "")
          
          if (!jsonStr || jsonStr === "[DONE]") continue // Skip empty or DONE signals if sent raw

          try {
            const evt = JSON.parse(jsonStr)
            // 🔥 No throttling here to ensure init/sources/metadata are never lost
            onEvent(evt)
          } catch (e) {
            console.error("Error parsing SSE JSON:", e, jsonStr)
          }
        }
      }
    } catch (e: any) {
      if (e.name === 'AbortError') {
        console.log('Stream aborted by user')
      } else {
        console.error('Stream error:', e)
        onEvent({ type: "error", message: e?.message || String(e) })
      }
    }

    return { abort: () => controller.abort() }
  }
}