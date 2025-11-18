import { StreamEvent } from './types'

export class ChatStreamingService {
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
          
          console.log("📦 Received chunk:", value?.length, "bytes")
          
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

    console.log('🚀 Sending admin message:', { 
      conversationId, 
      content: content.substring(0, 50), 
      ragType, 
      model, 
      temperature 
    })

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
  }
}