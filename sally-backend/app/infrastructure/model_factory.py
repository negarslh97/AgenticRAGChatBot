#model_factory.py

"""
Advanced model factory with strategy pattern and dynamic model selection.
"""

import asyncio
import logging
import copy
import json
import os
from typing import Dict, Any, Optional, Type, List, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import time
from functools import lru_cache

from .ai_exceptions import AIException, ErrorType, AISeverity
from .circuit_breaker import CircuitBreaker, circuit_breaker_protect, CircuitBreakerConfig
from .cache_manager import CacheManager, cache_result, CacheConfig
from .security_utils import SecurityManager, SecurityConfig
from app.core.config import settings

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """Supported AI model providers."""
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    LOCAL = "local"


class ModelType(str, Enum):
    """Types of AI models."""
    CHAT = "chat"
    EMBEDDING = "embedding"
    COMPLETION = "completion"
    RERANK = "rerank"
    IMAGE = "image"


@dataclass
class ModelConfig:
    """Configuration for AI models."""
    name: str
    provider: ModelProvider
    model_type: ModelType
    max_tokens: int = 4096
    temperature: float = 0.2
    top_p: float = 1.0
    top_k: Optional[int] = None
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    streaming: bool = False
    force_json: bool = False
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 30
    retry_count: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Validate configuration
        if self.temperature < 0 or self.temperature > 2:
            raise ValueError("Temperature must be between 0 and 2")
        
        if self.max_tokens <= 0:
            raise ValueError("Max tokens must be positive")
        
        if self.top_p <= 0 or self.top_p > 1:
            raise ValueError("Top p must be between 0 and 1")


@dataclass
class ModelCapabilities:
    """Model capabilities and features."""
    supports_streaming: bool = True
    supports_json: bool = True
    supports_tools: bool = False
    supports_vision: bool = False
    supports_embeddings: bool = False
    max_context_length: int = 8192
    cost_per_1k_tokens: Dict[str, float] = field(default_factory=dict)
    languages: List[str] = field(default_factory=list)
    special_features: List[str] = field(default_factory=list)


class BaseModelInterface(ABC):
    """Base interface for all AI models."""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from model."""
        pass
    
    @abstractmethod
    async def generate_stream(self, prompt: str, **kwargs):
        """Generate streaming response from model."""
        pass
    
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Generate embeddings for text."""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> ModelCapabilities:
        """Get model capabilities."""
        pass
    
    @abstractmethod
    def get_config(self) -> ModelConfig:
        """Get model configuration."""
        pass


