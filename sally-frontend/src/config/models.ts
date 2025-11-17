// Model configuration interface
export interface ModelConfig {
  id: string;
  name: string;
  provider: string;
  description: string;
  category: string;
  speed?: string;
  empty_chunks?: string;
  max_tokens: number;
  temperature: number;
  supports_streaming: boolean;
  supports_json: boolean;
  api_key: string;
  base_url: string;
  metadata?: {
    category: string;
    speed_ch_per_s?: number;
    empty_chunks?: string;
    description: string;
  };
}

export interface ModelsConfig {
  default_models: {
    rag: string;
    chat: string;
    intent: string;
    embedder: string;
  };
  models: ModelConfig[];
}

// Centralized models configuration
export const MODELS_CONFIG: ModelsConfig = {
  default_models: {
    rag: "google/gemini-2.5-flash",
    chat: "google/gemini-2.5-flash",
    intent: "google/gemini-2.5-flash",
    embedder: "text-embedding-3-large"
  },
  models: [
    {
      id: "google/gemini-2.5-flash",
      name: "Gemini 2.5 Flash",
      provider: "Google",
      description: "✅ سریع‌ترین - 264 ch/s",
      category: "fastest",
      speed: "264 ch/s",
      empty_chunks: "0%",
      max_tokens: 8192,
      temperature: 0.2,
      supports_streaming: true,
      supports_json: true,
      api_key: "openrouter",
      base_url: "https://openrouter.ai/api/v1",
      metadata: {
        category: "fastest",
        speed_ch_per_s: 264,
        empty_chunks: "0%",
        description: "✅ سریع‌ترین - 264 ch/s"
      }
    },
    {
      id: "moonshotai/kimi-linear-48b-a3b-instruct",
      name: "Kimi",
      provider: "MoonshotAI",
      description: "مدل قدرتمند MoonshotAI",
      category: "fastest",
      speed: "264 ch/s",
      empty_chunks: "0%",
      max_tokens: 8192,
      temperature: 0.7,
      supports_streaming: true,
      supports_json: true,
      api_key: "openrouter",
      base_url: "https://openrouter.ai/api/v1",
      metadata: {
        category: "fastest",
        speed_ch_per_s: 264,
        empty_chunks: "0%",
        description: "✅مدل قدرتمند MoonshotAI"
      }
    },
    {
      id: "minimax/minimax-m2",
      name: "MINIMAX M2",
      provider: "minimax",
      description: "مدل سریع MINIMAX",
      category: "fastest",
      max_tokens: 8192,
      temperature: 0.7,
      supports_streaming: true,
      supports_json: true,
      api_key: "openrouter",
      base_url: "https://openrouter.ai/api/v1",
      metadata: {
        category: "fastest",
        description: "مدل سریع MINIMAX"
      }
    },
    {
      id: "deepseek/deepseek-chat-v3.1",
      name: "DeepSeek V3.1",
      provider: "DeepSeek",
      description: "✅مدل قدرتمند DeepSeek",
      category: "free",
      speed: "117 ch/s",
      empty_chunks: "0%",
      max_tokens: 8192,
      temperature: 0.7,
      supports_streaming: true,
      supports_json: true,
      api_key: "openrouter",
      base_url: "https://openrouter.ai/api/v1",
      metadata: {
        category: "free",
        speed_ch_per_s: 117,
        empty_chunks: "0%",
        description: "✅مدل قدرتمند DeepSeek"
      }
    },
    {
      id: "gpt-5",
      name: "GPT-5",
      provider: "OpenAI",
      description: "جدیدترین و پیشرفته‌ترین مدل OpenAI",
      category: "openai",
      max_tokens: 8192,
      temperature: 0.7,
      supports_streaming: true,
      supports_json: true,
      api_key: "openai",
      base_url: "https://api.openai.com/v1",
      metadata: {
        category: "openai",
        description: "جدیدترین و پیشرفته‌ترین مدل OpenAI"
      }
    },
    {
      id: "gpt-5-mini",
      name: "GPT-5 Mini",
      provider: "OpenAI",
      description: "جدیدترین و پیشرفته‌ترین مدل OpenAI",
      category: "openai",
      max_tokens: 8192,
      temperature: 0.7,
      supports_streaming: true,
      supports_json: true,
      api_key: "openai",
      base_url: "https://api.openai.com/v1",
      metadata: {
        category: "openai",
        description: "جدیدترین و پیشرفته‌ترین مدل OpenAI"
      }
    },
    {
      id: "gpt-4o",
      name: "GPT-4o",
      provider: "OpenAI",
      description: "قدرتمندترین OpenAI",
      category: "openai",
      max_tokens: 8192,
      temperature: 0.7,
      supports_streaming: true,
      supports_json: true,
      api_key: "openai",
      base_url: "https://api.openai.com/v1",
      metadata: {
        category: "openai",
        description: "قدرتمندترین OpenAI"
      }
    },
    {
      id: "gpt-4o-mini",
      name: "GPT-4o Mini",
      provider: "OpenAI",
      description: "✅ 89 ch/s، پایدار، کیفیت بالا",
      category: "openai",
      speed: "89 ch/s",
      max_tokens: 8192,
      temperature: 0.7,
      supports_streaming: true,
      supports_json: true,
      api_key: "openai",
      base_url: "https://api.openai.com/v1",
      metadata: {
        category: "openai",
        speed_ch_per_s: 89,
        description: "✅ 89 ch/s، پایدار، کیفیت بالا"
      }
    },
    {
      id: "gpt-4-turbo",
      name: "GPT-4 Turbo",
      provider: "OpenAI",
      description: "نسخه توربو GPT-4",
      category: "openai",
      max_tokens: 8192,
      temperature: 0.7,
      supports_streaming: true,
      supports_json: true,
      api_key: "openai",
      base_url: "https://api.openai.com/v1",
      metadata: {
        category: "openai",
        description: "نسخه توربو GPT-4"
      }
    },
    {
      id: "x-ai/grok-4-fast",
      name: "Grok 4 Fast",
      provider: "xAI",
      description: "مدل قدرتمند xAI",
      category: "heavy",
      speed: "143 ch/s",
      empty_chunks: "70%",
      max_tokens: 8192,
      temperature: 0.7,
      supports_streaming: true,
      supports_json: true,
      api_key: "openrouter",
      base_url: "https://openrouter.ai/api/v1",
      metadata: {
        category: "heavy",
        speed_ch_per_s: 143,
        empty_chunks: "70%",
        description: "مدل قدرتمند xAI"
      }
    },
    {
      id: "ollama:gpt-oss:20b",
      name: "GPT-OSS 20B",
      provider: "Ollama",
      description: "مدل محلی OpenAI",
      category: "ollama",
      max_tokens: 4096,
      temperature: 0.7,
      supports_streaming: true,
      supports_json: true,
      api_key: "ollama",
      base_url: "http://192.168.10.222:11434/api",
      metadata: {
        category: "ollama",
        description: "مدل محلی OpenAI"
      }
    },
    {
      id: "ollama:gemma3n:e4b",
      name: "Gemma 3N E4B",
      provider: "Ollama",
      description: "مدل محلی قدرتمند Google",
      category: "ollama",
      max_tokens: 4096,
      temperature: 0.7,
      supports_streaming: true,
      supports_json: true,
      api_key: "ollama",
      base_url: "http://192.168.10.222:11434/api",
      metadata: {
        category: "ollama",
        description: "مدل محلی قدرتمند Google"
      }
    },
    {
      id: "ollama:llama3.1:8b-instruct-q4_0",
      name: "Llama 3.1 8B",
      provider: "Ollama",
      description: "مدل محلی Meta",
      category: "ollama",
      max_tokens: 4096,
      temperature: 0.7,
      supports_streaming: true,
      supports_json: true,
      api_key: "ollama",
      base_url: "http://192.168.10.222:11434/api",
      metadata: {
        category: "ollama",
        description: "مدل محلی Meta"
      }
    }
  ]
};

