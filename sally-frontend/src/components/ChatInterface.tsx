"use client"

import type React from "react"
import { useState, useEffect, useRef, useCallback } from "react"
import { useAuth } from "../context/AuthContext"
import { chatService, type ChatMessage, type ChatResponse } from "../services/chatService"

interface ExtendedChatMessage extends ChatMessage {
  ragType?: string;
}
import { Button } from "./ui/button"
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
  const { user } = useAuth()
  
  // Smart scroll state - using useRef for better performance
  const userHasScrolledUp = useRef(false)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const [showGoToBottomBtn, setShowGoToBottomBtn] = useState(false)
  
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

      // Debug: بررسی rag_type در هر پیام
      conversationMessages.forEach((msg, index) => {
        console.log(`Message ${index}: ID=${msg.id}, sender_type=${msg.sender_type}, rag_type=${msg.metadata?.rag_type || 'NOT_SET'}`)
      })

      // Show welcome message if no messages found
      console.log("Processing messages:", conversationMessages.length)
      if (conversationMessages.length === 0) {
        console.log("No messages found, showing welcome message")
        const welcomeMessage: ChatMessage = {
          id: "welcome",
          content: "👋 Hi! I'm Sally, your AI assistant. How can I help you today?",
          sender_type: "AI" as const,
          created_at: new Date().toISOString(),
        }
        console.log("Setting welcome message:", welcomeMessage)
        setMessages([welcomeMessage])
        console.log("Messages state after setting:", [welcomeMessage])
      } else {
        console.log("Setting conversation messages:", conversationMessages)
        
        // Assume 'apiResponse.messages' is the array of messages received from the API.
        // In our case, conversationMessages is the array from the API response
        
        // Step A: Map the incoming API data to the structure needed for the state.
        // This MUST explicitly extract `rag_type` from the metadata.
        const processedMessages = conversationMessages.map(msg => ({
          ...msg,
          ragType: msg.metadata?.rag_type || 'simple'
        }));

        // Step B: *** THIS IS THE MOST IMPORTANT STEP ***
        // Add this exact console.log to print the processed data.
        console.log('--- RAG TYPE DIAGNOSTIC DATA ---', processedMessages);

        // Step C: Update the state with the processed data.
        setMessages(processedMessages)
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
        sender_type: "AI" as const,
        created_at: new Date().toISOString(),
      }
      setMessages([welcomeMessage])
    }
  }, [conversationId, loadConversationMessages])

  useEffect(() => {
    // Always auto-scroll smoothly when messages change, but respect user scroll preference
    if (!userHasScrolledUp.current) {
      scrollToBottom()
    }
  }, [messages])

  const scrollToBottom = () => {
    // Only auto-scroll if user hasn't scrolled up
    if (!userHasScrolledUp.current && chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: 'smooth'
      })
    }
  }

  const handleScroll = () => {
    if (!chatContainerRef.current) return
    
    const container = chatContainerRef.current
    const isAtBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 10

    if (isAtBottom) {
      userHasScrolledUp.current = false
      setShowGoToBottomBtn(false)
    } else {
      userHasScrolledUp.current = true
      setShowGoToBottomBtn(true)
    }
  }

  const handleGoToBottom = () => {
    userHasScrolledUp.current = false
    setShowGoToBottomBtn(false)
    scrollToBottom()
  }

  // ✅✅✅ نسخه نهایی و صحیح handleSendMessage ✅✅✅
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || loading) return;

    const userMessage: ChatMessage = {
      id: `temp_user_${Date.now()}`,
      content: inputMessage,
      sender_type: user ? "Customer" : "Guest",
      created_at: new Date().toISOString(),
    };

    const aiMessageId = `ai_stream_${Date.now()}`;
    const tempAiMessage: ChatMessage = {
      id: aiMessageId,
      content: "", // شروع با محتوای خالی
      sender_type: "AI",
      created_at: new Date().toISOString(),
    };

    // ✅✅✅ اصلاح کلیدی: هر دو پیام را در یک فراخوانی setMessages اضافه کن ✅✅✅
    setMessages((prev) => [...prev, userMessage, tempAiMessage]);

    setInputMessage("");
    setLoading(true);

    try {
      let fullResponseContent = "";
      let finalEventData: any = null;

      // Wrap the streaming call in a promise to wait for completion
      await new Promise<void>((resolve, reject) => {
        const streamPromise = chatService.sendMessageStream(
          inputMessage,
          conversationId,
          user ? undefined : guestSessionId,
          (event) => {
            console.log("Stream event:", event);

            if (event.type === 'init' && !conversationId && onNewConversation && event.conversation_id) {
              onNewConversation(event.conversation_id);
            }
            if (event.type === 'chunk') {
              fullResponseContent += event.content;
              setMessages(prev =>
                prev.map(msg =>
                  msg.id === aiMessageId ? { ...msg, content: fullResponseContent } : msg
                )
              );
            }
            if (event.type === 'complete') {
              finalEventData = event;
              resolve(); // Resolve the promise when complete
            }
            if (event.type === 'error') {
              reject(new Error(event.message || "Stream error"));
            }
          }
        );

        // Handle the promise rejection if stream setup fails
        streamPromise.catch(reject);
      });

      if (finalEventData) {
        setMessages(prev =>
          prev.map(msg => {
            if (msg.id === aiMessageId) {
              return {
                ...msg,
                id: finalEventData.message_id,
                content: finalEventData.message || fullResponseContent,
                metadata: {
                  sources: finalEventData.sources,
                  confidence: finalEventData.confidence,
                  suggested_actions: finalEventData.suggested_actions,
                  rag_type: finalEventData.metadata?.rag_type || 'simple'
                }
              };
            }
            return msg;
          })
        );
      } else {
        // اگر استریم بدون رویداد complete تمام شد (مثلا خطا)
        // پیام موقت AI را حذف کن
        setMessages(prev => prev.filter(msg => msg.id !== aiMessageId));
      }

    } catch (error: any) {
      toast.error(error.message || "Failed to get response");
      setMessages(prev => prev.filter(msg => msg.id !== aiMessageId && msg.id !== userMessage.id));
    } finally {
      setLoading(false);
    }
  };

  const renderMessage = (message: ExtendedChatMessage) => {
    const isUser = message.sender_type !== 'AI'
    const sources = message.metadata?.sources || []
    const suggestedActions = message.metadata?.suggested_actions || []
    const canGetMoreDetails = message.metadata?.can_get_more_details || false
    const ragType = message.ragType || 'simple' // از فیلد جدید و صحیح استفاده کن

    // نمایش rag_type برای پیام‌های AI
    const displayRagType = !isUser && ragType

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

          {!isUser && (suggestedActions.length > 0 || canGetMoreDetails) && (
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
                {canGetMoreDetails && (
                  <button
                    className="text-xs bg-primary text-primary-foreground px-2 py-1 rounded hover:opacity-80 transition-opacity"
                    onClick={() => handleGetMoreDetails(message)}
                  >
                    توضیحات کامل
                  </button>
                )}
              </div>
            </div>
          )}

          {/* نمایش rag_type برای پیام‌های AI */}
          {displayRagType && (
            <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
              <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full">
                {ragType === 'simple' ? '🔍 Simple RAG' :
                 ragType === 'agentic' ? '🤖 Agentic RAG' :
                 ragType}
              </span>
            </div>
          )}

          <p className="text-xs text-muted-foreground/70 mt-1">{new Date(message.created_at).toLocaleTimeString("fa-IR")}</p>
        </div>
      </div>
    )
  }

  const handleGetMoreDetails = async (aiMessage: ChatMessage) => {
    // Find the previous user message in the conversation
    const aiMessageIndex = messages.findIndex(msg => msg.id === aiMessage.id)
    if (aiMessageIndex <= 0) {
      toast.error("Unable to find the original question")
      return
    }

    const userMessage = messages[aiMessageIndex - 1]
    if (userMessage.sender_type === 'AI') {
      toast.error("Unable to find the original question")
      return
    }

    // Add a temporary message indicating we're getting detailed response
    const tempMessage: ChatMessage = {
      id: `temp_detailed_${Date.now()}`,
      content: "در حال دریافت توضیحات کامل...",
      sender_type: "AI" as const,
      created_at: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, tempMessage])
    setLoading(true)

    try {
      const guestSessionIdToSend = user ? undefined : guestSessionId

      const response: ChatResponse = await chatService.sendMessage({
        content: userMessage.content,
        conversation_id: conversationId,
        guest_session_id: guestSessionIdToSend,
        rag_type: "agentic"
      })

      // Update conversation ID if this is a new conversation
      if (!conversationId && onNewConversation) {
        onNewConversation(response.conversation_id)
      }

      const detailedMessage: ChatMessage = {
        id: response.message_id,
        content: response.message,
        sender_type: "AI" as const,
        created_at: new Date().toISOString(),
        metadata: {
          sources: response.sources,
          confidence: response.confidence,
          suggested_actions: response.suggested_actions,
          rag_type: "agentic",
          can_get_more_details: false, // Detailed response doesn't need more details
        },
      }

      // Replace the temporary message with the detailed response
      setMessages((prev) => [
        ...prev.filter((msg) => msg.id !== tempMessage.id),
        detailedMessage,
      ])

      toast.success("توضیحات کامل دریافت شد")
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to get detailed response")
      setMessages((prev) => prev.filter((msg) => msg.id !== tempMessage.id)) // Remove temp message
    } finally {
      setLoading(false)
    }
  }

  const handleSuggestedAction = (action: string) => {
    switch (action) {
      case "create_ticket":
        // Ticket system removed - redirect to chat instead
        if (user) {
          window.location.href = "/chat"
        } else {
          toast.error("Please log in to start a chat")
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
      create_ticket: "Continue Chat",
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
      <div
        ref={chatContainerRef}
        id="chat-container"
        className="flex-1 overflow-y-auto p-4 space-y-4 bg-gradient-to-br from-background to-muted/20"
        onScroll={handleScroll}
      >
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

        
        {/* Go to bottom button */}
        <button
          id="go-to-bottom-btn"
          onClick={handleGoToBottom}
          title="برو به آخرین پیام"
          className={`fixed bottom-24 left-1/2 transform -translate-x-1/2 bg-white border border-gray-300 rounded-full w-10 h-10 flex items-center justify-center cursor-pointer shadow-lg hover:shadow-xl transition-all duration-200 z-10 ${
            showGoToBottomBtn ? 'block' : 'hidden'
          }`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
            <path d="M12 15.586l-4.293-4.293-1.414 1.414L12 18.414l5.707-5.707-1.414-1.414L12 15.586z"/>
            <path d="M12 8.586l-4.293-4.293-1.414 1.414L12 11.414l5.707-5.707-1.414-1.414L12 8.586z"/>
          </svg>
        </button>
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
          <Button
            type="submit"
            disabled={loading || !inputMessage.trim()}
            className="rounded-lg px-4 py-2"
          >
            ارسال
          </Button>
        </form>
      </div>
    </div>
  )
}

export default ChatInterface