class OpenAIModel(BaseModelInterface):
    """OpenAI model implementation."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self._capabilities = self._initialize_capabilities()
        cb_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            name=f"openai_{config.name}"
        )
        self._circuit_breaker = CircuitBreaker(cb_config)
    
    def _initialize_capabilities(self) -> ModelCapabilities:
        """Initialize model capabilities based on model name."""
        capabilities = ModelCapabilities()
        
        # Set capabilities based on model type
        if self.config.model_type == ModelType.CHAT:
            capabilities.supports_streaming = True
            capabilities.supports_json = True
            capabilities.supports_tools = True
            capabilities.max_context_length = 128000 if "gpt-4" in self.config.name else 16384
            capabilities.cost_per_1k_tokens = {
                "input": 0.001 if "gpt-3.5" in self.config.name else 0.01,
                "output": 0.002 if "gpt-3.5" in self.config.name else 0.03
            }
        elif self.config.model_type == ModelType.EMBEDDING:
            capabilities.supports_embeddings = True
            capabilities.max_context_length = 8192
            capabilities.cost_per_1k_tokens = {"input": 0.0001}
        
        return capabilities
    
    @circuit_breaker_protect(failure_threshold=3, recovery_timeout=30)
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from OpenAI model."""
        try:
            from langchain_openai import ChatOpenAI
            
            model = ChatOpenAI(
                model=self.config.name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
                frequency_penalty=self.config.frequency_penalty,
                presence_penalty=self.config.presence_penalty,
                streaming=False,
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout
            )
            
            from langchain_core.messages import HumanMessage
            from langchain_core.output_parsers import StrOutputParser
            
            # Use HumanMessage for plain text prompts instead of ChatPromptTemplate
            messages = [HumanMessage(content=prompt)]
            chain = model | StrOutputParser()
            
            result = await chain.ainvoke(messages)
            return result
            
        except Exception as e:
            logger.error(f"OpenAI model generation failed: {e}")
            raise AIException(
                message=f"OpenAI model {self.config.name} failed: {str(e)}",
                error_type=ErrorType.MODEL_UNAVAILABLE,
                severity=AISeverity.HIGH,
                model_name=self.config.name
            )
    
    @circuit_breaker_protect(failure_threshold=3, recovery_timeout=30)
    async def generate_stream(self, prompt: str, **kwargs):
        """Generate streaming response from OpenAI model."""
        try:
            from langchain_openai import ChatOpenAI
            
            model = ChatOpenAI(
                model=self.config.name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
                frequency_penalty=self.config.frequency_penalty,
                presence_penalty=self.config.presence_penalty,
                streaming=True,
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout
            )
            
            from langchain_core.messages import HumanMessage
            
            # Use HumanMessage for plain text prompts instead of ChatPromptTemplate
            messages = [HumanMessage(content=prompt)]
            chain = model
            
            async for chunk in chain.astream(messages):
                if hasattr(chunk, 'content'):
                    yield chunk.content
                else:
                    yield str(chunk)
                    
        except Exception as e:
            logger.error(f"OpenAI model streaming failed: {e}")
            raise AIException(
                message=f"OpenAI model {self.config.name} streaming failed: {str(e)}",
                error_type=ErrorType.MODEL_UNAVAILABLE,
                severity=AISeverity.HIGH,
                model_name=self.config.name
            )
    
    @circuit_breaker_protect(failure_threshold=3, recovery_timeout=30)
    async def embed(self, text: str) -> List[float]:
        """Generate embeddings from OpenAI model."""
        try:
            from langchain_openai import OpenAIEmbeddings
            
            embeddings = OpenAIEmbeddings(
                model=self.config.name,
                api_key=self.config.api_key,
                base_url=self.config.base_url
            )
            
            return await embeddings.aembed_query(text)
            
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise AIException(
                message=f"OpenAI embedding {self.config.name} failed: {str(e)}",
                error_type=ErrorType.MODEL_UNAVAILABLE,
                severity=AISeverity.HIGH,
                model_name=self.config.name
            )
    
    def get_capabilities(self) -> ModelCapabilities:
        """Get model capabilities."""
        return self._capabilities
    
    def get_config(self) -> ModelConfig:
        """Get model configuration."""
        return self.config


