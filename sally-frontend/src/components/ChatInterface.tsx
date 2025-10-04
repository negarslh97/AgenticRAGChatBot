"use client"

import type React from "react"
import { useState, useEffect, useRef, useCallback } from "react"
import { useAuth } from "../context/AuthContext"
import { chatService, type ChatMessage, type ChatResponse } from "../services/chatService"
import toast from "react-hot-toast"

interface ChatInterfaceProps {
  conversationId?: string
  onNewConversation?: (conversationId: string) => void
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ conversationId, onNewConversation }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputMessage, setInputMessage] = useState("")
  const [loading, setLoading] = useState(false)
  const [guestSessionId] = useState(() => `guest_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { user } = useAuth()
  
  // Removed debug logging

  const loadConversationMessages = useCallback(async () => {
    try {
      console.log("Loading messages for conversation:", conversationId)
      if (!conversationId) {
        console.log("No conversation ID provided")
        return
      }
      
      // For guests, also pass guest session ID as query parameter
      const conversationMessages = await chatService.getConversationMessages(conversationId, user ? undefined : guestSessionId)
      
      console.log("Loaded conversation messages:", conversationMessages)
      console.log("Messages type:", typeof conversationMessages, "isArray:", Array.isArray(conversationMessages))
      console.log("Messages length:", conversationMessages?.length)
      console.log("Messages content:", JSON.stringify(conversationMessages, null, 2))
      
      // Show welcome message if no messages found
      console.log("Processing messages:", conversationMessages.length)
      if (conversationMessages.length === 0) {
        console.log("No messages found, showing welcome message")
        const welcomeMessage: ChatMessage = {
          id: "welcome",
          content: "👋 Hi! I'm Sally, your AI assistant. How can I help you today?",
          sender_type: "ai" as const,
          created_at: new Date().toISOString(),
        }
        console.log("Setting welcome message:", welcomeMessage)
        setMessages([welcomeMessage])
        console.log("Messages state after setting:", [welcomeMessage])
      } else {
        console.log("Setting conversation messages:", conversationMessages)
        setMessages(conversationMessages)
        console.log("Messages state after setting:", conversationMessages)
      }
    } catch (error) {
      console.error("Error loading conversation:", error)
      toast.error("Failed to load conversation")
    }
  }, [conversationId, user, guestSessionId])

  useEffect(() => {
    if (conversationId) {
      loadConversationMessages()
    } else {
      // Show welcome message for new conversation
      const welcomeMessage: ChatMessage = {
        id: "welcome",
        content: "👋 Hi! I'm Sally, your AI assistant. How can I help you today?",
        sender_type: "ai" as const,
        created_at: new Date().toISOString(),
      }
      setMessages([welcomeMessage])
    }
  }, [conversationId, loadConversationMessages])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    // Use requestAnimationFrame to ensure DOM is updated
    requestAnimationFrame(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    })
  }

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputMessage.trim() || loading) return

    const userMessage: ChatMessage = {
      id: `temp_${Date.now()}`,
      content: inputMessage,
        sender_type: user ? "Customer" : "Guest" as const,
      created_at: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputMessage("")
    setLoading(true)

    try {
      const guestSessionIdToSend = user ? undefined : guestSessionId
      
      const response: ChatResponse = await chatService.sendMessage({
        content: inputMessage,
        conversation_id: conversationId,
        guest_session_id: guestSessionIdToSend
      })

      console.log("API Response:", response)

      // Update conversation ID if this is a new conversation
      if (!conversationId && onNewConversation) {
        console.log("Setting new conversation ID:", response.conversation_id)
        onNewConversation(response.conversation_id)
      }

      const aiMessage: ChatMessage = {
        id: response.message_id,
        content: response.message,
        sender_type: "ai" as const,
        created_at: new Date().toISOString(),
        metadata: {
          sources: response.sources,
          confidence: response.confidence,
          suggested_actions: response.suggested_actions,
        },
      }

      // Replace the temporary user message with the real one from the server
      // and add the AI's response
      setMessages((prev) => [
        ...prev.filter((msg) => msg.id !== userMessage.id),
        aiMessage,
      ])
      console.log("Messages state after setting:", messages)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to send message")
      setMessages((prev) => prev.slice(0, -1)) // Remove the temporary user message
    } finally {
      setLoading(false)
    }
  }

  const renderMessage = (message: ChatMessage) => {
    const isUser = message.sender_type !== 'ai'
    const sources = message.metadata?.sources || []
    const suggestedActions = message.metadata?.suggested_actions || []

    return (
      <div key={message.id} className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
        <div
          className={`max-w-xs lg:max-w-md px-4 py-2 rounded-xl shadow-md ${
            isUser
              ? "bg-gradient-to-r from-primary to-primary/80 text-primary-foreground"
              : "bg-gradient-to-r from-secondary to-secondary/80 text-secondary-foreground"
          }`}
        >
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>

          {!isUser && sources.length > 0 && (
            <div className="mt-2 pt-2 border-t border-border">
              <p className="text-xs text-muted-foreground mb-1">منابع:</p>
              {sources.map((source, index) => (
                <div key={index} className="text-xs text-primary hover:opacity-80 cursor-pointer">
                  📄 {source.title}
                </div>
              ))}
            </div>
          )}

          {!isUser && suggestedActions.length > 0 && (
            <div className="mt-2 pt-2 border-t border-border">
              <p className="text-xs text-muted-foreground mb-1">اقدامات پیشنهادی:</p>
              <div className="flex flex-wrap gap-1">
                {suggestedActions.map((action, index) => (
                  <button
                    key={index}
                    className="text-xs bg-secondary text-secondary-foreground px-2 py-1 rounded hover:opacity-80 transition-opacity"
                    onClick={() => handleSuggestedAction(action)}
                  >
                    {formatActionText(action)}
                  </button>
                ))}
              </div>
            </div>
          )}

          <p className="text-xs text-muted-foreground/70 mt-1">{new Date(message.created_at).toLocaleTimeString("fa-IR")}</p>
        </div>
      </div>
    )
  }

  const handleSuggestedAction = (action: string) => {
    switch (action) {
      case "create_ticket":
        if (user) {
          window.location.href = "/tickets"
        } else {
          toast.error("Please log in to create a support ticket")
        }
        break
      case "view_related_articles":
        // Could open a modal or navigate to knowledge base
        toast("Feature coming soon: View related articles")
        break
      case "contact_support":
        toast("Please email support@sally.com or call 1-800-SALLY")
        break
      default:
        console.log("Unknown action:", action)
    }
  }

  const formatActionText = (action: string): string => {
    const actionMap: Record<string, string> = {
      create_ticket: "Create Ticket",
      view_related_articles: "View Articles",
      contact_support: "Contact Support",
      view_account: "View Account",
    }
    return actionMap[action] || action
  }

  return (
    <div className="flex flex-col h-full">
      {/* Chat Header */}
      <div className="bg-card border-b border-border px-4 py-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">
            {conversationId ? "مکالمه جاری" : "چت با Sally"}
          </h2>
          <div className="text-sm text-muted-foreground">
            {user ? `وارد شده به عنوان ${user.full_name}` : "کاربر مهمان"}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gradient-to-br from-background to-muted/20">
        {/* Always render messages */}
        {messages.map(renderMessage)}

        {loading && (
          <div className="flex justify-start mb-4">
            <div className="bg-secondary text-secondary-foreground max-w-xs lg:max-w-md px-4 py-2 rounded-lg">
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                <span className="text-sm">Sally در حال تایپ کردن است...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-card border-t border-border p-4">
        <form onSubmit={handleSendMessage} className="flex items-center space-x-2 bg-background rounded-lg pl-4 border border-border">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="پیام خود را تایپ کنید..."
            className="flex-1 bg-transparent border-none focus:ring-0 focus:outline-none"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !inputMessage.trim()}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed rounded-lg px-4 py-2"
          >
            ارسال
          </button>
        </form>
      </div>
    </div>
  )
}

export default ChatInterface
