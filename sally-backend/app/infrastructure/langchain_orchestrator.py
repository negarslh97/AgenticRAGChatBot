#langchain_orchestrator.py

"""
Advanced LangChain orchestrator with modern architecture patterns.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import time
import re
from functools import wraps

from .ai_exceptions import AIException, ErrorType, AISeverity
from .circuit_breaker import CircuitBreaker, circuit_breaker_protect
from .cache_manager import CacheManager, cache_result, CacheConfig
from .security_utils import SecurityManager, SecurityConfig, SecurityLevel
from .model_factory import ModelFactory, ModelConfig, ModelProvider, ModelType
from .model_factory import model_factory as global_model_factory
from .conversation_memory_service import ConversationMemoryService
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Types of user queries."""
    SPECIFIC = "specific"
    GENERAL = "general"
    EXPLANATION = "explanation"
    CONVERSATIONAL = "conversational"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    CODING = "coding"


class ResponseStyle(str, Enum):
    """Response styles for different query types."""
    CONCISE = "concise"
    DETAILED = "detailed"
    TECHNICAL = "technical"
    SIMPLE = "simple"
    EDUCATIONAL = "educational"
    PROFESSIONAL = "professional"


@dataclass
class RequestContext:
    """Context for request processing."""
    query: str
    context: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None
    query_type: QueryType = QueryType.GENERAL
    response_style: ResponseStyle = ResponseStyle.DETAILED
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    custom_model: Optional[str] = None
    custom_temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    streaming: bool = False
    agentic_mode: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Validate query
        if not self.query or not self.query.strip():
            raise ValueError("Query cannot be empty")
        
        # Set default max tokens based on query type
        if self.max_tokens is None:
            self.max_tokens = self._get_default_max_tokens()
    
    def _get_default_max_tokens(self) -> int:
        """Get default max tokens based on query type."""
        token_limits = {
            QueryType.SPECIFIC: 2000,
            QueryType.GENERAL: 3000,
            QueryType.EXPLANATION: 4000,
            QueryType.CONVERSATIONAL: 1000,
            QueryType.CREATIVE: 3500,
            QueryType.ANALYTICAL: 4500,
            QueryType.CODING: 3000
        }
        return token_limits.get(self.query_type, 3000)


@dataclass
class ResponseResult:
    """Result of response generation."""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    tokens_used: Optional[int] = None
    model_used: Optional[str] = None
    cache_hit: bool = False
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "metadata": self.metadata,
            "processing_time": self.processing_time,
            "tokens_used": self.tokens_used,
            "model_used": self.model_used,
            "cache_hit": self.cache_hit,
            "error": self.error
        }


class ResponseGenerator:
    """Handles response generation for different query types."""

