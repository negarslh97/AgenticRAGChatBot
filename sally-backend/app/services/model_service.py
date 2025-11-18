"""
Model Management Service
========================

این سرویس مسئولیت مدیریت مدل‌های AI را بر عهده دارد:
- Model detection and provider identification
- Model caching and lifecycle management
- Model configuration and parameter handling
- Provider-specific model initialization

Features:
- Support for multiple providers (OpenAI, OpenRouter, Ollama)
- Intelligent model caching
- Provider-specific optimizations
- Error handling and fallback mechanisms
"""

from typing import Dict, Any, Optional, Union
from enum import Enum
import logging

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from app.core.config import settings
from app.core.logging_config import get_logger
from app.infrastructure.langchain_callbacks import get_default_callbacks

logger = get_logger(__name__)


class ModelProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"          # OpenAI رسمی (gpt-4o, gpt-3.5-turbo, ...)
    OPENROUTER = "openrouter"  # OpenRouter (Grok, Gemini, Claude, Llama, Mistral, ...)
    OLLAMA = "ollama"          # Ollama محلی


class ModelService:
    """
    Service for managing AI models with caching and provider detection
    
    این سرویس مسئولیت‌های زیر را بر عهده دارد:
    - تشخیص provider از نام مدل
    - مدیریت حافظه‌نهان مدل‌ها
    - پیکربندی مدل‌ها بر اساس provider
    - بهینه‌سازی‌های خاص provider
    """
    
    def __init__(self):
        self._models: Dict[str, Any] = {}
        self._callbacks = get_default_callbacks()
        logger.debug("🎯 ModelService initialized")
    
    def detect_model_provider(self, model_name: str) -> ModelProvider:
        """
        تشخیص provider از روی نام مدل با الگوریتم هوشمندتر
        
        🔍 منطق تشخیص پیشرفته:
        - ollama:*       → Ollama (محلی)
        - gpt-*          → OpenAI (رسمی)
        - openai/o1-*    → OpenAI (رسمی - سری o1)
        - openai/*       → OpenAI (رسمی)
        - anthropic/*    → OpenRouter (Claude)
        - google/*       → OpenRouter (Gemini)
        - x-ai/*         → OpenRouter (Grok)
        - meta-llama/*   → OpenRouter (Llama)
        - mistralai/*    → OpenRouter (Mistral)
        - deepseek/*     → OpenRouter (DeepSeek)
        - qwen/*         → OpenRouter (Qwen)
        - cohere/*       → OpenRouter (Cohere)
        - 其他模型名称       → OpenRouter (سایر مدل‌ها)
        
        Args:
            model_name: نام مدل (e.g., "gpt-4o", "x-ai/grok-beta", "google/gemini-2.0")
        
        Returns:
            ModelProvider enum
        """
        if not model_name:
            logger.debug("⚠️ Empty model name provided, defaulting to OpenAI")
            return ModelProvider.OPENAI  # Default
        
        model_lower = model_name.lower()
        
        # ✅ Ollama: prefix با "ollama:"
        if model_lower.startswith("ollama:"):
            logger.debug(f"🔍 Detected Ollama model: {model_name}")
            return ModelProvider.OLLAMA

        # ✅ OpenAI رسمی: شروع با "gpt-" یا "openai/"
        if model_lower.startswith("gpt-") or model_lower.startswith("openai/"):
            logger.debug(f"🔍 Detected OpenAI official model: {model_name}")
            return ModelProvider.OPENAI

        # ✅ لیست دقیق‌تر از مدل‌های OpenRouter
        openrouter_patterns = [
            "anthropic/",      # Claude
            "google/",         # Gemini
            "x-ai/",           # Grok
            "meta-llama/",     # Llama
            "mistralai/",      # Mistral
            "deepseek/",       # DeepSeek
            "qwen/",           # Qwen
            "cohere/",         # Cohere
            "togetherai/",     # Together AI
            "fireworks/",      # Fireworks AI
            "replicate/",      # Replicate
            "huggingface/",    # Hugging Face
            "nousresearch/",   # Nous Research
            "01-ai/",          # 01 AI
            "databricks/",     # Databricks
            "azure/",          # Azure OpenAI
            "nvidia/",         # NVIDIA
            "ibm/",            # IBM
            "aws/",            # AWS Bedrock
            "palmyraai/",      # Palmyra AI
            "recursal/",       # Recursal
            "yandex/",         # Yandex
            "baidu/",          # Baidu
            "tencent/",        # Tencent
            "alibaba/",        # Alibaba
            "xiaohongshu/",    # Xiaohongshu
            "baichuan/",       # Baichuan
            "minimax/",        # Minimax
            "stepfun/",        # StepFun
            "moonshot/",       # Moonshot
            "01-ai/",          # 01 AI
            "doubao/",         # Doubao
            "deepseek/",       # DeepSeek
            "zhihu/",          # Zhihu
            "wenxin/",         # Wenxin
            "spark/",          # Spark
            "kimi/",           # Kimi
            "glm/",            # Zhipu AI
            "chatglm/",        # ChatGLM
            "qwen/",           # Qwen
            "baichuan/",       # Baichuan
            "internlm/",       # InternLM
            "yuan/",           # Yuan
            "deepseek/",       # DeepSeek
            "minimax/",        # Minimax
            "stepfun/",        # StepFun
            "moonshot/",       # Moonshot
            "01-ai/",          # 01 AI
            "doubao/",         # Doubao
            "zhihu/",          # Zhihu
            "wenxin/",         # Wenxin
            "spark/",          # Spark
            "kimi/",           # Kimi
            "glm/",            # Zhipu AI
            "chatglm/",        # ChatGLM
        ]
        
        # بررسی الگوهای OpenRouter
        for pattern in openrouter_patterns:
            if model_lower.startswith(pattern):
                logger.debug(f"🔍 Detected OpenRouter model: {model_name} (pattern: {pattern})")
                return ModelProvider.OPENROUTER
        
        # ✅ سایر مدل‌ها به پیش‌فرض OpenRouter
        logger.debug(f"🔍 Detected OpenRouter model (fallback): {model_name}")
        return ModelProvider.OPENROUTER
    
    def _apply_model_specific_optimizations(self, model_name: str, max_tokens: int, temperature: float) -> tuple[int, float]:
        """
        اعمال بهینه‌سازی‌های خاص مدل
        
        Args:
            model_name: نام مدل
            max_tokens: حداکثر توکن‌های فعلی
            temperature: دمای فعلی
        
        Returns:
            tuple: (max_tokens_optimized, temperature_optimized)
        """
        if not model_name:
            return max_tokens, temperature
            
        model_lower = model_name.lower()
        
        # 🎯 Gemini models: double the max_tokens and adjust temperature for better output quality
        if "gemini" in model_lower:
            original_max_tokens = max_tokens
            max_tokens = max_tokens * 2
            # 🎯 Lower temperature for more accurate responses with Gemini
            original_temperature = temperature
            temperature = min(temperature, 0.2)  # Cap temperature at 0.2 for Gemini
            logger.debug(f"🔥 Gemini model detected: {model_name} - Doubling max_tokens from {original_max_tokens} to {max_tokens}, adjusting temperature from {original_temperature} to {temperature}")
        
        return max_tokens, temperature
    
    def _create_cache_key(self, model_name: str, force_json: bool, max_tokens: int, temperature: float, streaming: bool) -> str:
        """ایجاد کلید حافظه‌نهان برای مدل"""
        return f"{model_name}_{'json' if force_json else 'text'}_{max_tokens}_{temperature}_{'stream' if streaming else 'batch'}"
    
    def _create_ollama_model(self, model_name: str, temperature: float, max_tokens: int) -> ChatOllama:
        """ایجاد مدل Ollama"""
        try:
            # حذف prefix "ollama:" از نام مدل
            actual_model_name = model_name.replace("ollama:", "").replace("Ollama:", "")
            
            ollama_url = settings.ollama_url_loaded
            
            model = ChatOllama(
                model=actual_model_name,
                base_url=ollama_url,
                temperature=temperature,
                num_predict=max_tokens,  # Ollama uses num_predict instead of max_tokens
            )
            logger.debug(f"✅ Ollama model {actual_model_name} ready at {ollama_url}")
            return model
            
        except ImportError:
            logger.debug("❌ langchain-ollama not installed. Install with: pip install -U langchain-ollama")
            raise Exception("Ollama support requires langchain-ollama package")
    
    def _create_openrouter_model(self, model_name: str, temperature: float, max_tokens: int, streaming: bool, force_json: bool = False) -> ChatOpenAI:
        """ایجاد مدل OpenRouter"""
        model_kwargs = {}
        if force_json:
            model_kwargs["response_format"] = {"type": "json_object"}
            logger.debug("📋 JSON mode enabled")

        model = ChatOpenAI(
            model_name=model_name,
            openai_api_key=settings.openai_api_key_loaded,      # 🔑 OpenRouter API Key
            base_url=settings.openai_base_url_loaded,           # 🔗 OpenRouter Base URL
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming,
            callbacks=self._callbacks,
            model_kwargs=model_kwargs
        )
        logger.debug(f"✅ OpenRouter model {model_name} ready (via {settings.openai_base_url_loaded})")
        return model
    
    def _create_openai_model(self, model_name: str, temperature: float, max_tokens: int, streaming: bool, force_json: bool = False) -> ChatOpenAI:
        """ایجاد مدل OpenAI رسمی"""
        model_kwargs = {}
        if force_json:
            model_kwargs["response_format"] = {"type": "json_object"}
            logger.debug("📋 JSON mode enabled")

        model = ChatOpenAI(
            model_name=model_name,
            openai_api_key=settings.embedder_api_key_loaded or settings.openai_api_key_loaded,        # 🔑 OpenAI Official API Key
            base_url=settings.embedder_openai_base_url_loaded or settings.openai_base_url_loaded,     # 🔗 OpenAI Official Base URL
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming,
            callbacks=self._callbacks,
            model_kwargs=model_kwargs
        )
        logger.debug(f"✅ OpenAI model {model_name} ready (Official API)")
        return model
    
    def get_model(
        self,
        model_name: str,
        force_json: bool = False,
        max_tokens: int = 500,
        temperature: float = 0.7,
        streaming: bool = False
    ) -> Union[ChatOpenAI, ChatOllama, Any]:
        """
        دریافت یا ایجاد یک instance از LLM model (پشتیبانی از همه provider ها)

        Args:
            model_name: نام مدل (e.g., "gpt-4o", "ollama:llama3.2", "claude-3-5-sonnet")
            force_json: فعال کردن JSON mode (فقط برای OpenAI)
            max_tokens: حداکثر توکن‌های خروجی
            temperature: دمای sampling
            streaming: فعال کردن streaming

        Returns:
            LLM instance (ChatOpenAI, ChatOllama, etc.)
        """
        # اعمال بهینه‌سازی‌های خاص مدل
        max_tokens, temperature = self._apply_model_specific_optimizations(model_name, max_tokens, temperature)
        
        cache_key = self._create_cache_key(model_name, force_json, max_tokens, temperature, streaming)

        if cache_key not in self._models:
            provider = self.detect_model_provider(model_name)

            logger.debug(
                f"🤖 Loading model: {model_name} (Provider: {provider.value})",
                extra={
                    'extra_data': {
                        'model': model_name,
                        'provider': provider.value,
                        'max_tokens': max_tokens,
                        'temperature': temperature,
                        'json_mode': force_json,
                        'streaming': streaming
                    }
                }
            )

            # بسته به provider، instance مناسب را بسازیم
            if provider == ModelProvider.OLLAMA:
                self._models[cache_key] = self._create_ollama_model(model_name, temperature, max_tokens)
            elif provider == ModelProvider.OPENROUTER:
                self._models[cache_key] = self._create_openrouter_model(model_name, temperature, max_tokens, streaming, force_json)
            else:  # ModelProvider.OPENAI (رسمی)
                self._models[cache_key] = self._create_openai_model(model_name, temperature, max_tokens, streaming, force_json)
        else:
            logger.debug(f"♻️ Using cached model: {cache_key}")
        
        return self._models[cache_key]
    
    def clear_cache(self):
        """پاک کردن حافظه‌نهان مدل‌ها"""
        self._models.clear()
        logger.debug("🗑️ Model cache cleared")
    
    def get_cached_models(self) -> Dict[str, str]:
        """دریافت لیست مدل‌های کش شده"""
        return {key: str(model) for key, model in self._models.items()}


# Global instance
model_service = ModelService()