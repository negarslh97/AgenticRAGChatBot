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
import os
import tiktoken
import hashlib
from functools import wraps

from .ai_exceptions import AIException, ErrorType, AISeverity
from .circuit_breaker import CircuitBreaker, circuit_breaker_protect
from .cache_manager import CacheManager, cache_result, CacheConfig, default_cache_manager
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
    custom_prompt: Optional[str] = None  # 🔥 پشتیبانی از پرامپت سفارشی
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

    def __init__(self, model_factory: ModelFactory, security_manager: SecurityManager):
        self.model_factory = model_factory
        self.security_manager = security_manager
        self._prompt_cache: Dict[str, str] = {}  # 🔥 کش پرامپت‌ها

        # ایجاد یک شیء CircuitBreakerConfig
        cb_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            name="response_generator"
        )

        # پاس دادن شیء پیکربندی به CircuitBreaker
        self._circuit_breaker = CircuitBreaker(cb_config)

    def _load_prompt_from_file(self, prompt_name: str) -> Optional[str]:
        """بارگذاری پرامپت از فایل."""
        if prompt_name in self._prompt_cache:
            return self._prompt_cache[prompt_name]

        # مسیر فایل‌های پرامپت
        prompt_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
        prompt_file = os.path.join(prompt_dir, f"{prompt_name}.txt")

        try:
            if os.path.exists(prompt_file):
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    self._prompt_cache[prompt_name] = content
                    logger.debug(f"Loaded prompt: {prompt_name}")
                    return content
            else:
                logger.warning(f"Prompt file not found: {prompt_file}")
                return None
        except Exception as e:
            logger.error(f"Failed to load prompt {prompt_name}: {e}")
            return None

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
        
        # 🎯 Add introduction for first message (if no history exists)
        is_first_message = not request_context.conversation_history or len(request_context.conversation_history) == 0
        if is_first_message:
            logger.info("👋 First message detected (ResponseGenerator non-streaming) - Bot will introduce itself")
            if not history_text or history_text.strip() == "":
                history_text = "[هیچ تاریخچه‌ای وجود ندارد - این اولین پیام است]"

        # Get prompt based on query type
        prompt = self._build_prompt(request_context, history_text)

        # Generate response
        result = await model.generate(prompt)

        # Clean up thinking blocks and leaked system instructions
        result = re.sub(r'<thinking>.*?</thinking>', '', result, flags=re.DOTALL)
        result = re.sub(r'```thinking.*?```', '', result, flags=re.DOTALL)

        # Remove common leaked system instructions and prompts
        result = re.sub(r'^- بررسی.*$', '', result, flags=re.MULTILINE)
        result = re.sub(r'^- .*بررسی.*$', '', result, flags=re.MULTILINE)
        result = re.sub(r'^سلام من سالی.*$', '', result, flags=re.MULTILINE)
        result = re.sub(r'^⚠️.*$', '', result, flags=re.MULTILINE)

        # Remove multiple consecutive empty lines
        result = re.sub(r'\n\s*\n\s*\n+', '\n\n', result)
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
        
        # 🎯 Add introduction for first message (if no history exists)
        is_first_message = not request_context.conversation_history or len(request_context.conversation_history) == 0
        if is_first_message:
            logger.info("👋 First message detected (ResponseGenerator streaming) - Bot will introduce itself")
            if not history_text or history_text.strip() == "":
                history_text = "[هیچ تاریخچه‌ای وجود ندارد - این اولین پیام است]"

        # Get prompt based on query type
        prompt = self._build_prompt(request_context, history_text)

        # Stream chunks directly as they arrive
        async for chunk in model.generate_stream(prompt):
            # Clean up thinking blocks and leaked system instructions from each chunk
            clean_chunk = re.sub(r'<thinking>.*?</thinking>', '', chunk, flags=re.DOTALL)
            clean_chunk = re.sub(r'```thinking.*?```', '', clean_chunk, flags=re.DOTALL)

            # Remove common leaked system instructions and prompts from chunks
            clean_chunk = re.sub(r'^- بررسی.*$', '', clean_chunk, flags=re.MULTILINE)
            clean_chunk = re.sub(r'^- .*بررسی.*$', '', clean_chunk, flags=re.MULTILINE)
            clean_chunk = re.sub(r'^سلام من سالی.*$', '', clean_chunk, flags=re.MULTILINE)
            clean_chunk = re.sub(r'^⚠️.*$', '', clean_chunk, flags=re.MULTILINE)

            # ❌ REMOVED: clean_chunk = clean_chunk.strip() - This was removing essential spaces from LLM tokens!
            # LLM streaming tokens already include proper spacing (e.g., " world" starts with space)

            if clean_chunk:  # Only yield non-empty chunks
                yield clean_chunk

    def _select_model(self, request_context: RequestContext) -> str:
        """Select optimal model based on request context."""
        
        # 1. Check if user requested a specific model (Priority 1)
        # 👈 این بخش به ابتدای تابع منتقل شد تا هیچ مدلی پیش از آن انتخاب نشود
        if request_context.custom_model:
            # Validate model existence
            if request_context.custom_model in self.model_factory._models:
                logger.info(f"Using user-selected model: {request_context.custom_model}")
                return request_context.custom_model  # 👈 بازگشت سریع
            else:
                logger.warning(f"Requested model {request_context.custom_model} not found. Falling back to auto-selection.")

        # Select model based on query type and complexity - optimized caching
        model_cache_key = f"{request_context.query_type.value}_{request_context.agentic_mode}"
        cached_model = getattr(self, f'_cached_model_{model_cache_key}', None)
        
        if cached_model and hasattr(cached_model, '_last_used'):
            # Use cached model if it's still valid (within 5 minutes)
            if time.time() - cached_model['_last_used'] < 300:
                return cached_model['name']
        
        # Select model based on query type and complexity
        if request_context.agentic_mode:
            # 🔥 CHANGE: Using a faster, more reliable model for agentic mode
            model_name = "gpt-4o-mini"
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
        
        # Cache the model selection
        cache_attr = f'_cached_model_{model_cache_key}'
        setattr(self, cache_attr, {'name': model_name, '_last_used': time.time()})
        
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
            # For Persian explanations, prefer the educational style
            if persian_chars:
                return ResponseStyle.EDUCATIONAL
            return ResponseStyle.DETAILED

        if query_type == QueryType.ANALYTICAL:
            return ResponseStyle.DETAILED

        # For Persian queries, prefer a professional but accessible style
        if persian_chars:
            return ResponseStyle.PROFESSIONAL

        return ResponseStyle.PROFESSIONAL

    def _estimate_tokens(self, query: str, context_length: int) -> int:
        """Estimate token usage."""
        # Simple estimation (4 chars per token on average)
        query_tokens = len(query) // 4
        context_tokens = context_length // 4
        return query_tokens + context_tokens


