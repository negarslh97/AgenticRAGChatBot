'use client'

import React, { useState, useEffect } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'
import { chatService } from '../services/chatService'
import { Bot, Zap, Crown, Cpu, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'

interface Model {
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
}

interface ModelSelectorProps {
  selectedModel: string
  onModelChange: (modelId: string) => void
  disabled?: boolean
  className?: string
}

const ModelSelector: React.FC<ModelSelectorProps> = ({
  selectedModel,
  onModelChange,
  disabled = false,
  className = ''
}) => {
  const [models, setModels] = useState<Model[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadModels()
  }, [])

  const loadModels = async () => {
    try {
      setLoading(true)
      setError(null)
      const modelData = await chatService.getAvailableModels()
      setModels(modelData.models)
    } catch (err) {
      console.error('Failed to load models:', err)
      setError('خطا در بارگذاری مدل‌ها')
      toast.error('خطا در بارگذاری مدل‌ها')
    } finally {
      setLoading(false)
    }
  }

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'fastest':
        return <Zap className="h-4 w-4 text-green-600" />
      case 'free':
        return <Crown className="h-4 w-4 text-blue-600" />
      case 'openai':
        return <Bot className="h-4 w-4 text-purple-600" />
      case 'heavy':
        return <AlertTriangle className="h-4 w-4 text-orange-600" />
      case 'ollama':
        return <Cpu className="h-4 w-4 text-gray-600" />
      default:
        return <Bot className="h-4 w-4 text-gray-600" />
    }
  }

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'fastest':
        return 'سریع‌ترین'
      case 'free':
        return 'رایگان'
      case 'openai':
        return 'OpenAI'
      case 'heavy':
        return 'سنگین'
      case 'ollama':
        return 'محلی'
      default:
        return 'سایر'
    }
  }

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'fastest':
        return 'text-green-700 bg-green-50 border-green-200'
      case 'free':
        return 'text-blue-700 bg-blue-50 border-blue-200'
      case 'openai':
        return 'text-purple-700 bg-purple-50 border-purple-200'
      case 'heavy':
        return 'text-orange-700 bg-orange-50 border-orange-200'
      case 'ollama':
        return 'text-gray-700 bg-gray-50 border-gray-200'
      default:
        return 'text-gray-700 bg-gray-50 border-gray-200'
    }
  }

  // گروه‌بندی مدل‌ها بر اساس category
  const groupedModels = models.reduce((acc, model) => {
    const category = model.category || 'other'
    if (!acc[category]) {
      acc[category] = []
    }
    acc[category].push(model)
    return acc
  }, {} as Record<string, Model[]>)

  const categoryOrder = ['fastest', 'free', 'openai', 'heavy', 'ollama', 'other']

  return (
    <div className={`model-selector ${className}`}>
      <div className="flex items-center gap-2 mb-2">
        <Bot className="h-4 w-4 text-blue-600" />
        <span className="text-sm font-medium text-gray-700">انتخاب مدل AI</span>
      </div>
      
      <Select
        value={selectedModel}
        onValueChange={onModelChange}
        disabled={disabled || loading}
      >
        <SelectTrigger className="w-full min-h-[44px] text-right">
          <SelectValue placeholder={
            loading ? "در حال بارگذاری..." : 
            error ? "خطا در بارگذاری" : 
            "مدل را انتخاب کنید"
          } />
        </SelectTrigger>
        
        <SelectContent className="max-h-96">
          {error ? (
            <div className="p-4 text-center text-red-600">
              <AlertTriangle className="h-8 w-8 mx-auto mb-2" />
              <p className="text-sm">{error}</p>
              <button 
                onClick={loadModels}
                className="mt-2 text-xs text-blue-600 hover:underline"
              >
                تلاش مجدد
              </button>
            </div>
          ) : loading ? (
            <div className="p-4 text-center text-gray-500">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto mb-2"></div>
              <p className="text-sm">در حال بارگذاری مدل‌ها...</p>
            </div>
          ) : (
            <>
              {categoryOrder.map(category => {
                const categoryModels = groupedModels[category] || []
                if (categoryModels.length === 0) return null

                return (
                  <div key={category}>
                    <div className={`px-3 py-2 text-xs font-semibold border-b ${getCategoryColor(category)}`}>
                      <div className="flex items-center gap-2">
                        {getCategoryIcon(category)}
                        {getCategoryLabel(category)} ({categoryModels.length})
                      </div>
                    </div>
                    
                    {categoryModels.map((model) => (
                      <SelectItem
                        key={model.id}
                        value={model.id}
                        className="cursor-pointer hover:bg-blue-50"
                      >
                        <div className="flex items-center justify-between w-full gap-3">
                          <div className="flex items-center gap-2 min-w-0 flex-1">
                            {getCategoryIcon(model.category)}
                            <div className="min-w-0 flex-1 text-right">
                              <div className="font-medium text-gray-900 truncate">
                                {model.name}
                              </div>
                              <div className="text-xs text-gray-500 truncate">
                                {model.description}
                              </div>
                            </div>
                          </div>
                          
                          <div className="flex flex-col items-end gap-1 text-xs">
                            {model.speed && (
                              <span className="text-green-600 font-medium">
                                {model.speed}
                              </span>
                            )}
                            <div className="flex items-center gap-1 text-gray-400">
                              <span>{model.provider}</span>
                              <span>•</span>
                              <span>{model.max_tokens.toLocaleString()}</span>
                            </div>
                          </div>
                        </div>
                      </SelectItem>
                    ))}
                  </div>
                )
              })}
            </>
          )}
        </SelectContent>
      </Select>
      
      {selectedModel && !loading && !error && (
        <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center gap-2 text-sm text-blue-800">
            {getCategoryIcon(models.find(m => m.id === selectedModel)?.category || 'other')}
            <span className="font-medium">
              مدل انتخابی: {models.find(m => m.id === selectedModel)?.name}
            </span>
          </div>
          <p className="text-xs text-blue-600 mt-1">
            {models.find(m => m.id === selectedModel)?.description}
          </p>
        </div>
      )}
    </div>
  )
}

export default ModelSelector