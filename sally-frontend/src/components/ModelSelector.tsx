'use client'

import React, { useState, useEffect } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'
import { chatService } from '../services/chatService'
import { Bot, Zap, Cpu, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'
import { MODELS_CONFIG, getGroupedModels, getModelById } from '../config/models'

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
      // اول از API امتحان می‌کنیم
      try {
        const modelData = await chatService.getAvailableModels()
        setModels(modelData.models)
      } catch (apiError) {
        console.warn('Failed to load models from API, using local config:', apiError)
        // fallback به فایل کانفیگ
        setModels(MODELS_CONFIG.models)
      }
    } catch (err) {
      console.error('Failed to load models:', err)
      setError('خطا در بارگذاری مدل‌ها')
      toast.error('خطا در بارگذاری مدل‌ها')
      // در صورت خطا، از config محلی استفاده کن
      setModels(MODELS_CONFIG.models)
    } finally {
      setLoading(false)
    }
  }

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'openai':
        return <Bot className="h-4 w-4 text-purple-600" />
      case 'ollama':
      case 'local':
        return <Cpu className="h-4 w-4 text-gray-600" />
      case 'openrouter':
        return <Zap className="h-4 w-4 text-blue-600" />
      default:
        return <Bot className="h-4 w-4 text-gray-600" />
    }
  }

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'openai':
        return 'OpenAI'
      case 'ollama':
      case 'local':
        return 'محلی'
      case 'openrouter':
        return 'OpenRouter'
      default:
        return 'سایر'
    }
  }

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'openai':
        return 'text-purple-700 bg-purple-50 border-purple-200'
      case 'ollama':
      case 'local':
        return 'text-gray-700 bg-gray-50 border-gray-200'
      case 'openrouter':
        return 'text-blue-700 bg-blue-50 border-blue-200'
      default:
        return 'text-gray-700 bg-gray-50 border-gray-200'
    }
  }

  // تبدیل دسته‌های قدیمی به دسته‌های جدید (سه دسته: openai, local, openrouter)
  const normalizeCategory = (category: string | undefined, provider?: string): string => {
    let normalized = category || 'other'
    
    // تبدیل دسته‌های قدیمی
    if (normalized === 'ollama') {
      return 'local'
    } else if (normalized === 'fastest' || normalized === 'free' || normalized === 'heavy') {
      return 'openrouter'
    }
    
    // اگر دسته در لیست سه دسته نیست، بر اساس provider تصمیم می‌گیریم
    if (normalized !== 'openai' && normalized !== 'local' && normalized !== 'openrouter') {
      if (provider === 'OpenAI' || provider === 'openai') {
        return 'openai'
      } else if (provider === 'Ollama' || provider === 'ollama') {
        return 'local'
      } else {
        return 'openrouter'
      }
    }
    
    return normalized
  }

  // گروه‌بندی مدل‌ها بر اساس category (فقط سه دسته: openai, local, openrouter)
  const groupedModels = models.reduce((acc, model) => {
    const category = normalizeCategory(model.category, model.provider)
    
    if (!acc[category]) {
      acc[category] = []
    }
    acc[category].push(model)
    return acc
  }, {} as Record<string, Model[]>)

  // فقط سه دسته را نمایش می‌دهیم - OpenRouter اول
  const categoryOrder = ['openrouter', 'openai', 'local']

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
        <SelectTrigger className="w-full min-h-[44px] text-right" dir="rtl">
          <SelectValue placeholder={
            loading ? "در حال بارگذاری..." : 
            error ? "خطا در بارگذاری" : 
            "مدل را انتخاب کنید"
          } />
        </SelectTrigger>
        
        <SelectContent className="max-h-96 text-right [&>*]:text-right" dir="rtl">
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
                      <div className="flex items-center gap-2 justify-end">
                        {getCategoryIcon(category)}
                        <span>{getCategoryLabel(category)} ({categoryModels.length})</span>
                      </div>
                    </div>
                    
                    {categoryModels.map((model) => {
                      const displayCategory = normalizeCategory(model.category, model.provider)
                      
                      return (
                        <SelectItem
                          key={model.id}
                          value={model.id}
                          className="cursor-pointer hover:bg-blue-50 pr-8 pl-2 text-right [&>span]:text-right [&>span]:justify-end"
                        >
                          <div className="flex items-center justify-between w-full gap-3 flex-row-reverse">
                            <div className="flex flex-col items-end gap-1 text-xs flex-shrink-0">
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
                            
                            <div className="flex items-center gap-2 min-w-0 flex-1 flex-row-reverse">
                              <div className="min-w-0 flex-1 text-right">
                                <div className="font-medium text-gray-900 truncate text-right">
                                  {model.name}
                                </div>
                                <div className="text-xs text-gray-500 truncate text-right">
                                  {model.description}
                                </div>
                              </div>
                              <div className="flex-shrink-0">
                                {getCategoryIcon(displayCategory)}
                              </div>
                            </div>
                          </div>
                        </SelectItem>
                      )
                    })}
                  </div>
                )
              })}
            </>
          )}
        </SelectContent>
      </Select>
      
      {selectedModel && !loading && !error && (() => {
        const selectedModelInfo = getModelById(selectedModel) || models.find(m => m.id === selectedModel)
        if (!selectedModelInfo) return null
        
        const displayCategory = normalizeCategory(selectedModelInfo.category, selectedModelInfo.provider)
        
        return (
          <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded-lg text-right">
            <div className="flex items-center gap-2 text-sm text-blue-800 justify-end">
              <span className="font-medium">
                مدل انتخابی: {selectedModelInfo.name}
              </span>
              {getCategoryIcon(displayCategory)}
            </div>
            <p className="text-xs text-blue-600 mt-1">
              {selectedModelInfo.description}
            </p>
          </div>
        )
      })()}
    </div>
  )
}

export default ModelSelector