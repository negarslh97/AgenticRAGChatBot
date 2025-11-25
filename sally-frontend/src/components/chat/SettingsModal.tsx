'use client'

import React from 'react'
import { X, Settings, Thermometer, Sparkles, Brain, BookOpen } from 'lucide-react'
import { Button } from '../ui/button'
import ModelSelector from '../ModelSelector'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
  selectedModel: string
  onModelChange: (modelId: string) => void
  temperature: number
  onTemperatureChange: (temp: number) => void
  ragType: 'simple' | 'agentic'
  onRagTypeChange: (ragType: 'simple' | 'agentic') => void
  availableModels?: any[]
}

const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  selectedModel,
  onModelChange,
  temperature,
  onTemperatureChange,
  ragType,
  onRagTypeChange,
  availableModels = []
}) => {
  if (!isOpen) return null

  const getTemperatureColor = (temp: number) => {
    if (temp <= 0.5) return 'text-blue-600'
    if (temp <= 1.0) return 'text-purple-600'
    return 'text-pink-600'
  }

  const getTemperatureBg = (temp: number) => {
    if (temp <= 0.5) return 'bg-blue-50 border-blue-200'
    if (temp <= 1.0) return 'bg-purple-50 border-purple-200'
    return 'bg-pink-50 border-pink-200'
  }

  return (
    <div 
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200" 
      onClick={onClose}
    >
      <div 
        className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-gray-100 animate-in zoom-in-95 duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header with Gradient */}
        <div className="relative bg-gradient-to-r from-purple-600 via-blue-600 to-purple-600 p-6 rounded-t-2xl">
          <div className="absolute inset-0 bg-black/5 rounded-t-2xl"></div>
          <div className="relative flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white/20 rounded-lg backdrop-blur-sm">
                <Settings className="h-5 w-5 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">تنظیمات پیشرفته</h2>
                <p className="text-sm text-white/80 mt-0.5">تنظیم مدل AI و پارامترهای پاسخ</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-lg transition-colors duration-200 group"
              aria-label="بستن"
            >
              <X className="h-5 w-5 text-white group-hover:rotate-90 transition-transform duration-300" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gradient-to-b from-gray-50 to-white">
          {/* Model Selection Card */}
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
            <div className="flex items-center gap-2 mb-4">
              <div className="p-2 bg-gradient-to-br from-purple-100 to-blue-100 rounded-lg">
                <Sparkles className="h-5 w-5 text-purple-600" />
              </div>
              <h3 className="text-base font-semibold text-gray-900">انتخاب مدل AI</h3>
            </div>
            <ModelSelector
              selectedModel={selectedModel}
              onModelChange={onModelChange}
              className="w-full"
            />
          </div>

          {/* Temperature Selection Card */}
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-gradient-to-br from-orange-100 to-pink-100 rounded-lg">
                  <Thermometer className="h-5 w-5 text-orange-600" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-gray-900">دمای مدل</h3>
                  <p className="text-xs text-gray-500 mt-0.5">کنترل خلاقیت و دقت پاسخ</p>
                </div>
              </div>
              <div className={`px-4 py-2 rounded-lg border-2 font-bold text-lg ${getTemperatureBg(temperature)} ${getTemperatureColor(temperature)}`}>
                {temperature.toFixed(1)}
              </div>
            </div>
            
            <div className="space-y-4">
              {/* Custom Range Slider */}
              <div className="relative">
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => onTemperatureChange(parseFloat(e.target.value))}
                  className="w-full h-3 bg-gradient-to-r from-blue-200 via-purple-200 to-pink-200 rounded-full appearance-none cursor-pointer"
                  style={{
                    background: `linear-gradient(to right, #3b82f6 0%, #a855f7 ${(temperature / 2) * 50}%, #ec4899 ${(temperature / 2) * 100}%)`
                  }}
                />
                <style dangerouslySetInnerHTML={{__html: `
                  input[type="range"]::-webkit-slider-thumb {
                    appearance: none;
                    width: 20px;
                    height: 20px;
                    border-radius: 50%;
                    background: white;
                    border: 3px solid #6366f1;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                    cursor: pointer;
                    transition: all 0.2s;
                  }
                  input[type="range"]::-webkit-slider-thumb:hover {
                    transform: scale(1.2);
                    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
                  }
                  input[type="range"]::-moz-range-thumb {
                    width: 20px;
                    height: 20px;
                    border-radius: 50%;
                    background: white;
                    border: 3px solid #6366f1;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                    cursor: pointer;
                    transition: all 0.2s;
                  }
                  input[type="range"]::-moz-range-thumb:hover {
                    transform: scale(1.2);
                    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
                  }
                `}} />
              </div>

              {/* Temperature Labels */}
              <div className="flex items-center justify-between px-2">
                <div className="flex flex-col items-center gap-1">
                  <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                  <span className="text-xs text-gray-600 font-medium">محافظه‌کارانه</span>
                  <span className="text-xs text-gray-400">0.0</span>
                </div>
                <div className="flex flex-col items-center gap-1">
                  <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                  <span className="text-xs text-gray-600 font-medium">متعادل</span>
                  <span className="text-xs text-gray-400">1.0</span>
                </div>
                <div className="flex flex-col items-center gap-1">
                  <div className="w-2 h-2 rounded-full bg-pink-500"></div>
                  <span className="text-xs text-gray-600 font-medium">خلاقانه</span>
                  <span className="text-xs text-gray-400">2.0</span>
                </div>
              </div>

              {/* Info Card */}
              <div className={`mt-4 p-4 rounded-lg border-2 ${getTemperatureBg(temperature)} transition-all duration-300`}>
                <div className="flex items-start gap-3">
                  <div className={`p-1.5 rounded-lg ${temperature <= 0.7 ? 'bg-blue-100' : temperature <= 1.3 ? 'bg-purple-100' : 'bg-pink-100'}`}>
                    <Sparkles className={`h-4 w-4 ${temperature <= 0.7 ? 'text-blue-600' : temperature <= 1.3 ? 'text-purple-600' : 'text-pink-600'}`} />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-800 mb-1">
                      {temperature <= 0.7 
                        ? 'حالت محافظه‌کارانه فعال است'
                        : temperature <= 1.3 
                        ? 'حالت متعادل فعال است'
                        : 'حالت خلاقانه فعال است'}
                    </p>
                    <p className="text-xs text-gray-600 leading-relaxed">
                      {temperature <= 0.7
                        ? 'پاسخ‌های دقیق و قابل پیش‌بینی. مناسب برای سوالات فنی و اطلاعاتی.'
                        : temperature <= 1.3
                        ? 'تعادل بین دقت و خلاقیت. مناسب برای اکثر کاربردها.'
                        : 'پاسخ‌های خلاقانه و متنوع. مناسب برای محتوای هنری و داستان‌نویسی.'}
                    </p>
                  </div>
                </div>
      
                {/* RAG Type Selection Card */}
                <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="p-2 bg-gradient-to-br from-green-100 to-blue-100 rounded-lg">
                      <Brain className="h-5 w-5 text-green-600" />
                    </div>
                    <div>
                      <h3 className="text-base font-semibold text-gray-900">نوع سیستم پاسخ‌دهی</h3>
                      <p className="text-xs text-gray-500 mt-0.5">انتخاب نحوه پردازش و پاسخ به سوالات</p>
                    </div>
                  </div>
                  
                  <div className="space-y-3">
                    {/* Simple RAG Option */}
                    <div
                      className={`p-4 rounded-lg border-2 cursor-pointer transition-all duration-200 ${
                        ragType === 'simple'
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50/50'
                      }`}
                      onClick={() => onRagTypeChange('simple')}
                    >
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-blue-100 rounded-lg">
                          <BookOpen className="h-4 w-4 text-blue-600" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="text-sm font-semibold text-gray-900">ساده (Simple)</h4>
                            {ragType === 'simple' && (
                              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                            )}
                          </div>
                          <p className="text-xs text-gray-600 leading-relaxed">
                            پاسخ‌های مستقیم و کوتاه بر اساس اطلاعات موجود. مناسب برای سوالات ساده و پاسخ‌های سریع.
                          </p>
                        </div>
                      </div>
                    </div>
      
                    {/* Agentic RAG Option */}
                    <div
                      className={`p-4 rounded-lg border-2 cursor-pointer transition-all duration-200 ${
                        ragType === 'agentic'
                          ? 'border-purple-500 bg-purple-50'
                          : 'border-gray-200 hover:border-purple-300 hover:bg-purple-50/50'
                      }`}
                      onClick={() => onRagTypeChange('agentic')}
                    >
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-purple-100 rounded-lg">
                          <Brain className="h-4 w-4 text-purple-600" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="text-sm font-semibold text-gray-900">هوشمند (Agentic)</h4>
                            {ragType === 'agentic' && (
                              <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                            )}
                          </div>
                          <p className="text-xs text-gray-600 leading-relaxed">
                            پاسخ‌های تحلیلی و جامع با بررسی چندمنبعی. مناسب برای سوالات پیچیده و نیاز به درک عمیق.
                          </p>
                        </div>
                      </div>
                    </div>
      
                  </div>
      
                  {/* Current Selection Info */}
                  <div className="mt-4 p-4 rounded-lg border-2 bg-gradient-to-r from-purple-50 to-blue-50 border-purple-200">
                    <div className="flex items-start gap-3">
                      <div className="p-1.5 bg-purple-100 rounded-lg">
                        {ragType === 'simple' && <BookOpen className="h-4 w-4 text-blue-600" />}
                        {ragType === 'agentic' && <Brain className="h-4 w-4 text-purple-600" />}
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-800 mb-1">
                          {ragType === 'simple' && 'حالت ساده فعال است'}
                          {ragType === 'agentic' && 'حالت هوشمند فعال است'}
                        </p>
                        <p className="text-xs text-gray-600 leading-relaxed">
                          {ragType === 'simple' && 'پاسخ‌های کوتاه و مستقیم برای سوالات ساده'}
                          {ragType === 'agentic' && 'تحلیل عمیق و پاسخ‌های جامع برای سوالات پیچیده'}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-6 border-t border-gray-200 bg-white rounded-b-2xl">
          <Button
            onClick={onClose}
            variant="outline"
            className="px-6"
          >
            انصراف
          </Button>
          <Button
            onClick={onClose}
            className="px-6 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105"
          >
            ذخیره تنظیمات
          </Button>
        </div>
      </div>
    </div>
  )
}

export default SettingsModal