class OpenRouterModel(BaseModelInterface):
    """OpenRouter model implementation for non-OpenAI models."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self._capabilities = self._initialize_capabilities()
        cb_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30,
            name=f"openrouter_{config.name}"
        )
        self._circuit_breaker = CircuitBreaker(cb_config)
    
    def _initialize_capabilities(self) -> ModelCapabilities:
        """Initialize model capabilities based on model name."""
        capabilities = ModelCapabilities()
        
        # Set capabilities based on model type
        if self.config.model_type == ModelType.CHAT:
            capabilities.supports_streaming = True
            capabilities.supports_json = True
            capabilities.supports_tools = True
            capabilities.max_context_length = 128000  # Most OpenRouter models support this
            capabilities.cost_per_1k_tokens = {
                "input": 0.001,  # Default cost
                "output": 0.002
            }
            # Add Persian language support
            capabilities.languages = ["fa", "en", "ar", "ur"]
            capabilities.special_features = ["multilingual", "farsi_support"]
        elif self.config.model_type == ModelType.EMBEDDING:
            capabilities.supports_embeddings = True
            capabilities.max_context_length = 8192
            capabilities.cost_per_1k_tokens = {"input": 0.0001}
        
        return capabilities
    
    @circuit_breaker_protect(failure_threshold=3, recovery_timeout=30)
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from OpenRouter model."""
        try:
            from langchain_openai import ChatOpenAI
            
            # Use config base_url or default to OpenRouter
            base_url = self.config.base_url
            
            model = ChatOpenAI(
                model=self.config.name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
                frequency_penalty=self.config.frequency_penalty,
                presence_penalty=self.config.presence_penalty,
                streaming=False,
                api_key=self.config.api_key,
                base_url=base_url,
                timeout=self.config.timeout
            )
            
            from langchain_core.messages import HumanMessage
            from langchain_core.output_parsers import StrOutputParser
            
            # Use HumanMessage for plain text prompts instead of ChatPromptTemplate
            messages = [HumanMessage(content=prompt)]
            chain = model | StrOutputParser()
            
            result = await chain.ainvoke(messages)
            return result
            
        except Exception as e:
            logger.error(f"OpenRouter model generation failed: {e}")
            raise AIException(
                message=f"OpenRouter model {self.config.name} failed: {str(e)}",
                error_type=ErrorType.MODEL_UNAVAILABLE,
                severity=AISeverity.HIGH,
                model_name=self.config.name
            )
    
    @circuit_breaker_protect(failure_threshold=3, recovery_timeout=30)
    async def generate_stream(self, prompt: str, **kwargs):
        """Generate streaming response from OpenRouter model."""
        try:
            from langchain_openai import ChatOpenAI
            
            # Use config base_url or default to OpenRouter
            base_url = self.config.base_url
            
            model = ChatOpenAI(
                model=self.config.name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
                frequency_penalty=self.config.frequency_penalty,
                presence_penalty=self.config.presence_penalty,
                streaming=True,
                api_key=self.config.api_key,
                base_url=base_url,
                timeout=self.config.timeout
            )
            
            from langchain_core.messages import HumanMessage
            
            # Use HumanMessage for plain text prompts instead of ChatPromptTemplate
            messages = [HumanMessage(content=prompt)]
            chain = model
            
            async for chunk in chain.astream(messages):
                if hasattr(chunk, 'content'):
                    yield chunk.content
                else:
                    yield str(chunk)
                    
        except Exception as e:
            logger.error(f"OpenRouter model streaming failed: {e}")
            raise AIException(
                message=f"OpenRouter model {self.config.name} streaming failed: {str(e)}",
                error_type=ErrorType.MODEL_UNAVAILABLE,
                severity=AISeverity.HIGH,
                model_name=self.config.name
            )
    
    @circuit_breaker_protect(failure_threshold=3, recovery_timeout=30)
    async def embed(self, text: str) -> List[float]:
        """Generate embeddings from OpenRouter model."""
        try:
            from langchain_openai import OpenAIEmbeddings
            
            # Use config base_url or default to OpenRouter
            base_url = self.config.base_url
            
            embeddings = OpenAIEmbeddings(
                model=self.config.name,
                api_key=self.config.api_key,
                base_url=base_url
            )
            
            return await embeddings.aembed_query(text)
            
        except Exception as e:
            logger.error(f"OpenRouter embedding generation failed: {e}")
            raise AIException(
                message=f"OpenRouter embedding {self.config.name} failed: {str(e)}",
                error_type=ErrorType.MODEL_UNAVAILABLE,
                severity=AISeverity.HIGH,
                model_name=self.config.name
            )
    
    def get_capabilities(self) -> ModelCapabilities:
        """Get model capabilities."""
        return self._capabilities
    
    def get_config(self) -> ModelConfig:
        """Get model configuration."""
        return self.config