class OptimizedTokenCounter:
    """Optimized token counter with caching and hybrid estimation strategy."""

    def __init__(self, cache_manager: Optional[CacheManager] = None, cache_ttl: int = 3600):
        self.cache_manager = cache_manager or default_cache_manager
        self.cache_ttl = cache_ttl
        self._encoding_cache = {}
        self._performance_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "estimation_used": 0,
            "accurate_counting_used": 0,
            "total_calls": 0,
            "avg_estimation_time": 0.0,
            "avg_accurate_time": 0.0
        }

        # Initialize tiktoken encodings for common models
        self._init_encodings()

    def _init_encodings(self):
        """Initialize tiktoken encodings for common models."""
        try:
            # Common model encodings
            self._encoding_cache["gpt-3.5-turbo"] = tiktoken.encoding_for_model("gpt-3.5-turbo")
            self._encoding_cache["gpt-4"] = tiktoken.encoding_for_model("gpt-4")
            self._encoding_cache["gpt-4o"] = tiktoken.encoding_for_model("gpt-4o")
            self._encoding_cache["gpt-4o-mini"] = tiktoken.encoding_for_model("gpt-4o-mini")
            # Default fallback encoding
            self._encoding_cache["default"] = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning(f"Failed to initialize tiktoken encodings: {e}")
            # Fallback to basic encoding
            try:
                self._encoding_cache["default"] = tiktoken.get_encoding("cl100k_base")
            except:
                self._encoding_cache["default"] = None

    def _generate_cache_key(self, text: str, model: str = "default") -> str:
        """Generate a cache key for the text."""
        # Use SHA-256 hash of text + model for cache key
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
        return f"token_count:{model}:{text_hash}"

    def _estimate_tokens_fast(self, text: str) -> int:
        """Fast estimation based on character count with language-specific ratios."""
        if not text:
            return 0

        # Language-specific estimation ratios (chars per token)
        char_count = len(text)

        # Persian/Arabic text detection
        persian_chars = sum(1 for char in text if '\u0600' <= char <= '\u06FF')
        persian_ratio = persian_chars / char_count if char_count > 0 else 0

        # English text detection
        english_chars = sum(1 for char in text if char.isascii() and char.isalnum())
        english_ratio = english_chars / char_count if char_count > 0 else 0

        # Code detection (common programming patterns)
        code_indicators = ['def ', 'class ', 'import ', 'function', 'const ', 'let ', 'var ']
        is_code = any(indicator in text for indicator in text)

        if is_code:
            # Code typically has more tokens per character
            return max(1, char_count // 3)
        elif persian_ratio > 0.3:
            # Persian text
            return max(1, char_count // 5)
        elif english_ratio > 0.7:
            # English text
            return max(1, char_count // 4)
        else:
            # Mixed content
            return max(1, char_count // 4)

    def _count_tokens_accurate(self, text: str, model: str = "default") -> int:
        """Accurate token counting using tiktoken."""
        try:
            encoding = self._encoding_cache.get(model, self._encoding_cache.get("default"))
            if encoding is None:
                raise ValueError("No encoding available")

            tokens = encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.warning(f"Accurate token counting failed for model {model}: {e}")
            # Fallback to estimation
            return self._estimate_tokens_fast(text)

    def count_tokens(self, text: str, model: str = "default", use_cache: bool = True) -> int:
        """Count tokens using hybrid strategy with caching."""
        start_time = time.time()
        self._performance_stats["total_calls"] += 1

        if not text:
            return 0

        # For very short texts, use estimation directly (no caching needed)
        if len(text) < 50:
            result = self._estimate_tokens_fast(text)
            self._performance_stats["estimation_used"] += 1
            self._performance_stats["avg_estimation_time"] = (
                (self._performance_stats["avg_estimation_time"] * (self._performance_stats["estimation_used"] - 1) +
                 (time.time() - start_time)) / self._performance_stats["estimation_used"]
            )
            return result

        # Try cache first
        if use_cache:
            cache_key = self._generate_cache_key(text, model)
            cached_result = self.cache_manager.get(cache_key)
            if cached_result is not None:
                self._performance_stats["cache_hits"] += 1
                return cached_result
            self._performance_stats["cache_misses"] += 1

        # Determine strategy based on text length
        text_length = len(text)

        if text_length < 1000:
            # Short texts: use accurate counting
            result = self._count_tokens_accurate(text, model)
            self._performance_stats["accurate_counting_used"] += 1
            accurate_time = time.time() - start_time
            self._performance_stats["avg_accurate_time"] = (
                (self._performance_stats["avg_accurate_time"] * (self._performance_stats["accurate_counting_used"] - 1) +
                 accurate_time) / self._performance_stats["accurate_counting_used"]
            )
        elif text_length < 20000:
            # Medium texts: use hybrid approach with optimized sampling
            estimated = self._estimate_tokens_fast(text)
            # Use smaller sample size for faster processing
            sample_size = min(500, text_length // 20)
            if sample_size > 50:
                sample = text[:sample_size]
                try:
                    sample_accurate = self._count_tokens_accurate(sample, model)
                    sample_estimated = self._estimate_tokens_fast(sample)

                    # Adjust estimation based on sample accuracy
                    if sample_estimated > 0:
                        adjustment_ratio = sample_accurate / sample_estimated
                        result = int(estimated * adjustment_ratio)
                    else:
                        result = estimated
                except:
                    result = estimated
            else:
                result = estimated

            self._performance_stats["estimation_used"] += 1
        else:
            # Long texts: use estimation only (fastest)
            result = self._estimate_tokens_fast(text)
            self._performance_stats["estimation_used"] += 1

        # Cache the result with shorter TTL for better performance
        if use_cache:
            cache_key = self._generate_cache_key(text, model)
            self.cache_manager.set(cache_key, result, ttl=self.cache_ttl)

        return result

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = self._performance_stats.copy()
        total_cache_requests = stats["cache_hits"] + stats["cache_misses"]
        stats["cache_hit_rate"] = (
            stats["cache_hits"] / total_cache_requests if total_cache_requests > 0 else 0
        )
        stats["estimation_ratio"] = (
            stats["estimation_used"] / stats["total_calls"] if stats["total_calls"] > 0 else 0
        )
        stats["accurate_ratio"] = (
            stats["accurate_counting_used"] / stats["total_calls"] if stats["total_calls"] > 0 else 0
        )
        return stats

    def clear_cache(self):
        """Clear the token counting cache."""
        # Note: This would require clearing all keys with "token_count:" prefix
        # For now, we'll let the cache manager handle TTL-based cleanup
        logger.info("Token counting cache will be cleared via TTL expiration")


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

        # Initialize optimized token counter
        self._token_counter = OptimizedTokenCounter(self._cache, cache_ttl=cache_ttl)

        # Create a CircuitBreakerConfig object for CircuitBreaker
        cb_config = CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=120,
            name="langchain_orchestrator"
        )
        self._circuit_breaker = CircuitBreaker(cb_config)

        logger.info("LangChain Orchestrator initialized with modern architecture")

    async def process_request(
        self,
        query: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        custom_prompt: Optional[str] = None,  # 🔥 پشتیبانی از پرامپت سفارشی
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
                custom_prompt=custom_prompt,
                **kwargs
            )

            # If custom_prompt is provided, use the direct model approach
            if custom_prompt:
                logger.info(f"Using custom prompt: {custom_prompt}")

                # Load the custom prompt
                custom_prompt_content = self.response_generator._load_prompt_from_file(custom_prompt)
                if not custom_prompt_content:
                    logger.warning(f"Failed to load custom prompt: {custom_prompt}")
                    # Fall back to the default prompt if custom prompt loading fails
                    custom_prompt = None
                else:
                    # Override prompt building with the custom prompt
                    request_context.custom_prompt = custom_prompt
                    return await self._process_with_custom_prompt(request_context, start_time)

            # Standard processing for non-custom prompts
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

    async def _process_with_custom_prompt(self, request_context: RequestContext, start_time: float) -> ResponseResult:
        """Process request using custom prompt file with detailed timing and token logging."""
        custom_prompt_start_time = time.time()

        try:
            # Load the custom prompt
            custom_prompt_name = request_context.custom_prompt
            load_prompt_start = time.time()
            custom_prompt_content = self.response_generator._load_prompt_from_file(custom_prompt_name)
            load_prompt_time = time.time() - load_prompt_start

            if not custom_prompt_content:
                logger.warning(f"Failed to load custom prompt: {custom_prompt_name}, falling back to standard processing")
                # Fallback to standard processing
                return await self.response_generator.generate_response(
                    request_context,
                    self.memory_service
                )

            # Get model
            model_select_start = time.time()
            model_name = self.response_generator._select_model(request_context)
            model = self.model_factory.get_model(
                model_name,
                temperature=request_context.custom_temperature or self.response_generator._get_temperature(request_context),
                max_tokens=request_context.max_tokens,
                streaming=False
            )
            model_select_time = time.time() - model_select_start

            # Build the final prompt with context and history
            prompt_build_start = time.time()
            history_text = self.memory_service.format_history_for_prompt(request_context.conversation_history)
            
            # 🎯 Add introduction for first message (if no history exists)
            is_first_message = not request_context.conversation_history or len(request_context.conversation_history) == 0
            if is_first_message:
                logger.info("👋 First message detected (LangChain Orchestrator) - Bot will introduce itself")
                if not history_text or history_text.strip() == "":
                    history_text = "[هیچ تاریخچه‌ای وجود ندارد - این اولین پیام است]"
            
            final_prompt = custom_prompt_content

            # Replace common placeholders
            if "{query}" in final_prompt:
                final_prompt = final_prompt.replace("{query}", request_context.query)

            if "{context}" in final_prompt and request_context.context:
                final_prompt = final_prompt.replace("{context}", request_context.context)

            if "{history}" in final_prompt:
                # Always replace history, even if empty (for first message detection)
                final_prompt = final_prompt.replace("{history}", history_text or "[هیچ تاریخچه‌ای وجود ندارد]")

            prompt_build_time = time.time() - prompt_build_start

            # Count input tokens - skip timing for performance
            input_tokens = self._count_tokens(final_prompt)

            # Generate response using the model with minimal logging
            model_call_start = time.time()
            logger.info(f"🤖 Starting LLM call to {model_name}")
            logger.info(f"📊 Input tokens: {input_tokens:,}")

            result_content = await model.generate(final_prompt)
            model_call_time = time.time() - model_call_start

            # Count output tokens
            output_tokens = self._count_tokens(result_content)

            # Clean up thinking blocks and leaked system instructions
            result_content = re.sub(r'<thinking>.*?</thinking>', '', result_content, flags=re.DOTALL)
            result_content = re.sub(r'```thinking.*?```', '', result_content, flags=re.DOTALL)

            # Remove common leaked system instructions and prompts
            result_content = re.sub(r'^- بررسی.*$', '', result_content, flags=re.MULTILINE)
            result_content = re.sub(r'^- .*بررسی.*$', '', result_content, flags=re.MULTILINE)
            result_content = re.sub(r'^سلام من سالی.*$', '', result_content, flags=re.MULTILINE)
            result_content = re.sub(r'^⚠️.*$', '', result_content, flags=re.MULTILINE)

            # Remove multiple consecutive empty lines
            result_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', result_content)
            result_content = result_content.strip()

            # Calculate total processing time
            total_processing_time = time.time() - start_time
            custom_prompt_processing_time = time.time() - custom_prompt_start_time

            # Create result with detailed metadata
            result = ResponseResult(
                content=result_content,
                processing_time=total_processing_time,
                tokens_used=input_tokens + output_tokens,
                model_used=model_name,
                metadata={
                    "custom_prompt": custom_prompt_name,
                    "prompt_type": "custom_file",
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "timing_breakdown": {
                        "total_request_time": total_processing_time,
                        "custom_prompt_processing_time": custom_prompt_processing_time,
                        "pre_processing_time": custom_prompt_start_time - start_time,
                        "prompt_load_time": load_prompt_time,
                        "model_selection_time": model_select_time,
                        "prompt_build_time": prompt_build_time,
                        "token_counting_time": time.time() - model_call_start, # Token counting time is now part of model_call_time
                        "model_call_time": model_call_time
                    }
                }
            )

            # Detailed logging
            logger.info(f"✅ Custom prompt request completed successfully")
            logger.info(f"📈 Performance Metrics:")
            logger.info(f"   ⏱️ Total request time: {total_processing_time:.3f}s")
            logger.info(f"   🔄 Custom prompt processing: {custom_prompt_processing_time:.3f}s")
            logger.info(f"   📊 Input tokens: {input_tokens:,}")
            logger.info(f"   📤 Output tokens: {output_tokens:,}")
            logger.info(f"   🔢 Total tokens: {input_tokens + output_tokens:,}")
            logger.info(f"   🤖 Model: {model_name}")
            logger.info(f"   ⚡ Model call time: {model_call_time:.3f}s")
            tokens_per_second = (input_tokens + output_tokens) / model_call_time if model_call_time > 0 else 0
            logger.info(f"   📝 Tokens per second: {tokens_per_second:.1f}")
            logger.info(f"   🎯 Response length: {len(result_content)} characters")

            return result

        except Exception as e:
            error_time = time.time() - start_time
            logger.error(f"❌ Custom prompt processing failed after {error_time:.3f}s: {e}")
            return ResponseResult(
                content="متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم. لطفاً بعداً دوباره امتحان کنید.",
                error=str(e),
                processing_time=error_time
            )

    async def _process_streaming_with_custom_prompt(self, request_context: RequestContext) -> AsyncGenerator[str, None]:
        """Process streaming request using custom prompt file."""
        try:
            # Load the custom prompt
            custom_prompt_name = request_context.custom_prompt
            custom_prompt_content = self.response_generator._load_prompt_from_file(custom_prompt_name)

            if not custom_prompt_content:
                logger.warning(f"Failed to load custom prompt: {custom_prompt_name}, falling back to standard processing")
                # Fallback to standard streaming processing
                async for chunk in self._generate_streaming_response(
                    self.response_generator,
                    request_context,
                    self.memory_service
                ):
                    yield chunk
                return

            # Get model for streaming
            model_name = self.response_generator._select_model(request_context)
            model = self.model_factory.get_model(
                model_name,
                temperature=request_context.custom_temperature or self.response_generator._get_temperature(request_context),
                max_tokens=request_context.max_tokens,
                streaming=True
            )

            # Build the final prompt with context and history
            history_text = self.memory_service.format_history_for_prompt(request_context.conversation_history)

            # 🎯 Add introduction for first message (if no history exists)
            is_first_message = not request_context.conversation_history or len(request_context.conversation_history) == 0
            if is_first_message:
                logger.info("👋 First message detected (Streaming Custom Prompt) - Bot will introduce itself")
                if not history_text or history_text.strip() == "":
                    history_text = "[هیچ تاریخچه‌ای وجود ندارد - این اولین پیام است]"

            final_prompt = custom_prompt_content

            # Replace common placeholders
            if "{query}" in final_prompt:
                final_prompt = final_prompt.replace("{query}", request_context.query)

            if "{context}" in final_prompt and request_context.context:
                final_prompt = final_prompt.replace("{context}", request_context.context)

            if "{history}" in final_prompt:
                # Always replace history, even if empty (for first message detection)
                final_prompt = final_prompt.replace("{history}", history_text or "[هیچ تاریخچه‌ای وجود ندارد]")

            # Log streaming details
            logger.info(f"🤖 Starting streaming LLM call to {model_name} with custom prompt: {custom_prompt_name}")

            # Stream response using the model
            async for chunk in model.generate_stream(final_prompt):
                # Clean up thinking blocks and leaked system instructions from each chunk
                clean_chunk = re.sub(r'<thinking>.*?</thinking>', '', chunk, flags=re.DOTALL)
                clean_chunk = re.sub(r'```thinking.*?```', '', clean_chunk, flags=re.DOTALL)

                # Remove common leaked system instructions and prompts from chunks
                clean_chunk = re.sub(r'^- بررسی.*$', '', clean_chunk, flags=re.MULTILINE)
                clean_chunk = re.sub(r'^- .*بررسی.*$', '', clean_chunk, flags=re.MULTILINE)
                clean_chunk = re.sub(r'^سلام من سالی.*$', '', clean_chunk, flags=re.MULTILINE)
                clean_chunk = re.sub(r'^⚠️.*$', '', clean_chunk, flags=re.MULTILINE)

                # ❌ REMOVED: clean_chunk = clean_chunk.strip() - This was removing essential spaces from LLM tokens!
                # LLM streaming tokens already include proper spacing (e.g., " world" starts with space)

                if clean_chunk:  # Only yield non-empty chunks
                    # 🔥 اصلاح: حذف sanitize_output در استریمینگ برای حفظ فاصله‌ها
                    # امنیت در سمت کلاینت و MarkdownRenderer تامین می‌شود
                    yield clean_chunk

        except Exception as e:
            logger.error(f"❌ Custom prompt streaming failed: {e}")
            yield "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم."

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using optimized hybrid strategy with caching."""
        return self._token_counter.count_tokens(text)

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

            # If custom_prompt is provided, use the direct streaming approach
            if request_context.custom_prompt:
                logger.info(f"Using custom prompt for streaming: {request_context.custom_prompt}")
                async for chunk in self._process_streaming_with_custom_prompt(request_context):
                    yield chunk
                return

            # Standard processing for non-custom prompts
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
                # 🔥 اصلاح: حذف sanitize_output چون فاصله‌های ابتدای چانک را می‌خورد
                yield chunk

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
            "memory_service_active": True,
            "token_counter_stats": self._token_counter.get_performance_stats()
        }


# Global orchestrator instance
orchestrator = LangChainOrchestrator()
