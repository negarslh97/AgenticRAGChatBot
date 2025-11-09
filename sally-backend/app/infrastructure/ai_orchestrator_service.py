# ai_orchestrator_service.py

"""
🚀 AI Orchestrator Service - مغز و نقطه ورود اصلی تمام عملیات‌های هوش مصنوعی
=================================================================================

این سرویس به عنوان نقطه مرکزی و کنترل‌کننده اصلی تمام عملیات‌های AI عمل می‌کند.

## جریان کاری ۸ مرحله‌ای:

1. **امنیت ورودی:** SecurityManager ورودی کاربر را اعتبارسنجی می‌کند
2. **تحلیل سوال:** QueryAnalyzer نوع سوال و پیچیدگی آن را تشخیص می‌دهد  
3. **بازیابی اطلاعات (RAG):** KnowledgeBaseRepository (با CircuitBreaker) context می‌یابد
4. **انتخاب مدل:** ModelFactory بهترین مدل را انتخاب می‌کند
5. **تولید پاسخ:** ResponseGenerator با مدل انتخاب شده پاسخ تولید می‌کند
6. **امنیت خروجی:** SecurityManager خروجی مدل را پاک‌سازی می‌کند
7. **کش کردن:** @cache_result کل فرآیند را کش می‌کند
8. **مدیریت خطا:** AIException و RecoveryManager مدیریت می‌کند
"""

import asyncio
import logging
import time
import functools
import traceback
from typing import Dict, Any, Optional, List, Union, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum

from .ai_exceptions import AIException, ErrorType, AISeverity
from .circuit_breaker import circuit_breaker_protect, CircuitBreaker
from .cache_manager import cache_result, CacheManager, CacheConfig, CacheStrategy
from .security_utils import SecurityManager, SecurityConfig, SecurityLevel
from .model_factory import ModelFactory, ModelConfig, model_factory
from .connection_manager import get_weaviate_manager, get_mongodb_manager
from .conversation_memory_service import ConversationMemoryService
from .langchain_orchestrator import QueryType, ResponseStyle, RequestContext, ResponseResult

# Import query analyzer
from app.utils.query_analyzer import query_analyzer

logger = logging.getLogger(__name__)


class RequestType(str, Enum):
    """انواع درخواست"""
    CHAT = "chat"
    RAG = "rag"
    CONVERSATIONAL = "conversational"
    METADATA = "metadata"
    CONVERSION = "conversion"