class LocalModel(BaseModelInterface):
    """Local model implementation (Ollama)."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self._capabilities = self._initialize_capabilities()
        cb_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30,
            name=f"local_{config.name}"
        )
        self._circuit_breaker = CircuitBreaker(cb_config)
    
    def _initialize_capabilities(self) -> ModelCapabilities:
        """Initialize model capabilities based on model name."""
        capabilities = ModelCapabilities()
        
        # Set capabilities based on model type
        if self.config.model_type == ModelType.CHAT:
            capabilities.supports_streaming = True
            capabilities.supports_json = True
            capabilities.supports_tools = False
            capabilities.max_context_length = 4096  # Ollama typically has lower context
            capabilities.cost_per_1k_tokens = {"input": 0.0, "output": 0.0}  # Free
            capabilities.languages = ["en", "fa"]
            capabilities.special_features = ["local", "offline"]
        elif self.config.model_type == ModelType.EMBEDDING:
            capabilities.supports_embeddings = True
            capabilities.max_context_length = 8192
            capabilities.cost_per_1k_tokens = {"input": 0.0}
        
        return capabilities
    
    @circuit_breaker_protect(failure_threshold=3, recovery_timeout=30)
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from local model."""
        try:
            from langchain_ollama import ChatOllama
            
            model = ChatOllama(
                model=self.config.name.split(":")[-1],  # Extract model name from "ollama:model-name"
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
                streaming=False,
                base_url=self.config.base_url,
                timeout=self.config.timeout
            )
            
            from langchain_core.messages import HumanMessage
            from langchain_core.output_parsers import StrOutputParser
            
            messages = [HumanMessage(content=prompt)]
            chain = model | StrOutputParser()
            
            result = await chain.ainvoke(messages)
            return result
            
        except Exception as e:
            logger.error(f"Local model generation failed: {e}")
            raise AIException(
                message=f"Local model {self.config.name} failed: {str(e)}",
                error_type=ErrorType.MODEL_UNAVAILABLE,
                severity=AISeverity.HIGH,
                model_name=self.config.name
            )
    
    @circuit_breaker_protect(failure_threshold=3, recovery_timeout=30)
    async def generate_stream(self, prompt: str, **kwargs):
        """Generate streaming response from local model."""
        try:
            from langchain_ollama import ChatOllama
            
            model = ChatOllama(
                model=self.config.name.split(":")[-1],  # Extract model name from "ollama:model-name"
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
                streaming=True,
                base_url=self.config.base_url,
                timeout=self.config.timeout
            )
            
            from langchain_core.messages import HumanMessage
            
            messages = [HumanMessage(content=prompt)]
            chain = model
            
            async for chunk in chain.astream(messages):
                if hasattr(chunk, 'content'):
                    yield chunk.content
                else:
                    yield str(chunk)
                    
        except Exception as e:
            logger.error(f"Local model streaming failed: {e}")
            raise AIException(
                message=f"Local model {self.config.name} streaming failed: {str(e)}",
                error_type=ErrorType.MODEL_UNAVAILABLE,
                severity=AISeverity.HIGH,
                model_name=self.config.name
            )
    
    @circuit_breaker_protect(failure_threshold=3, recovery_timeout=30)
    async def embed(self, text: str) -> List[float]:
        """Generate embeddings from local model."""
        try:
            from langchain_ollama import OllamaEmbeddings
            
            embeddings = OllamaEmbeddings(
                model=self.config.name.split(":")[-1],  # Extract model name from "ollama:model-name"
                base_url=self.config.base_url
            )
            
            return await embeddings.aembed_query(text)
            
        except Exception as e:
            logger.error(f"Local embedding generation failed: {e}")
            raise AIException(
                message=f"Local embedding {self.config.name} failed: {str(e)}",
                error_type=ErrorType.MODEL_UNAVAILABLE,
                severity=AISeverity.HIGH,
                model_name=self.config.name
            )
    
    def get_capabilities(self) -> ModelCapabilities:
        """Get model capabilities."""
        return self._capabilities
    
    def get_config(self) -> ModelConfig:
        """Get model configuration."""
        return self.config