// Helper functions
export const getModelById = (id: string): ModelConfig | undefined => {
  return MODELS_CONFIG.models.find(model => model.id === id);
};

export const getDefaultModel = (type: keyof ModelsConfig['default_models']): string => {
  return MODELS_CONFIG.default_models[type];
};

export const getModelsByCategory = (category: string): ModelConfig[] => {
  return MODELS_CONFIG.models.filter(model => model.category === category);
};

export const getGroupedModels = () => {
  return MODELS_CONFIG.models.reduce((acc, model) => {
    const category = model.category;
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(model);
    return acc;
  }, {} as Record<string, ModelConfig[]>);
};

export const getCategoryIcon = (category: string) => {
  switch (category) {
    case 'fastest': return '⚡';
    case 'free': return '👑';
    case 'openai': return '🤖';
    case 'heavy': return '⚠️';
    case 'ollama': return '🖥️';
    default: return '🤖';
  }
};

export const getCategoryLabel = (category: string) => {
  switch (category) {
    case 'fastest': return 'سریع‌ترین';
    case 'free': return 'رایگان';
    case 'openai': return 'OpenAI';
    case 'heavy': return 'سنگین';
    case 'ollama': return 'محلی';
    default: return 'سایر';
  }
};

export const getCategoryColor = (category: string) => {
  switch (category) {
    case 'fastest': return 'text-green-700 bg-green-50 border-green-200';
    case 'free': return 'text-blue-700 bg-blue-50 border-blue-200';
    case 'openai': return 'text-purple-700 bg-purple-50 border-purple-200';
    case 'heavy': return 'text-orange-700 bg-orange-50 border-orange-200';
    case 'ollama': return 'text-gray-700 bg-gray-50 border-gray-200';
    default: return 'text-gray-700 bg-gray-50 border-gray-200';
  }
};

// Get all category names in order
export const getCategoryOrder = () => ['fastest', 'free', 'openai', 'heavy', 'ollama', 'other'];