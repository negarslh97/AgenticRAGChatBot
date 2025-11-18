import React from 'react'
import { Button } from '../ui/button'
import { Textarea } from '../ui/textarea'
import { VoiceInput } from '../ui/voice-input'
import { Send } from 'lucide-react'

interface ChatInputProps {
  newMessage: string
  isLoading: boolean
  onMessageChange: (message: string | ((prev: string) => string)) => void
  onKeyPress: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void
  onSendMessage: () => void
}

export const ChatInput: React.FC<ChatInputProps> = ({
  newMessage,
  isLoading,
  onMessageChange,
  onKeyPress,
  onSendMessage
}) => {
  return (
    <footer className="p-4 bg-white shadow-[0_-2px_4px_-2px_rgba(0,0,0,0.05)]">
      <div className="flex gap-2 items-end">
        <Button
          onClick={onSendMessage}
          disabled={!newMessage.trim() || isLoading}
          className="whitespace-nowrap text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 text-white bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 h-10 w-10 md:h-12 md:w-12 rounded-xl flex items-center justify-center flex-shrink-0"
        >
          {isLoading ? (
            <div className="animate-spin rounded-full h-4 w-4 md:h-5 md:w-5 border-2 border-white border-t-transparent"></div>
          ) : (
            <Send className="h-4 w-4 md:h-5 md:w-5" />
          )}
        </Button>
        <VoiceInput
          onTranscriptionComplete={(text) => {
            onMessageChange(prev => prev ? `${prev}\n${text}` : text)
          }}
          disabled={isLoading}
        />
        <Textarea
          value={newMessage}
          onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => onMessageChange(e.target.value)}
          onKeyPress={onKeyPress}
          placeholder="پیام خود را بنویسید..."
          className="flex-1 resize-none text-right bg-white rounded-lg p-3 border-2 border-slate-200 focus-visible:border-blue-500 focus-visible:ring-0 focus-visible:outline-none transition-colors"
          rows={1}
        />
      </div>
    </footer>
  )
}