# در متد __init__ کلاس ResponseGenerator
    def __init__(self, model_factory: ModelFactory, security_manager: SecurityManager):
        self.model_factory = model_factory
        self.security_manager = security_manager
        
        # ایجاد یک شیء CircuitBreakerConfig
        cb_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            name="response_generator"
        )
        
        # پاس دادن شیء پیکربندی به CircuitBreaker
        self._circuit_breaker = CircuitBreaker(cb_config)
    
    @circuit_breaker_protect(failure_threshold=3, recovery_timeout=30)
    async def generate_response(
        self, 
        request_context: RequestContext,
        memory_service: ConversationMemoryService
    ) -> ResponseResult:
        """Generate response based on request context."""
        start_time = time.time()
        
        try:
            # Validate input
            validation_result = self.security_manager.validate_user_input(request_context.query)
            if not validation_result["valid"]:
                raise AIException(
                    message=f"Input validation failed: {validation_result['errors']}",
                    error_type=ErrorType.INVALID_INPUT,
                    severity=AISeverity.MEDIUM
                )
            
            # Select optimal model
            model_name = self._select_model(request_context)
            model = self.model_factory.get_model(
                model_name,
                temperature=request_context.custom_temperature or self._get_temperature(request_context),
                max_tokens=request_context.max_tokens,
                streaming=request_context.streaming
            )
            
            # Generate response
            if request_context.streaming:
                # For streaming, we need to collect the async generator into a string
                # This is used when the caller wants the complete response but with streaming enabled internally
                streaming_generator = self._generate_streaming_response(
                    model, request_context, memory_service
                )
                content = "".join([chunk async for chunk in streaming_generator])
            else:
                content = await self._generate_non_streaming_response(
                    model, request_context, memory_service
                )
            
            # Sanitize output
            sanitized_content = self.security_manager.sanitize_output(content)
            
            # Create result
            processing_time = time.time() - start_time
            result = ResponseResult(
                content=sanitized_content,
                processing_time=processing_time,
                model_used=model_name,
                metadata={
                    "query_type": request_context.query_type.value,
                    "response_style": request_context.response_style.value,
                    "agentic_mode": request_context.agentic_mode
                }
            )
            
            logger.info(f"Response generated successfully in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return ResponseResult(
                content="متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم. لطفاً بعداً دوباره امتحان کنید.",
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    async def _generate_non_streaming_response(
        self, 
        model, 
        request_context: RequestContext,
        memory_service: ConversationMemoryService
    ) -> str:
        """Generate non-streaming response."""
        # Build conversation history
        history_text = memory_service.format_history_for_prompt(request_context.conversation_history)
        
        # Get prompt based on query type
        prompt = self._build_prompt(request_context, history_text)
        
        # Generate response
        result = await model.generate(prompt)
        
        # Clean up thinking blocks
        result = re.sub(r'<thinking>.*?</thinking>', '', result, flags=re.DOTALL)
        return result.strip()
    
    async def _generate_streaming_response(
        self,
        model,
        request_context: RequestContext,
        memory_service: ConversationMemoryService
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response as async generator."""
        # Build conversation history
        history_text = memory_service.format_history_for_prompt(request_context.conversation_history)
        
        # Get prompt based on query type
        prompt = self._build_prompt(request_context, history_text)
        
        # Stream chunks directly as they arrive
        async for chunk in model.generate_stream(prompt):
            # Clean up thinking blocks from each chunk
            clean_chunk = re.sub(r'<thinking>.*?</thinking>', '', chunk, flags=re.DOTALL).strip()
            if clean_chunk:  # Only yield non-empty chunks
                yield clean_chunk
    
    def _select_model(self, request_context: RequestContext) -> str:
        """Select optimal model based on request context."""
        # Use custom model if provided
        if request_context.custom_model:
            logger.info(f"Using custom model: {request_context.custom_model}")
            return request_context.custom_model
        
        # Select model based on query type and complexity
        if request_context.agentic_mode:
            model_name = self.model_factory.get_optimal_model("rag", context_length=4000)
            logger.info(f"Agentic mode - selected model: {model_name}")
            return model_name
        
        model_mapping = {
            QueryType.SPECIFIC: "completion",
            QueryType.GENERAL: "chat",
            QueryType.EXPLANATION: "rag",
            QueryType.CONVERSATIONAL: "chat",
            QueryType.CREATIVE: "chat",
            QueryType.ANALYTICAL: "rag",
            QueryType.CODING: "completion"
        }
        
        task_type = model_mapping.get(request_context.query_type, "chat")
        logger.info(f"Query type: {request_context.query_type}, task_type: {task_type}")
        model_name = self.model_factory.get_optimal_model(task_type)
        logger.info(f"Selected model: {model_name}")
        return model_name
    
    def _get_temperature(self, request_context: RequestContext) -> float:
        """Get temperature based on query type."""
        temperature_mapping = {
            QueryType.SPECIFIC: 0.1,
            QueryType.GENERAL: 0.3,
            QueryType.EXPLANATION: 0.2,
            QueryType.CONVERSATIONAL: 0.7,
            QueryType.CREATIVE: 0.8,
            QueryType.ANALYTICAL: 0.1,
            QueryType.CODING: 0.2
        }
        
        return temperature_mapping.get(request_context.query_type, 0.3)
    
    def _build_prompt(self, request_context: RequestContext, history_text: str) -> str:
        """Build prompt based on request context with enhanced Persian support."""
        
        # Detect if the query is in Persian
        query_lower = request_context.query.lower()
        persian_chars = any('\u0600' <= char <= '\u06FF' for char in request_context.query)
        
        # Base system prompt
        if persian_chars:
            system_prompt = """شما یک دستیار هوش مصنوعی پیشرفته هستید. لطفاً به سوال کاربر به زبان فارسی پاسخ دهید.
            
قوانین پاسخدهی:
1. پاسخ‌ها را به زبان فارسی و با لحن مناسب ارائه دهید
2. از اصطلاحات تخصصی با توضیح کافی استفاده کنید
3. در صورت نیاز به مثال، از مثال‌های مرتبط با فرهنگ ایرانی استفاده کنید
4. پاسخ‌ها را واضح و قابل فهم ارائه دهید
5. اگر سوال تخصصی است، پاسخ را با جزئیات مناسب ارائه دهید

"""
        else:
            system_prompt = """You are an advanced AI assistant. Please respond to the user's query in a professional and helpful manner.
            
Response Guidelines:
1. Provide clear and accurate information
2. Use appropriate technical terms when necessary
3. Include examples when helpful
4. Maintain a professional tone
5. Be comprehensive but concise

"""
        
        # Add query type specific instructions
        query_type_instructions = {
            QueryType.EXPLANATION: "لطفاً پاسخ خود را با توضیحات کامل و مثال‌های مرتبع ارائه دهید." if persian_chars else "Please provide a detailed explanation with relevant examples.",
            QueryType.CODING: "لطفاً کدها را با توضیحات کامل ارائه دهید و بهترین روش‌ها را رعایت کنید." if persian_chars else "Please provide well-commented code following best practices.",
            QueryType.CREATIVE: "لطفاً پاسخ خلاقانه و الهام‌بخش ارائه دهید." if persian_chars else "Please provide a creative and inspiring response.",
            QueryType.ANALYTICAL: "لطفاً تحلیل دقیق و مبتنی بر داده ارائه دهید." if persian_chars else "Please provide a detailed data-driven analysis.",
            QueryType.CONVERSATIONAL: "لطفاً به صورت دوستانه و صمیمی پاسخ دهید." if persian_chars else "Please respond in a friendly and conversational manner.",
            QueryType.SPECIFIC: "لطفاً پاسخ دقیق و مستقیم ارائه دهید." if persian_chars else "Please provide a direct and specific answer.",
            QueryType.GENERAL: "لطفاً پاسخ جامع و مفید ارائه دهید." if persian_chars else "Please provide a comprehensive and helpful response."
        }
        
        # Build the complete prompt
        base_prompt = f"""{system_prompt}
نوع سوال: {request_context.query_type.value}
سبک پاسخ: {request_context.response_style.value}
دستورالعمل: {query_type_instructions.get(request_context.query_type, "")}

سوال کاربر: {request_context.query}
"""
        
        # Add context if available
        if request_context.context:
            base_prompt += f"\n\nبستر اطلاعات: {request_context.context}" if persian_chars else f"\n\nContext: {request_context.context}"
        
        # Add conversation history if available
        if history_text:
            base_prompt += f"\n\nتاریخچه مکالمه: {history_text}" if persian_chars else f"\n\nConversation History: {history_text}"
        
        # Add agentic mode instructions
        if request_context.agentic_mode:
            if persian_chars:
                base_prompt += "\n\nحالت عامل: شما در حالت عامل هستید. لطفاً به صورت گام به گام فکر کرده و پاسخ جامع ارائه دهید."
            else:
                base_prompt += "\n\nAgentic Mode: You are in agentic mode. Feel free to think step by step and provide a comprehensive response."
        
        # Add response style specific instructions
        style_instructions = {
            ResponseStyle.CONCISE: "پاسخ را مختصر و مفید ارائه دهید." if persian_chars else "Provide a concise response.",
            ResponseStyle.DETAILED: "پاسخ را با جزئیات کامل ارائه دهید." if persian_chars else "Provide a detailed response.",
            ResponseStyle.TECHNICAL: "از اصطلاحات فنی دقیق استفاده کنید." if persian_chars else "Use precise technical terminology.",
            ResponseStyle.SIMPLE: "پاسخ را ساده و قابل فهم برای همه ارائه دهید." if persian_chars else "Provide a simple and easy-to-understand response.",
            ResponseStyle.EDUCATIONAL: "پاسخ را آموزشی و با مثال‌های آموزشی ارائه دهید." if persian_chars else "Provide an educational response with examples.",
            ResponseStyle.PROFESSIONAL: "پاسخ را به صورت حرفه‌ای و استاندارد ارائه دهید." if persian_chars else "Provide a professional response."
        }
        
        base_prompt += f"\n\n{style_instructions.get(request_context.response_style, '')}"
        
        return base_prompt


class QueryAnalyzer:
    """Analyzes user queries to determine type and complexity."""
    
    def __init__(self, security_manager: SecurityManager):
        self.security_manager = security_manager
    
    def analyze_query(self, query: str, context_length: int = 0, history_length: int = 0) -> Dict[str, Any]:
        """Analyze query to determine type and complexity."""
        # Validate input
        validation_result = self.security_manager.validate_user_input(query)
        if not validation_result["valid"]:
            raise AIException(
                message=f"Query validation failed: {validation_result['errors']}",
                error_type=ErrorType.INVALID_INPUT,
                severity=AISeverity.MEDIUM
            )
        
        # Determine query type
        query_type = self._determine_query_type(query)
        
        # Determine complexity
        complexity = self._determine_complexity(query, context_length, history_length)
        
        # Determine response style
        response_style = self._determine_response_style(query, query_type)
        
        return {
            "query_type": query_type,
            "complexity": complexity,
            "response_style": response_style,
            "query_length": len(query),
            "context_length": context_length,
            "history_length": history_length,
            "estimated_tokens": self._estimate_tokens(query, context_length)
        }
    
    def _determine_query_type(self, query: str) -> QueryType:
        """Determine the type of query with enhanced Persian support."""
        query_lower = query.lower()
        
        # Persian keywords for different query types
        persian_explanation_keywords = ["توضیح ده", "چگونه", "چه چیزی است", "تعریف کن", "شرح بده",
                                       "چرا", "چطور", "مفهوم", "معنی", "توضیح"]
        persian_coding_keywords = ["کد", "برنامه نویسی", "تابع", "الگوریتم", "کدنویسی",
                                  "پایتون", "جاوا", "سی شارپ", "وب", "اپلیکیشن"]
        persian_creative_keywords = ["خلاقانه", "داستان", "شعر", "نوشتن", "ایده", "خلاقیت",
                                    "نمایش", "تئاتر", "هنر", "ادبیات"]
        persian_analytical_keywords = ["تحلیل", "مقایسه", "ارزیابی", "بررسی", "تحقیق",
                                      "داده", "آمار", "نتیجه گیری", "تحقیق کنید"]
        persian_conversational_keywords = ["سلام", "درود", "خوش آمدید", "مرسی", "خداحافظ",
                                          "چطوره", "حالت چطوره", "چی کار داری"]
        persian_specific_keywords = ["چه کسی", "چه چیزی", "کجا", "چه زمانی", "چرا", "چطور",
                                    "چند", "چقدر", "کدام", "کدامیک"]
        
        # Check for Persian keywords first
        if any(keyword in query_lower for keyword in persian_explanation_keywords):
            return QueryType.EXPLANATION
        
        if any(keyword in query_lower for keyword in persian_coding_keywords):
            return QueryType.CODING
        
        if any(keyword in query_lower for keyword in persian_creative_keywords):
            return QueryType.CREATIVE
        
        if any(keyword in query_lower for keyword in persian_analytical_keywords):
            return QueryType.ANALYTICAL
        
        if any(keyword in query_lower for keyword in persian_conversational_keywords):
            return QueryType.CONVERSATIONAL
        
        # Check for English keywords
        if any(keyword in query_lower for keyword in ["how to", "what is", "explain", "describe"]):
            return QueryType.EXPLANATION
        
        if any(keyword in query_lower for keyword in ["code", "programming", "function", "algorithm"]):
            return QueryType.CODING
        
        if any(keyword in query_lower for keyword in ["creative", "write", "story", "poem"]):
            return QueryType.CREATIVE
        
        if any(keyword in query_lower for keyword in ["analyze", "compare", "evaluate", "assess"]):
            return QueryType.ANALYTICAL
        
        if any(keyword in query_lower for keyword in ["hello", "hi", "hey", "good morning"]):
            return QueryType.CONVERSATIONAL
        
        # Check for specific questions
        if len(query) < 50 and any(keyword in query_lower for keyword in persian_specific_keywords +
                                 ["what", "who", "when", "where", "why"]):
            return QueryType.SPECIFIC
        
        return QueryType.GENERAL
    
    def _determine_complexity(self, query: str, context_length: int, history_length: int) -> str:
        """Determine query complexity."""
        # Simple heuristics for complexity determination
        if len(query) < 50 and context_length < 1000 and history_length == 0:
            return "simple"
        elif len(query) < 100 and context_length < 3000 and history_length < 5:
            return "moderate"
        else:
            return "complex"
    
    def _determine_response_style(self, query: str, query_type: QueryType) -> ResponseStyle:
        """Determine appropriate response style with enhanced Persian support."""
        query_lower = query.lower()
        
        # Check for Persian language indicators
        persian_chars = any('\u0600' <= char <= '\u06FF' for char in query)
        
        if query_type == QueryType.CONVERSATIONAL:
            return ResponseStyle.SIMPLE if persian_chars else ResponseStyle.PROFESSIONAL
        
        if query_type == QueryType.CODING:
            return ResponseStyle.TECHNICAL
        
        if query_type == QueryType.EXPLANATION:
            # For Persian explanations, prefer educational style
            if persian_chars:
                return ResponseStyle.EDUCATIONAL
            return ResponseStyle.DETAILED
        
        if query_type == QueryType.ANALYTICAL:
            return ResponseStyle.DETAILED
        
        # For Persian queries, prefer professional but accessible style
        if persian_chars:
            return ResponseStyle.PROFESSIONAL
        
        return ResponseStyle.PROFESSIONAL
    
    def _estimate_tokens(self, query: str, context_length: int) -> int:
        """Estimate token usage."""
        # Simple estimation (4 chars per token on average)
        query_tokens = len(query) // 4
        context_tokens = context_length // 4
        return query_tokens + context_tokens


class LangChainOrchestrator:
    """Main orchestrator for LangChain operations."""
    
    def __init__(
        self, 
        model_factory: Optional[ModelFactory] = None,
        security_config: Optional[SecurityConfig] = None,
        cache_ttl: int = 300
    ):
        self.model_factory = model_factory or global_model_factory
        self.security_manager = SecurityManager(security_config)
        self.memory_service = ConversationMemoryService()
        self.query_analyzer = QueryAnalyzer(self.security_manager)
        self.response_generator = ResponseGenerator(self.model_factory, self.security_manager)
        
        cache_config = CacheConfig(max_size=1000, ttl=cache_ttl)
        self._cache = CacheManager(cache_config)

        # ایجاد شیء CircuitBreakerConfig برای CircuitBreaker
        cb_config = CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=120,
            name="langchain_orchestrator"
        )
        self._circuit_breaker = CircuitBreaker(cb_config)
        
        logger.info("LangChain Orchestrator initialized with modern architecture")
    
    @cache_result(ttl_seconds=300)
    async def process_request(
        self, 
        query: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> ResponseResult:
        """Process a user request end-to-end."""
        start_time = time.time()
        
        try:
            # Create request context
            request_context = RequestContext(
                query=query,
                context=context,
                conversation_history=conversation_history,
                **kwargs
            )
            
            # Analyze query
            analysis = self.query_analyzer.analyze_query(
                query, 
                len(context) if context else 0, 
                len(conversation_history) if conversation_history else 0
            )
            
            # Update request context with analysis
            request_context.query_type = QueryType(analysis["query_type"])
            request_context.response_style = ResponseStyle(analysis["response_style"])
            
            # Generate response
            result = await self.response_generator.generate_response(
                request_context, 
                self.memory_service
            )
            
            # Update result with analysis
            result.metadata.update(analysis)
            
            logger.info(f"Request processed in {time.time() - start_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Request processing failed: {e}")
            return ResponseResult(
                content="متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم. لطفاً بعداً دوباره امتحان کنید.",
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    async def process_streaming_request(
        self, 
        query: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Process a streaming request."""
        try:
            # Create request context with streaming enabled
            request_context = RequestContext(
                query=query,
                context=context,
                conversation_history=conversation_history,
                streaming=True,
                **kwargs
            )
            
            # Analyze query
            analysis = self.query_analyzer.analyze_query(
                query, 
                len(context) if context else 0, 
                len(conversation_history) if conversation_history else 0
            )
            
            # Update request context with analysis
            request_context.query_type = QueryType(analysis["query_type"])
            request_context.response_style = ResponseStyle(analysis["response_style"])
            
            # Select model
            model_name = self.response_generator._select_model(request_context)
            model = self.model_factory.get_model(
                model_name,
                temperature=request_context.custom_temperature or self.response_generator._get_temperature(request_context),
                max_tokens=request_context.max_tokens,
                streaming=True
            )
            
            # Build prompt
            history_text = self.memory_service.format_history_for_prompt(conversation_history)
            prompt = self.response_generator._build_prompt(request_context, history_text)
            
            # Stream response
            async for chunk in model.generate_stream(prompt):
                sanitized_chunk = self.security_manager.sanitize_output(chunk)
                yield sanitized_chunk
                
        except Exception as e:
            logger.error(f"Streaming request processing failed: {e}")
            yield "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم."
    
    def add_model(self, config: ModelConfig) -> bool:
        """Add a model to the orchestrator."""
        return self.model_factory.add_model(config)
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        return self.model_factory.list_models()
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        return {
            "models_count": len(self.model_factory._models),
            "cache_size": len(self._cache.cache),
            "circuit_breaker_state": self._circuit_breaker.get_state(),
            "security_level": self.security_manager.config.level.value,
            "memory_service_active": True
        }


# Global orchestrator instance
orchestrator = LangChainOrchestrator()