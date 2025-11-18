import { ChatBaseService } from './baseService'
import { ChatStreamingService } from './streamingService'
import { ChatModelService } from './modelService'
import { 
  ChatResponse, 
  Conversation, 
  ChatMessage, 
  SendMessageData,
  RatingStats,
  AdvancedAgenticMessageData,
  AdvancedAgenticResponse,
  StreamEvent,
  AvailableModelsResponse,
  ModelInfo
} from './types'

// Create service instances
const baseService = new ChatBaseService()
const streamingService = new ChatStreamingService()
const modelService = new ChatModelService()

export const chatService = {
  // Base API operations
  sendMessage: baseService.sendMessage.bind(baseService),
  sendAdminMessage: baseService.sendAdminMessage.bind(baseService),
  getConversations: baseService.getConversations.bind(baseService),
  getConversation: baseService.getConversation.bind(baseService),
  deleteConversation: baseService.deleteConversation.bind(baseService),
  updateConversationTitle: baseService.updateConversationTitle.bind(baseService),
  getConversationMessages: baseService.getConversationMessages.bind(baseService),
  rateMessage: baseService.rateMessage.bind(baseService),
  getConversationRatingStats: baseService.getConversationRatingStats.bind(baseService),
  sendAdvancedAgenticMessage: baseService.sendAdvancedAgenticMessage.bind(baseService),

  // Streaming operations
  sendMessageStream: streamingService.sendMessageStream.bind(streamingService),
  sendAdminMessageStream: streamingService.sendAdminMessageStream.bind(streamingService),
  sendAdvancedAgenticMessageStream: streamingService.sendAdvancedAgenticMessageStream.bind(streamingService),

  // Model operations
  getAvailableModels: modelService.getAvailableModels.bind(modelService),
  getDefaultModel: modelService.getDefaultModel.bind(modelService),
  getModelInfo: modelService.getModelInfo.bind(modelService),
  getModelById: modelService.getModelById.bind(modelService),
  getGroupedModels: modelService.getGroupedModels.bind(modelService),
  getFastestModels: modelService.getFastestModels.bind(modelService),
  getFreeModels: modelService.getFreeModels.bind(modelService),
  getOpenAIModels: modelService.getOpenAIModels.bind(modelService),
  getHeavyModels: modelService.getHeavyModels.bind(modelService),
  getOllamaModels: modelService.getOllamaModels.bind(modelService),
  getOtherModels: modelService.getOtherModels.bind(modelService),
  getModelsByCategory: modelService.getModelsByCategory.bind(modelService),
  modelSupportsStreaming: modelService.modelSupportsStreaming.bind(modelService),
  modelSupportsJSON: modelService.modelSupportsJSON.bind(modelService),
  getModelTemperatureRange: modelService.getModelTemperatureRange.bind(modelService),
  getModelMaxTokens: modelService.getModelMaxTokens.bind(modelService),
  getModelSpeed: modelService.getModelSpeed.bind(modelService),
  getModelEmptyChunks: modelService.getModelEmptyChunks.bind(modelService),

  // Type exports for convenience
  types: {
    ChatResponse: require('./types').ChatResponse,
    Conversation: require('./types').Conversation,
    ChatMessage: require('./types').ChatMessage,
    SendMessageData: require('./types').SendMessageData,
    RatingStats: require('./types').RatingStats,
    AdvancedAgenticMessageData: require('./types').AdvancedAgenticMessageData,
    AdvancedAgenticResponse: require('./types').AdvancedAgenticResponse,
    StreamEvent: require('./types').StreamEvent,
    AvailableModelsResponse: require('./types').AvailableModelsResponse,
    ModelInfo: require('./types').ModelInfo
  }
}

// Export service classes for advanced use cases
export { ChatBaseService, ChatStreamingService, ChatModelService }

// Export types
export * from './types'