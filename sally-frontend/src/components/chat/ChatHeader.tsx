'use client'

import React from 'react'
import { Button } from '../ui/button'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useAudio } from '../../hooks/useAudio'
import blackCatImage from '../../assets/Black-Cat.png'
import meowSound from '../../assets/meow.mp3'

interface ChatHeaderProps {
  isSidebarOpen: boolean
  onToggleSidebar: () => void
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  isSidebarOpen,
  onToggleSidebar
}) => {
  console.log('ChatHeader image asset:', blackCatImage)
  console.log('ChatHeader audio asset:', meowSound)
  const { play } = useAudio(meowSound)

  const handleImageClick = () => {
    console.log('Playing meow sound...')
    console.log('Image src:', blackCatImage)
    console.log('Sound src:', meowSound)
    play()
  }

  return (
    <header className="flex items-center justify-between p-4 bg-white shadow-sm">
      <div className="flex items-center gap-3 mr-4">
        <div className="relative">
          <img
            src={blackCatImage}
            alt="سالی"
            className="h-8 w-8 rounded-full cursor-pointer object-cover"
            onClick={handleImageClick}
          />
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