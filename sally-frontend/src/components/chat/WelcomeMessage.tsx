import React from 'react'
import { Button } from '../ui/button'
import { Sparkles, HelpCircle, Lightbulb } from 'lucide-react'

interface WelcomeMessageProps {
  onExampleClick: (message: string) => void
}

export const WelcomeMessage: React.FC<WelcomeMessageProps> = ({ onExampleClick }) => {
  const examples = [
    {
      icon: HelpCircle,
      text: 'به من درباره شرکت صدگان بگو',
      gradient: 'from-blue-500 to-purple-500'
    },
    {
      icon: Lightbulb,
      text: 'محصولات شرکت صدگان چیست؟',
      gradient: 'from-purple-500 to-pink-500'
    },
    {
      icon: Sparkles,
      text: 'چطور می‌توانم محصول CRM این شرکت رو بخرم؟',
      gradient: 'from-pink-500 to-orange-500'
    }
  ]

  return (
    <div className="flex flex-col items-center justify-center h-full text-center space-y-8 px-4" dir="rtl">
      <div className="relative">
        <div className="h-24 w-24 rounded-2xl bg-gradient-to-br from-purple-600 via-blue-600 to-purple-600 flex items-center justify-center shadow-2xl shadow-purple-500/30 transform hover:scale-105 transition-transform duration-300">
          <Sparkles className="h-12 w-12 text-white" />
        </div>
        <div className="absolute -bottom-2 -right-2 h-7 w-7 bg-green-500 border-2 border-white rounded-full flex items-center justify-center shadow-lg animate-pulse">
          <div className="h-2.5 w-2.5 bg-white rounded-full"></div>
        </div>
        <div className="absolute -top-1 -left-1 w-4 h-4 bg-purple-400 rounded-full opacity-60 animate-ping"></div>
      </div>
      
      <div className="space-y-3">
        <h2 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
          به چت با سالی خوش آمدید!
        </h2>
        <p className="text-gray-600 max-w-lg leading-relaxed">
          من Sally، دستیار هوش مصنوعی شما هستم. می‌توانم به سؤالات شما پاسخ دهم، اطلاعات ارائه کنم و در کارهای شما کمک کنم.
        </p>
      </div>
      
      <div className="space-y-4 w-full max-w-lg">
        <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-purple-600" />
          مثال‌های سؤال:
        </h3>
        <div className="flex flex-col gap-3">
          {examples.map((example, index) => {
            const IconComponent = example.icon
            return (
              <Button
                key={index}
                variant="outline"
                className="group flex items-center justify-start justify-content-start p-4 h-auto border-2 border-purple-100 hover:border-purple-300 bg-white/80 backdrop-blur-sm hover:bg-gradient-to-r hover:from-purple-50 hover:to-blue-50 transition-all duration-200 hover:shadow-lg hover:scale-[1.02] rounded-xl"
                onClick={() => onExampleClick(example.text)}
              >
                <div className="flex items-center gap-3 flex-justify-content-start">
                  <div className={`p-2 rounded-lg bg-gradient-to-br ${example.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-200`}>
                    <IconComponent className="h-4 w-4 text-white" />
                  </div>
                  <span className="text-sm font-medium text-gray-700 group-hover:text-purple-700 transition-colors">
                    {example.text}
                  </span>
                  {/* <div className="p-1.5 rounded-md bg-gray-100 group-hover:bg-purple-100 transition-colors">
                    <IconComponent className="h-4 w-4 text-gray-500 group-hover:text-purple-600 transition-colors" />
                  </div> */}
                </div>
              </Button>
            )
          })}
        </div>
      </div>
    </div>
  )
}