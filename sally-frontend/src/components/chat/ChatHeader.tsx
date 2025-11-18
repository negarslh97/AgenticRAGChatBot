import React from 'react'
import { Button } from '../ui/button'
import { Bot, ChevronLeft, ChevronRight } from 'lucide-react'

interface ChatHeaderProps {
  isSidebarOpen: boolean
  onToggleSidebar: () => void
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  isSidebarOpen,
  onToggleSidebar
}) => {
  return (
    <header className="flex items-center justify-between p-4 bg-white shadow-sm">
      <div className="flex items-center gap-3 mr-4">
        <div className="relative">
          <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center">
            <Bot className="h-4 w-4 text-white" />
          </div>
          <div className="absolute -bottom-1 -right-1 h-3 w-3 bg-green-500 border-2 border-white rounded-full"></div>
        </div>
        <div>
          <h1 className="font-semibold text-gray-900">سالی</h1>
          <p className="text-xs text-gray-500">آنلاین</p>
        </div>
      </div>
      <Button
        onClick={onToggleSidebar}
        variant="ghost"
        size="icon"
        className=""
      >
        {isSidebarOpen ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
      </Button>
    </header>
  )
}