class ModelFactory:
    """Factory for creating and managing AI models."""
    
    def __init__(self, security_config: Optional[SecurityConfig] = None):
        self._models: Dict[str, BaseModelInterface] = {}
        self._configs: Dict[str, ModelConfig] = {}
        self._security_manager = SecurityManager(security_config)
        
        cache_config = CacheConfig(max_size=100, ttl=300)
        self._cache = CacheManager(cache_config)
        
        self._model_strategies: Dict[ModelProvider, Type[BaseModelInterface]] = {
            ModelProvider.OPENAI: OpenAIModel,
            ModelProvider.OPENROUTER: OpenRouterModel,
            ModelProvider.LOCAL: LocalModel,
        }
    
    def register_provider(self, provider: ModelProvider, model_class: Type[BaseModelInterface]):
        """Register a new model provider."""
        self._model_strategies[provider] = model_class
        logger.info(f"Registered model provider: {provider}")
    
    def add_model(self, config: ModelConfig) -> bool:
        """Add a model to the factory."""
        try:
            # Validate model configuration
            if not config.name:
                raise ValueError("Model name is required")
            
            # Check if model already exists
            if config.name in self._models:
                logger.warning(f"Model {config.name} already exists, replacing...")
            
            # Create model instance
            if config.provider not in self._model_strategies:
                raise ValueError(f"Unsupported provider: {config.provider}")
            
            model_class = self._model_strategies[config.provider]
            model_instance = model_class(config)
            
            # Store model and config
            self._models[config.name] = model_instance
            self._configs[config.name] = config
            
            logger.info(f"Added model: {config.name} ({config.provider.value})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add model {config.name}: {e}")
            return False
    
    def get_model(self, model_name: str, **kwargs) -> BaseModelInterface:
        """Get a model instance by name."""
        # 🔧 SAFETY CHECK: If model not found, try to use first available model
        if model_name not in self._models:
            logger.warning(f"Model {model_name} not found in factory")
            logger.warning(f"Available models: {list(self._models.keys())}")
            
            # If no models available at all, raise the original error
            if not self._models:
                raise AIException(
                    message=f"Model {model_name} not found",
                    error_type=ErrorType.MODEL_UNAVAILABLE,
                    severity=AISeverity.HIGH
                )
            
            # Use the first available model as a fallback
            first_model = list(self._models.keys())[0]
            logger.warning(f"Using fallback model: {first_model} instead of {model_name}")
            model_name = first_model
        
        model = self._models[model_name]
        
        # Override config parameters if provided - create a copy to avoid side effects
        if kwargs:
            config = model.get_config()
            # Create a copy of the config to avoid modifying the original
            config_copy = copy.copy(config)
            
            # Apply the overrides to the copy
            for key, value in kwargs.items():
                if hasattr(config_copy, key):
                    setattr(config_copy, key, value)
            
            # Update the model's config with the copy
            model.config = config_copy
        
        return model
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all available models."""
        models_info = []
        for name, model in self._models.items():
            config = model.get_config()
            capabilities = model.get_capabilities()
            
            models_info.append({
                "name": name,
                "provider": config.provider.value,
                "type": config.model_type.value,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
                "streaming": capabilities.supports_streaming,
                "json": capabilities.supports_json,
                "cost_per_1k_tokens": capabilities.cost_per_1k_tokens,
                "max_context_length": capabilities.max_context_length
            })
        
        return models_info
    
    def remove_model(self, model_name: str) -> bool:
        """Remove a model from the factory."""
        if model_name in self._models:
            del self._models[model_name]
            del self._configs[model_name]
            logger.info(f"Removed model: {model_name}")
            return True
        return False
    
    def get_optimal_model(self, task_type: str, context_length: int = 0) -> str:
        """Get optimal model for a specific task."""

         # ✅✅✅ این خطوط را برای دیباگ اضافه کنید ✅✅✅
        logger.info(f"Searching for optimal model for task: '{task_type}'")
        logger.info(f"Available models to choose from: {list(self._models.keys())}")
        # ✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅
        
        task_requirements = {
            "chat": {"streaming": True, "json": True, "min_context": 1000},
            "embedding": {"embeddings": True, "min_context": 100},
            "completion": {"streaming": False, "json": False, "min_context": 500},
            "rag": {"streaming": True, "json": True, "min_context": 2000}
        }
        
        if task_type not in task_requirements:
            raise ValueError(f"Unknown task type: {task_type}")
        
        requirements = task_requirements[task_type]
        best_model = None
        best_score = -1
        
        for name, model in self._models.items():
            capabilities = model.get_capabilities()
            config = model.get_config()
            
            # Check if model meets requirements
            # Ensure model type matches task type
            if task_type == "chat" and config.model_type != ModelType.CHAT:
                continue
            if task_type == "rag" and config.model_type != ModelType.CHAT: # RAG typically uses chat models for generation
                continue
            if task_type == "embedding" and config.model_type != ModelType.EMBEDDING:
                continue
            # Add other task types as needed

            if (requirements.get("streaming", False) and not capabilities.supports_streaming):
                continue
            if (requirements.get("json", False) and not capabilities.supports_json):
                continue
            if (requirements.get("embeddings", False) and not capabilities.supports_embeddings):
                continue
            if context_length > 0 and context_length > capabilities.max_context_length:
                continue
            
            # Calculate score based on requirements
            score = 0
            if capabilities.supports_streaming:
                score += 1
            if capabilities.supports_json:
                score += 1
            if capabilities.supports_embeddings:
                score += 1
            if capabilities.max_context_length >= context_length:
                score += 1
            
            # Prefer models with lower cost
            if hasattr(capabilities, "cost_per_1k_tokens") and "input" in capabilities.cost_per_1k_tokens:
                score += (1 / capabilities.cost_per_1k_tokens["input"])
            
            if score > best_score:
                best_score = score
                best_model = name
        
        if best_model is None:
            # 🔧 SAFETY FALLBACK: If no model meets requirements, use the first available model
            if self._models:
                first_model = list(self._models.keys())[0]
                logger.warning(f"No suitable model found for task '{task_type}', using first available model: {first_model}")
                logger.warning(f"Available models: {list(self._models.keys())}")
                return first_model
            else:
                raise AIException(
                    message=f"No suitable model found for task type: {task_type}",
                    error_type=ErrorType.MODEL_UNAVAILABLE,
                    severity=AISeverity.HIGH
                )
        
        logger.info(f"Selected optimal model: {best_model} for task: {task_type}")
        return best_model
    
    @cache_result(ttl_seconds=300)
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get detailed information about a model."""
        
        if model_name not in self._models:
            raise AIException(
                message=f"Model {model_name} not found",
                error_type=ErrorType.MODEL_UNAVAILABLE,
                severity=AISeverity.HIGH
            )
        
        model = self._models[model_name]
        config = model.get_config()
        capabilities = model.get_capabilities()
        
        return {
            "name": config.name,
            "provider": config.provider.value,
            "type": config.model_type.value,
            "config": {
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
                "top_p": config.top_p,
                "streaming": config.streaming,
                "force_json": config.force_json
            },
            "capabilities": {
                "supports_streaming": capabilities.supports_streaming,
                "supports_json": capabilities.supports_json,
                "supports_tools": capabilities.supports_tools,
                "supports_vision": capabilities.supports_vision,
                "supports_embeddings": capabilities.supports_embeddings,
                "max_context_length": capabilities.max_context_length,
                "cost_per_1k_tokens": capabilities.cost_per_1k_tokens,
                "languages": capabilities.languages,
                "special_features": capabilities.special_features
            },
            "metadata": config.metadata
        }
    
    def validate_model_config(self, config: ModelConfig) -> Dict[str, Any]:
        """Validate model configuration."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required fields
        if not config.name:
            validation_result["valid"] = False
            validation_result["errors"].append("Model name is required")
        
        if not config.provider:
            validation_result["valid"] = False
            validation_result["errors"].append("Model provider is required")
        
        if not config.model_type:
            validation_result["valid"] = False
            validation_result["errors"].append("Model type is required")
        
        # Check if provider is supported
        if config.provider not in self._model_strategies:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Unsupported provider: {config.provider}")
        
        # Check configuration values
        if config.temperature < 0 or config.temperature > 2:
            validation_result["valid"] = False
            validation_result["errors"].append("Temperature must be between 0 and 2")
        
        if config.max_tokens <= 0:
            validation_result["valid"] = False
            validation_result["errors"].append("Max tokens must be positive")
        
        if config.top_p <= 0 or config.top_p > 1:
            validation_result["valid"] = False
            validation_result["errors"].append("Top p must be between 0 and 1")
        
        return validation_result


# Global model factory instance
model_factory = ModelFactory()

# Register default providers
model_factory.register_provider(ModelProvider.OPENAI, OpenAIModel)
model_factory.register_provider(ModelProvider.OPENROUTER, OpenRouterModel)
model_factory.register_provider(ModelProvider.LOCAL, LocalModel)

# Add default models based on centralized config
def _register_default_models():
    """Register AI models based on centralized config file."""
    try:
        models_to_add = []
        
        # خواندن از فایل کانفیگ مرکزی
        # __file__ is in app/infrastructure/model_factory.py
        # Need to go up 2 levels: infrastructure -> app -> root
        current_dir = os.path.dirname(__file__)  # app/infrastructure
        app_dir = os.path.dirname(current_dir)   # app
        root_dir = os.path.dirname(app_dir)      # root (sally-backend)
        models_config_path = os.path.join(root_dir, "config", "models.json")
        
        if not os.path.exists(models_config_path):
            logger.error(f"❌ Models config file not found at: {models_config_path}")
            raise FileNotFoundError(f"Models configuration file not found: {models_config_path}")
        
        try:
            with open(models_config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                models_config = config_data.get("models", [])
            
            if not models_config:
                logger.error("❌ No models found in config file")
                raise ValueError("Models configuration file is empty or invalid")
            
            for model_config_data in models_config:
                try:
                    # تعیین provider بر اساس base_url و model_id (دقیق‌تر)
                    model_id = model_config_data.get("id", "")
                    base_url = model_config_data.get("base_url", "")
                    
                    # اولویت‌بندی تعیین provider:
                    # 1. بر اساس base_url
                    # 2. بر اساس model_id
                    # 3. بر اساس api_key
                    
                    if "openai.com" in base_url:
                        provider = ModelProvider.OPENAI
                        api_key = settings.embedder_api_key_loaded
                    elif "ollama" in model_id or base_url.startswith("http://192.168.10.222:11434"):
                        provider = ModelProvider.LOCAL
                        api_key = None
                        base_url = base_url or settings.ollama_url_loaded if hasattr(settings, 'ollama_url_loaded') else base_url
                    elif "openrouter.ai" in base_url or model_config_data.get("api_key") == "openrouter":
                        provider = ModelProvider.OPENROUTER
                        api_key = settings.openai_api_key_loaded
                    else:
                        # fallback به روش قبلی
                        provider_mapping = {
                            "openai": ModelProvider.OPENAI,
                            "openrouter": ModelProvider.OPENROUTER,
                            "ollama": ModelProvider.LOCAL
                        }
                        provider = provider_mapping.get(
                            model_config_data.get("api_key", "openrouter"),
                            ModelProvider.OPENROUTER
                        )
                        
                        if model_config_data.get("api_key") == "openai":
                            api_key = settings.embedder_api_key_loaded
                        elif model_config_data.get("api_key") == "openrouter":
                            api_key = settings.openai_api_key_loaded
                        elif model_config_data.get("api_key") == "ollama":
                            base_url = settings.ollama_url_loaded if hasattr(settings, 'ollama_url_loaded') else base_url
                    
                    model_config = ModelConfig(
                        name=model_config_data["id"],
                        provider=provider,
                        model_type=ModelType.CHAT,
                        max_tokens=model_config_data.get("max_tokens", 8192),
                        temperature=model_config_data.get("temperature", 0.7),
                        api_key=api_key,
                        base_url=base_url,
                        metadata={
                            "category": model_config_data.get("category", "other"),
                            "description": model_config_data.get("description", ""),
                            "speed": model_config_data.get("speed"),
                            "empty_chunks": model_config_data.get("empty_chunks"),
                            "provider_name": model_config_data.get("provider", ""),
                            "speed_ch_per_s": model_config_data.get("metadata", {}).get("speed_ch_per_s") if isinstance(model_config_data.get("metadata"), dict) else None
                        }
                    )
                    
                    models_to_add.append(model_config)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse model config {model_config_data.get('id', 'unknown')}: {e}")
                    continue
            
            if not models_to_add:
                logger.error("❌ No valid models could be loaded from config file")
                raise ValueError("No valid models found in configuration")
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in models config file: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to load models from config file: {e}")
            raise
        
        # Add all models to factory
        for model_config in models_to_add:
            success = model_factory.add_model(model_config)
            if not success:
                logger.warning(f"Failed to add model {model_config.name}")
        
        logger.info(f"✅ Registered {len(models_to_add)} models from centralized config file")
        
    except Exception as e:
        logger.error(f"❌ Failed to register default models: {e}")
        raise

# Initialize default models
_register_default_models()