import { useCallback } from 'react'
import { toast } from 'react-hot-toast'
import { chatService } from '../services/chatService'

interface Source {
  id: string
  title: string
  score?: number
  snippet?: string
  category?: string
  tags?: string[]
}

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
  sender_type?: 'Customer' | 'Admin' | 'SuperAdmin' | 'Guest' | 'AI'
  is_failed?: boolean
  failure_reason?: string
  metadata?: {
    model_name?: string
    provider?: string
    confidence?: number
    rag_type?: string
    token_usage?: {
      prompt_tokens?: number
      completion_tokens?: number
      total_tokens?: number
    }
    response_time?: number
  }
  sources?: Source[]
  confidence?: number
  suggested_actions?: string[]
}

interface Conversation {
  id: string
  title: string
  messages: Message[]
  created_at?: string
  updated_at?: string
}

interface StreamEvent {
  type: 'conversation_id' | 'chunk' | 'metadata' | 'done' | 'error'
  content?: string
  conversation_id?: string
  sources?: Source[]
  confidence?: number
  actions_taken?: string[]
  message?: string
}

export const useMessageStreaming = () => {
  const sendMessage = useCallback(async (
    chatService: any,
    userMessageContent: string,
    selectedConversation: Conversation | null,
    setSelectedConversation: any,
    setIsLoading: any,
    guestSessionId: string | null,
    ragType: string,
    useStreaming: boolean,
    loadConversations: any,
    scrollToBottom: any
  ) => {
    if (!userMessageContent.trim() || !chatService) return

    const userMessageContentTrimmed = userMessageContent.trim()
    setIsLoading(true)

    // Add user message to UI
    const tempUserMessage: Message = {
      id: `temp_${Date.now()}`,
      content: userMessageContentTrimmed,
      role: 'user',
      timestamp: new Date(),
      sender_type: 'Customer' // Will be updated based on actual user type
    }

    if (!selectedConversation) {
      // Create new conversation
      const newConv: Conversation = {
        id: `temp_${Date.now()}`,
        title: 'گفتگوی جدید',
        messages: [tempUserMessage]
      }
      setSelectedConversation(newConv)
    } else {
      setSelectedConversation((prev: Conversation | null) => ({
        ...prev!,
        messages: [...(prev?.messages || []), tempUserMessage]
      }))
    }

    try {
      // Use streaming for better UX
      if (useStreaming) {
        let streamedContent = ''
        let conversationId = selectedConversation?.id?.startsWith('temp_') ? undefined : selectedConversation?.id
        
        // Create AI message placeholder
        const aiMessageId = `msg_${Date.now()}`
        const aiMessage: Message = {
          id: aiMessageId,
          content: '',
          role: 'assistant',
          timestamp: new Date(),
          sender_type: 'AI',
          sources: [],
          confidence: 0.5,
          suggested_actions: [],
          metadata: {
            rag_type: ragType
          }
        }

        setSelectedConversation((prev: Conversation | null) => ({
          ...prev!,
          messages: [...(prev?.messages || []), aiMessage]
        }))

        // Handle streaming events
        const handleEvent = (evt: StreamEvent) => {
          console.log('📦 Stream event:', evt.type)
          
          if (evt.type === 'conversation_id') {
            conversationId = evt.conversation_id
          } else if (evt.type === 'chunk') {
            streamedContent += evt.content || ''
            setSelectedConversation((prev: Conversation | null) => ({
              ...prev!,
              messages: (prev?.messages || []).map((msg: Message) =>
                msg.id === aiMessageId
                  ? { ...msg, content: streamedContent }
                  : msg
              )
            }))
            setTimeout(scrollToBottom, 10)
          } else if (evt.type === 'metadata') {
            setSelectedConversation((prev: Conversation | null) => ({
              ...prev!,
              id: conversationId || prev!.id,
              messages: (prev?.messages || []).map((msg: Message) =>
                msg.id === aiMessageId
                  ? {
                      ...msg,
                      content: streamedContent,
                      sources: evt.sources || [],
                      confidence: evt.confidence,
                      suggested_actions: evt.actions_taken || [],
                      metadata: {
                        rag_type: ragType,
                        confidence: evt.confidence,
                        complexity: (evt as any).complexity
                      }
                    }
                  : msg
              )
            }))
          } else if (evt.type === 'done') {
            setIsLoading(false)
            // Update conversation list if new conversation
            if (selectedConversation?.id?.startsWith('temp_') || !selectedConversation) {
              loadConversations()
            }
          } else if (evt.type === 'error') {
            console.error('Stream error:', evt.message)
            setSelectedConversation((prev: Conversation | null) => ({
              ...prev!,
              messages: (prev?.messages || []).map((msg: Message) =>
                msg.id === aiMessageId
                  ? {
                      ...msg,
                      content: 'متأسفانه خطایی رخ داد. لطفاً دوباره تلاش کنید.',
                      is_failed: true,
                      failure_reason: evt.message
                    }
                  : msg
              )
            }))
            setIsLoading(false)
            toast.error('خطا در ارسال پیام')
          }
        }

        // Start streaming
        if (ragType === 'agentic') {
          console.log('🌊 Using Agentic RAG Streaming...')
          await chatService.sendAdvancedAgenticMessageStream(
            userMessageContentTrimmed,
            conversationId,
            handleEvent
          )
        } else {
          console.log('🌊 Using Simple RAG Streaming...')
          await chatService.sendMessageStream(
            userMessageContentTrimmed,
            conversationId,
            guestSessionId || undefined,
            handleEvent
          )
        }
      } else {
        // Non-streaming (original behavior)
        let response: {
          conversation_id: string
          message: string
          sources: Source[]
          confidence: number
          suggested_actions: string[]
          message_id: string
        }

        if (ragType === 'agentic') {
          console.log('🧠 Using Agentic RAG...')
          
          const apiResponse = await chatService.sendAdvancedAgenticMessage({
            query: userMessageContentTrimmed,
            conversation_id: selectedConversation?.id?.startsWith('temp_') ? null : selectedConversation?.id
          })

          response = {
            conversation_id: apiResponse.conversation_id,
            message: apiResponse.response,
            sources: apiResponse.sources || [],
            confidence: apiResponse.confidence || 0.5,
            suggested_actions: apiResponse.suggested_actions || [],
            message_id: apiResponse.conversation_id
          }
        } else {
          console.log('💬 Using Simple RAG...')
          response = await chatService.sendMessage({
            content: userMessageContentTrimmed,
            conversation_id: selectedConversation?.id?.startsWith('temp_') ? null : selectedConversation?.id,
            guest_session_id: guestSessionId
          })
        }

        // Add AI response to UI
        const aiMessage: Message = {
          id: response.message_id || `msg_${Date.now()}`,
          content: response.message,
          role: 'assistant',
          timestamp: new Date(),
          sender_type: 'AI',
          sources: response.sources || [],
          confidence: response.confidence,
          suggested_actions: response.suggested_actions || [],
          metadata: {
            rag_type: ragType,
            confidence: response.confidence
          }
        }

        setSelectedConversation((prev: Conversation | null) => ({
          ...prev!,
          id: response.conversation_id,
          messages: [...(prev?.messages || []), aiMessage]
        }))

        // Update conversation list
        if (selectedConversation?.id?.startsWith('temp_') || !selectedConversation) {
          loadConversations()
        }

        setTimeout(scrollToBottom, 100)
        setIsLoading(false)
      }
    } catch (error: any) {
      console.error('❌ Error sending message:', error)
      
      // Add error message
      const errorMessage: Message = {
        id: `error_${Date.now()}`,
        content: 'متأسفانه خطایی رخ داد. لطفاً دوباره تلاش کنید.',
        role: 'assistant',
        timestamp: new Date(),
        sender_type: 'AI',
        is_failed: true,
        failure_reason: error.response?.data?.detail || error.message
      }

      setSelectedConversation((prev: Conversation | null) => ({
        ...prev!,
        messages: [...(prev?.messages || []), errorMessage]
      }))

      toast.error(error.response?.data?.detail || 'خطا در ارسال پیام')
      setIsLoading(false)
    }
  }, [])

  return { sendMessage }
}