@dataclass
class ProcessingRequest:
    """درخواست پردازش کامل"""
    query: str
    request_type: RequestType = RequestType.RAG
    context: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    custom_model: Optional[str] = None
    custom_temperature: Optional[float] = None
    agentic_mode: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validation و setup اضافی"""
        if not self.query or not self.query.strip():
            raise AIException(
                message="Query cannot be empty",
                error_type=ErrorType.INVALID_INPUT,
                severity=AISeverity.MEDIUM
            )
    
    def to_request_context(self) -> RequestContext:
        """تبدیل به RequestContext برای سازگاری با orchestrator موجود"""
        query_type_map = {
            RequestType.CHAT: QueryType.SPECIFIC,
            RequestType.RAG: QueryType.GENERAL,
            RequestType.CONVERSATIONAL: QueryType.CONVERSATIONAL
        }
        
        return RequestContext(
            query=self.query,
            context=self.context,
            conversation_history=self.conversation_history,
            query_type=query_type_map.get(self.request_type, QueryType.GENERAL),
            response_style=ResponseStyle.DETAILED,
            user_id=self.user_id,
            session_id=self.session_id,
            custom_model=self.custom_model,
            custom_temperature=self.custom_temperature,
            streaming=False,  # Will be set by processor
            agentic_mode=self.agentic_mode,
            metadata=self.metadata
        )


@dataclass
class ProcessingResult:
    """نتیجه پردازش کامل"""
    success: bool
    response: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None
    circuit_breaker_states: Dict[str, str] = field(default_factory=dict)
    cache_hit: bool = False
    analysis_result: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """تبدیل به dictionary برای JSON response"""
        return {
            "success": self.success,
            "response": self.response,
            "metadata": self.metadata,
            "processing_time": self.processing_time,
            "error": self.error,
            "error_type": self.error_type.value if self.error_type else None,
            "circuit_breaker_states": self.circuit_breaker_states,
            "cache_hit": self.cache_hit,
            "analysis": {
                "complexity": self.analysis_result.complexity.value if self.analysis_result else None,
                "intent": self.analysis_result.intent.value if self.analysis_result else None,
                "needs_rag": self.analysis_result.needs_rag if self.analysis_result else None
            } if self.analysis_result else None
        }


class AIOrchestratorService:
    """
    🚀 AI Orchestrator Service - مغز اصلی سیستم AI
    
    این سرویس تمام عملیات‌های AI را هماهنگ و کنترل می‌کند.
    """
    
    def __init__(self):
        """Initialization با تمام components مورد نیاز"""
        # Initialize security
        security_config = SecurityConfig(level=SecurityLevel.STANDARD)
        self.security_manager = SecurityManager(security_config)
        
        # Initialize model factory
        self.model_factory = model_factory
        
        # Initialize conversation memory
        self.memory_service = ConversationMemoryService()
        
        # Initialize connection managers
        self.weaviate_manager = get_weaviate_manager()
        self.mongodb_manager = get_mongodb_manager()
        
        # Initialize cache manager with default config
        cache_config = CacheConfig(
            strategy=CacheStrategy.LRU,
            max_size=1000,
            ttl=300,
            background_cleanup=True,
            cleanup_interval=60
        )
        self.cache_manager = CacheManager(cache_config)
        
        logger.info("🚀 AI Orchestrator Service initialized with all components")
    
    async def process_request(
        self,
        request: ProcessingRequest,
        streaming: bool = False
    ):
        """
        🧠 پردازش کامل درخواست با ۸ مرحله اصلی
        
        Args:
            request: درخواست پردازش
            streaming: آیا streaming response می‌خواهیم
            
        Returns:
            ProcessingResult for non-streaming
            AsyncGenerator for streaming
        """
        if streaming:
            return self._process_request_streaming(request)
        else:
            return await self._process_request_regular(request)
    
    async def _process_request_regular(self, request: ProcessingRequest) -> ProcessingResult:
        """پردازش regular (non-streaming) درخواست"""
        start_time = time.time()
        processing_metadata = {
            "start_time": start_time,
            "query": request.query[:100] + "..." if len(request.query) > 100 else request.query,
            "request_type": request.request_type.value
        }
        
        try:
            # مرحله ۱: امنیت ورودی - اعتبارسنجی ورودی کاربر
            logger.info("🔒 مرحله ۱: امنیت ورودی - اعتبارسنجی ورودی")
            validation_result = self.security_manager.validate_user_input(request.query)
            if not validation_result["valid"]:
                raise AIException(
                    message=f"Input validation failed: {validation_result['errors']}",
                    error_type=ErrorType.INVALID_INPUT,
                    severity=AISeverity.MEDIUM
                )
            
            # مرحله ۲: تحلیل سوال - تشخیص نوع و پیچیدگی
            logger.info("🔍 مرحله ۲: تحلیل سوال - تشخیص نوع و پیچیدگی")
            analysis_result = await query_analyzer.analyze(
                request.query,
                tuple(request.conversation_history) if request.conversation_history else None
            )
            processing_metadata["analysis"] = {
                "intent": analysis_result.intent.value,
                "complexity": analysis_result.complexity.value,
                "needs_rag": analysis_result.needs_rag,
                "confidence": analysis_result.confidence
            }
            
            # مرحله ۳: بازیابی اطلاعات (RAG) - جستجو در knowledge base
            context = None
            if analysis_result.needs_rag or request.request_type == RequestType.RAG:
                logger.info("📚 مرحله ۳: بازیابی اطلاعات (RAG) - جستجو در knowledge base")
                context = await self._retrieve_context(request, analysis_result)
            
            # مرحله ۴: انتخاب مدل - ModelFactory
            logger.info("🤖 مرحله ۴: انتخاب مدل - ModelFactory")
            optimal_model = self.model_factory.get_optimal_model(
                "rag" if context else "chat",
                context_length=len(context) if context else 0
            )
            processing_metadata["selected_model"] = optimal_model
            
            # مرحله ۵: تولید پاسخ - ResponseGenerator
            logger.info("✍️ مرحله ۵: تولید پاسخ - ResponseGenerator")
            request_context = request.to_request_context()
            request_context.context = context
            request_context.streaming = False
            
            # Non-streaming response
            response_result = await self._generate_response(request_context, analysis_result)
            
            # مرحله ۶: امنیت خروجی - پاک‌سازی output
            logger.info("🛡️ مرحله ۶: امنیت خروجی - پاک‌سازی output")
            sanitized_response = self.security_manager.sanitize_output(response_result.content)
            
            return ProcessingResult(
                success=True,
                response=sanitized_response,
                metadata={**processing_metadata, **response_result.metadata},
                processing_time=time.time() - start_time,
                analysis_result=analysis_result,
                circuit_breaker_states=self._get_circuit_breaker_states()
            )
                
        except AIException as e:
            # مرحله ۸: مدیریت خطا - AIException handling
            logger.error(f"❌ AI Exception in processing: {e}")
            return ProcessingResult(
                success=False,
                response="متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم.",
                error=str(e),
                error_type=e.error_type,
                processing_time=time.time() - start_time,
                circuit_breaker_states=self._get_circuit_breaker_states()
            )
            
        except Exception as e:
            logger.error(f"❌ Unexpected error in processing: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                response="خطای غیرمنتظره‌ای رخ داد. لطفاً بعداً دوباره تلاش کنید.",
                error=str(e),
                error_type=ErrorType.UNKNOWN_ERROR,
                processing_time=time.time() - start_time,
                circuit_breaker_states=self._get_circuit_breaker_states()
            )
    
    async def _process_request_streaming(self, request: ProcessingRequest) -> AsyncGenerator[str, None]:
        """فقط برای streaming responses"""
        start_time = time.time()
        processing_metadata = {
            "start_time": start_time,
            "query": request.query[:100] + "..." if len(request.query) > 100 else request.query,
            "request_type": request.request_type.value
        }
        
        try:
            # مراحل ۱-۴ مشابه Regular processing
            logger.info("🔒 مرحله ۱: امنیت ورودی - اعتبارسنجی ورودی")
            validation_result = self.security_manager.validate_user_input(request.query)
            if not validation_result["valid"]:
                yield "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم."
                return
                
            logger.info("🔍 مرحله ۲: تحلیل سوال - تشخیص نوع و پیچیدگی")
            analysis_result = await query_analyzer.analyze(
                request.query,
                tuple(request.conversation_history) if request.conversation_history else None
            )
            processing_metadata["analysis"] = {
                "intent": analysis_result.intent.value,
                "complexity": analysis_result.complexity.value,
                "needs_rag": analysis_result.needs_rag,
                "confidence": analysis_result.confidence
            }
            
            # مرحله ۳: RAG
            context = None
            if analysis_result.needs_rag or request.request_type == RequestType.RAG:
                logger.info("📚 مرحله ۳: بازیابی اطلاعات (RAG)")
                context = await self._retrieve_context(request, analysis_result)
            
            # مرحله ۴: انتخاب مدل
            logger.info("🤖 مرحله ۴: انتخاب مدل")
            optimal_model = self.model_factory.get_optimal_model(
                "rag" if context else "chat",
                context_length=len(context) if context else 0
            )
            processing_metadata["selected_model"] = optimal_model
            
            # مرحله ۵: تولید پاسخ
            logger.info("✍️ مرحله ۵: تولید پاسخ streaming")
            request_context = request.to_request_context()
            request_context.context = context
            request_context.streaming = True
            
            async for chunk in self._generate_streaming_response(request_context):
                yield chunk
                
        except AIException as e:
            logger.error(f"❌ AI Exception in streaming: {e}")
            yield "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم."
        except Exception as e:
            logger.error(f"❌ Unexpected error in streaming: {e}", exc_info=True)
            yield "خطای غیرمنتظره‌ای رخ داد. لطفاً بعداً دوباره تلاش کنید."
    
    async def _retrieve_context(self, request: ProcessingRequest, analysis_result) -> Optional[str]:
        """مرحله ۳: بازیابی context از knowledge base"""
        try:
            # استفاده از knowledge base repository (با circuit breaker protection)
            with self.weaviate_manager.get_client() as weaviate_client:
                # جستجوی ساده در collections
                # TODO: پیاده‌سازی کامل RAG retrieval
                logger.info(f"🔍 Searching for context with keywords: {analysis_result.keywords}")
                return f"Retrieved context for query: {request.query}"
        except Exception as e:
            logger.warning(f"⚠️ Failed to retrieve context: {e}")
            return None
    
    async def _generate_response(self, request_context: RequestContext, analysis_result) -> ResponseResult:
        """مرحله ۵: تولید response با استفاده از orchestrator موجود"""
        try:
            from .langchain_orchestrator import ResponseGenerator
            
            response_generator = ResponseGenerator(self.model_factory, self.security_manager)
            result = await response_generator.generate_response(request_context, self.memory_service)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in response generation: {e}")
            raise AIException(
                message=f"Response generation failed: {str(e)}",
                error_type=ErrorType.GENERATION_FAILED,
                severity=AISeverity.HIGH
            )
    
    async def _generate_streaming_response(self, request_context: RequestContext) -> AsyncGenerator[str, None]:
        """مرحله ۵: تولید streaming response"""
        try:
            from .langchain_orchestrator import ResponseGenerator
            
            # Select model based on request context
            model_name = self.model_factory.get_optimal_model(
                "rag" if request_context.context else "chat",
                context_length=len(request_context.context) if request_context.context else 0
            )
            
            # Create model instance with streaming enabled
            model = self.model_factory.get_model(
                model_name,
                temperature=request_context.custom_temperature or 0.3,
                max_tokens=request_context.max_tokens,
                streaming=True
            )
            
            # Generate streaming response
            response_generator = ResponseGenerator(self.model_factory, self.security_manager)
            async for chunk in response_generator._generate_streaming_response(
                model,
                request_context,
                self.memory_service
            ):
                # Sanitize each chunk before yielding
                sanitized_chunk = self.security_manager.sanitize_output(chunk)
                if sanitized_chunk:  # Only yield non-empty chunks
                    yield sanitized_chunk
                
        except Exception as e:
            logger.error(f"❌ Error in streaming response generation: {e}")
            yield "متأسفانه در تولید پاسخ خطا رخ داد."
    
    def _get_circuit_breaker_states(self) -> Dict[str, str]:
        """دریافت وضعیت circuit breakers"""
        return {
            "weaviate": self.weaviate_manager.get_stats().get("circuit_breaker_state", "unknown"),
            "mongodb": self.mongodb_manager.get_stats().get("circuit_breaker_state", "unknown")
        }
    
    async def process_simple_chat(self, query: str, **kwargs) -> ProcessingResult:
        """متد کمکی برای chat ساده"""
        request = ProcessingRequest(
            query=query,
            request_type=RequestType.CONVERSATIONAL,
            **kwargs
        )
        return await self.process_request(request, streaming=False)
    
    async def process_rag_query(self, query: str, **kwargs) -> ProcessingResult:
        """متد کمکی برای RAG query"""
        request = ProcessingRequest(
            query=query,
            request_type=RequestType.RAG,
            **kwargs
        )
        return await self.process_request(request, streaming=False)
    
    async def process_streaming_chat(self, query: str, **kwargs) -> AsyncGenerator[str, None]:
        """متد کمکی برای streaming chat"""
        request = ProcessingRequest(
            query=query,
            request_type=RequestType.CONVERSATIONAL,
            **kwargs
        )
        async for chunk in self.process_request(request, streaming=True):
            yield chunk
    
    def get_health_status(self) -> Dict[str, Any]:
        """دریافت وضعیت سلامت سرویس"""
        return {
            "status": "healthy",
            "components": {
                "security_manager": "active",
                "model_factory": "active",
                "memory_service": "active",
                "weaviate_manager": self.weaviate_manager.get_stats(),
                "mongodb_manager": self.mongodb_manager.get_stats(),
                "cache_manager": "active"
            },
            "circuit_breakers": self._get_circuit_breaker_states(),
            "timestamp": time.time()
        }
    
    def reset_circuit_breakers(self):
        """Reset تمام circuit breakers"""
        self.weaviate_manager.reset_circuit_breaker()
        self.mongodb_manager.reset_circuit_breaker()
        logger.info("🔄 All circuit breakers reset")


# Global instance
ai_orchestrator = AIOrchestratorService()

# Decorator for automatic caching
def auto_cache_result(ttl_seconds: int = 300):
    """Decorator for automatic caching of AI responses"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = ai_orchestrator.cache_manager.get(cache_key)
            if cached_result:
                logger.info(f"✅ Cache hit for {func.__name__}")
                return ProcessingResult(
                    success=True,
                    response=cached_result,
                    cache_hit=True,
                    metadata={"cache_key": cache_key, "cached": True}
                )
            
            # Generate new result
            result = await func(self, *args, **kwargs)
            
            # Cache the result
            if result.success:
                ai_orchestrator.cache_manager.set(cache_key, result.response, ttl_seconds)
                logger.info(f"📝 Cached result for {func.__name__}")
            
            return result
        return wrapper
    return decorator


# Export main service
__all__ = [
    'AIOrchestratorService',
    'ai_orchestrator',
    'ProcessingRequest',
    'ProcessingResult',
    'auto_cache_result'
]