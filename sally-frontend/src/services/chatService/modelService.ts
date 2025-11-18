import { MODELS_CONFIG, getGroupedModels, getModelById } from '../../config/models'
import { AvailableModelsResponse, ModelInfo } from './types'

export class ChatModelService {
  async getAvailableModels(): Promise<AvailableModelsResponse> {
    try {
      const response = await fetch('/api/system/models')
      if (response.ok) {
        const data = await response.json()
        return data.data
      }
      throw new Error('Failed to fetch models from API')
    } catch (error: any) {
      console.error("Failed to get available models from API:", error)
      console.log("Using local model config as fallback")
      
      const groupedModels = getGroupedModels()
      
      return {
        models: MODELS_CONFIG.models.map(model => ({
          id: model.id,
          name: model.name,
          provider: model.provider,
          description: model.description,
          category: model.category,
          speed: model.speed,
          empty_chunks: model.empty_chunks,
          max_tokens: model.max_tokens,
          temperature: model.temperature,
          supports_streaming: model.supports_streaming,
          supports_json: model.supports_json
        })),
        categories: {
          fastest: groupedModels.fastest || [],
          free: groupedModels.free || [],
          openai: groupedModels.openai || [],
          heavy: groupedModels.heavy || [],
          ollama: groupedModels.ollama || [],
          other: groupedModels.other || []
        },
        default_model: MODELS_CONFIG.default_models.chat,
        total_count: MODELS_CONFIG.models.length
      }
    }
  }

  getDefaultModel(): string {
    return MODELS_CONFIG.default_models.chat
  }

  getModelInfo(modelId: string): ModelInfo | undefined {
    return getModelById(modelId)
  }

  getModelById(modelId: string): ModelInfo | undefined {
    return MODELS_CONFIG.models.find(model => model.id === modelId)
  }

  getGroupedModels() {
    return getGroupedModels()
  }

  // Helper methods for model categories
  getFastestModels(): ModelInfo[] {
    return this.getGroupedModels().fastest || []
  }

  getFreeModels(): ModelInfo[] {
    return this.getGroupedModels().free || []
  }

  getOpenAIModels(): ModelInfo[] {
    return this.getGroupedModels().openai || []
  }

  getHeavyModels(): ModelInfo[] {
    return this.getGroupedModels().heavy || []
  }

  getOllamaModels(): ModelInfo[] {
    return this.getGroupedModels().ollama || []
  }

  getOtherModels(): ModelInfo[] {
    return this.getGroupedModels().other || []
  }

  // Filter models by category
  getModelsByCategory(category: string): ModelInfo[] {
    switch (category) {
      case 'fastest':
        return this.getFastestModels()
      case 'free':
        return this.getFreeModels()
      case 'openai':
        return this.getOpenAIModels()
      case 'heavy':
        return this.getHeavyModels()
      case 'ollama':
        return this.getOllamaModels()
      case 'other':
        return this.getOtherModels()
      default:
        return []
    }
  }

  // Check if model supports streaming
  modelSupportsStreaming(modelId: string): boolean {
    const model = this.getModelById(modelId)
    return model?.supports_streaming || false
  }

  // Check if model supports JSON output
  modelSupportsJSON(modelId: string): boolean {
    const model = this.getModelById(modelId)
    return model?.supports_json || false
  }

  // Get model temperature range
  getModelTemperatureRange(modelId: string): { min: number; max: number; step: number } {
    const model = this.getModelById(modelId)
    if (!model) {
      return { min: 0, max: 2, step: 0.1 }
    }
    
    return {
      min: 0,
      max: model.temperature || 2,
      step: 0.1
    }
  }

  // Get model max tokens
  getModelMaxTokens(modelId: string): number {
    const model = this.getModelById(modelId)
    return model?.max_tokens || 4096
  }

  // Get model speed description
  getModelSpeed(modelId: string): string {
    const model = this.getModelById(modelId)
    return model?.speed || 'Unknown'
  }

  // Get model empty chunks behavior
  getModelEmptyChunks(modelId: string): string {
    const model = this.getModelById(modelId)
    return model?.empty_chunks || 'Unknown'
  }
}