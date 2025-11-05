# langchain_utils.py

"""
LangChain utilities for AI model interactions.
این ماژول یک interface کامل و حرفه‌ای برای استفاده از LangChain فراهم می‌کند.

Features:
- Refactored to use dedicated service classes
- Chains & Runnables برای workflow‌های پیچیده
- Callbacks برای monitoring و logging
- Retry logic با exponential backoff
- Token usage tracking
- Performance monitoring
"""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Union
import asyncio
import re
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.core.config import settings
from app.core.logging_config import get_logger, PerformanceLogger
from app.infrastructure.langchain_callbacks import get_default_callbacks
from app.services.model_service import model_service
from app.services.prompt_service import prompt_service
from app.infrastructure.conversation_memory_service import conversation_memory_service
from app.infrastructure.langchain_orchestrator import orchestrator as langchain_orchestrator

logger = get_logger(__name__)


class MetadataOutput(BaseModel):
    """Output schema for metadata generation."""
    summary: str = Field(description="خلاصه مقاله")
    tags: List[str] = Field(description="لیست تگ‌ها")
    suggested_category: str = Field(description="دسته‌بندی پیشنهادی")
    suggested_visibility: str = Field(description="سطح دسترسی پیشنهادی")

    model_config = {
        "protected_namespaces": ("model_",)
    }


class LangChainService:
    """
    Refactored LangChain Service using dedicated service classes
    
    این کلاس به عنوان یک orchestrator عمل می‌کند و از سرویس‌های تخصصی استفاده می‌کند:
    - ModelService: مدیریت مدل‌ها
    - PromptService: مدیریت پرامپت‌ها
    - ConversationMemoryService: مدیریت حافظه مکالمه
    """

    def __init__(self):
        self._embeddings = None
        self._callbacks = get_default_callbacks()
        self._response_cache = {}
        self._cache_ttl = 300  # 5 minutes
        
        logger.info("🎯 LangChainService initialized (refactored)")

    def get_embeddings(self) -> OpenAIEmbeddings:
        """
        دریافت embedding model
        
        Returns:
            OpenAIEmbeddings instance
        """
        if self._embeddings is None:
            logger.info("🔢 Initializing embeddings model")
            self._embeddings = OpenAIEmbeddings(
                model=settings.embedder_model_loaded,
                openai_api_key=settings.embedder_api_key_loaded or settings.openai_api_key_loaded,
                openai_api_base=settings.embedder_openai_base_url_loaded or settings.openai_base_url_loaded
            )
            logger.info("✅ Embeddings model ready")
        
        return self._embeddings
    
    def _determine_task_complexity(self, query: str, context_length: int, history_length: int) -> str:
        """
        Determine task complexity using LangChain Orchestrator
        
        Args:
            query: User query
            context_length: Length of context
            history_length: Length of conversation history
            
        Returns:
            str: Task complexity (simple, moderate, complex)
        """
        # Use LangChain Orchestrator for query analysis
        analysis = langchain_orchestrator.query_analyzer.analyze_query(query, context_length, history_length)
        complexity = analysis.get("complexity", "simple")
        
        logger.info(f"🎯 Task complexity determined: {complexity} (query: {len(query)}, context: {context_length}, history: {history_length})")
        return complexity
    
    def _get_cache_key(self, query: str, context: str, query_type: str, conversation_history: Optional[List] = None) -> str:
        """Generate cache key for RAG response"""
        import hashlib
        
        # Include conversation history in cache key if available
        history_str = ""
        if conversation_history:
            history_str = "_".join([f"{msg.get('role', '')}:{msg.get('content', '')[:50]}" for msg in conversation_history[-5:]])
        
        content = f"{query}_{context}_{query_type}_{history_str}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: dict) -> bool:
        """Check if cache entry is still valid"""
        import time
        return (time.time() - cache_entry["timestamp"]) < self._cache_ttl
    
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get cached response if valid"""
        cache_entry = self._response_cache.get(cache_key)
        if cache_entry and self._is_cache_valid(cache_entry):
            logger.info(f"✅ Using cached response for key: {cache_key[:8]}...")
            return cache_entry["response"]
        return None
    
    def _cache_response(self, cache_key: str, response: str):
        """Cache response"""
        import time
        self._response_cache[cache_key] = {
            "response": response,
            "timestamp": time.time()
        }
        logger.debug(f"📝 Cached response for key: {cache_key[:8]}...")
    
    def _select_model_by_strategy(self, query_type: str, task_complexity: str, streaming: bool = False) -> str:
        """
        Select model based on query type and task complexity using ModelFactory
        
        Args:
            query_type: Type of query (specific, general, explanation)
            task_complexity: Task complexity (simple, moderate, complex)
            streaming: Whether streaming is enabled
            
        Returns:
            str: Model name
        """
        # Use ModelFactory for optimal model selection
        try:
            # Map task complexity to task type
            task_mapping = {
                "simple": "chat",
                "moderate": "rag",
                "complex": "rag"
            }
            
            task_type = task_mapping.get(task_complexity, "rag")
            
            # Get optimal model from ModelFactory
            optimal_model = model_factory.get_optimal_model(task_type)
            logger.info(f"🎯 ModelFactory selected optimal model: {optimal_model} for task: {task_type}")
            
            return optimal_model
            
        except Exception as e:
            logger.warning(f"⚠️ ModelFactory selection failed, using fallback: {e}")
            # Fallback to simple strategy
            if task_complexity == "simple":
                return settings.chat_model_loaded
            else:
                return settings.rag_model_loaded
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    async def _call_with_retry(self, chain, inputs: Dict[str, Any]) -> Any:
        """
        فراخوانی chain با retry logic
        
        Args:
            chain: LangChain chain
            inputs: ورودی‌ها
            
        Returns:
            خروجی chain
        """
        try:
            return await chain.ainvoke(inputs)
        except Exception as e:
            logger.warning(
                f"⚠️ Chain call failed, retrying...",
                extra={'extra_data': {'error': str(e)}}
            )
            raise

    async def generate_metadata(self, title: str, content: str) -> Dict[str, Any]:
        """
        Generate metadata for an article using AI.

        Args:
            title: Article title
            content: Article content

        Returns:
            Dict containing summary, tags, category, and visibility
        """
        with PerformanceLogger(logger, "generate_metadata", title=title[:50], content_length=len(content)):
            try:
                selected_model = settings.metadata_model_loaded
                logger.info(
                    f"🔍 Generating metadata",
                    extra={
                        'extra_data': {
                            'model': selected_model,
                            'title': title[:100],
                            'content_length': len(content)
                        }
                    }
                )

                # Get model from ModelService
                model = model_service.get_model(
                    selected_model, 
                    force_json=True, 
                    max_tokens=1000
                )
                logger.info(f"✅ Model loaded successfully: {selected_model}")

                # Get prompt from PromptService
                prompt_template = prompt_service.get_prompt("metadata_generation")
                prompt = ChatPromptTemplate.from_template(prompt_template)

                # Create the chain with JSON parser
                parser = JsonOutputParser()
                chain = prompt | model | parser

                # Run the chain با retry
                result = await self._call_with_retry(chain, {
                    "title": title,
                    "content": content
                })

                # Validate result structure manually
                if not isinstance(result, dict):
                    raise ValueError("AI response is not a valid dictionary")

                required_keys = ['summary', 'tags', 'suggested_category', 'suggested_visibility']
                for key in required_keys:
                    if key not in result:
                        raise ValueError(f"Missing required key: {key}")

                # Ensure tags is a list
                if not isinstance(result['tags'], list):
                    result['tags'] = [str(result['tags'])]

                logger.info(
                    f"✨ Metadata generated successfully",
                    extra={
                        'extra_data': {
                            'summary_length': len(result.get('summary', '')),
                            'tags_count': len(result.get('tags', [])),
                            'category': result.get('suggested_category'),
                            'visibility': result.get('suggested_visibility')
                        }
                    }
                )

                return result

            except Exception as e:
                # Return default metadata if AI fails
                logger.error(
                    f"❌ Metadata generation failed",
                    exc_info=True,
                    extra={
                        'extra_data': {
                            'model': selected_model,
                            'error': str(e)
                        }
                    }
                )
                logger.warning("⚠️ Using default metadata")
                return {
                    "summary": f"محتوای استخراج شده از فایل: {title}",
                    "tags": [],
                    "suggested_category": "",
                    "suggested_visibility": ""
                }

    async def convert_text_to_markdown(self, title: str, content: str) -> str:
        """
        Convert plain text to structured Markdown using AI.

        Args:
            title: Article title
            content: Plain text content

        Returns:
            Formatted Markdown content
        """
        try:
            selected_model = settings.rag_model_loaded
            logger.info(f"🔄 تبدیل متن به Markdown با مدل: {selected_model}")
            logger.info(f"📝 عنوان: {title[:100]}...")
            logger.info(f"📊 طول محتوا: {len(content)} کاراکتر")

            # Get model from ModelService
            model = model_service.get_model(
                selected_model, 
                force_json=False, 
                max_tokens=4096
            )
            logger.info(f"✅ مدل {selected_model} برای تبدیل Markdown بارگذاری شد (max_tokens: 4096)")

            # Get prompt from PromptService
            prompt_template = prompt_service.get_prompt("markdown_conversion")
            prompt = ChatPromptTemplate.from_template(prompt_template)

            # Create the chain
            chain = prompt | model

            # Run the chain
            result = await chain.ainvoke({
                "title": title,
                "content": content
            })

            markdown_content = result.content.strip()
            logger.info(f"✅ متن با موفقیت به Markdown تبدیل شد - طول: {len(markdown_content)} کاراکتر")
            
            return markdown_content

        except Exception as e:
            logger.error(f"❌ خطا در تبدیل متن به Markdown: {str(e)}")
            # Return original content with basic title formatting if AI conversion fails
            return f"# {title}\n\n{content}"

    async def generate_chat_response(self, messages: List[Dict[str, str]], context: Optional[str] = None) -> str:
        """
        Generate a chat response using AI.

        Args:
            messages: List of chat messages
            context: Optional context from RAG

        Returns:
            AI response string
        """
        try:
            model = model_service.get_model(settings.chat_model_loaded, force_json=False)
            logger.info(f"🗣️ LangChain - Using CHAT model: {settings.chat_model_loaded}")

            # Get system message from PromptService
            system_message = prompt_service.get_prompt("chat_system_message")

            if context:
                system_message += f"\n\n**منابع مرتبط:**\n{context}"

            # Convert messages to LangChain format
            langchain_messages = [
                {"role": "system", "content": system_message}
            ]

            for msg in messages:
                langchain_messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

            # Create chain for chat
            prompt = ChatPromptTemplate.from_messages(langchain_messages)
            chain = prompt | model

            # Get response
            result = await chain.ainvoke({})
            return result.content

        except Exception as e:
            return "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم. لطفاً بعداً دوباره امتحان کنید."
    
    async def generate_chat_response_stream(self, messages: List[Dict[str, str]], context: Optional[str] = None):
        """
        Generate a streaming chat response using AI.
        
        Args:
            messages: List of chat messages
            context: Optional context from RAG
            
        Yields:
            Chunks of the AI response as they are generated
        """
        try:
            # Get model from ModelService with streaming enabled
            model = model_service.get_model(
                settings.chat_model_loaded,
                force_json=False,
                streaming=True
            )
            logger.info(f"📝 LangChain - Using CHAT model for metadata: {settings.chat_model_loaded}")
            
            # Get system message from PromptService
            system_message = prompt_service.get_prompt("chat_system_message")
            
            if context:
                system_message += f"\n\n**منابع مرتبط:**\n{context}"
            
            # Convert messages to LangChain format
            langchain_messages = [
                {"role": "system", "content": system_message}
            ]
            
            for msg in messages:
                langchain_messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
            
            # Create chain for chat
            prompt = ChatPromptTemplate.from_messages(langchain_messages)
            chain = prompt | model
            
            # Stream response
            async for chunk in chain.astream({}):
                if hasattr(chunk, 'content'):
                    yield chunk.content
                else:
                    yield str(chunk)
                    
        except Exception as e:
            logger.error(f"❌ Streaming chat response failed: {e}", exc_info=True)
            yield "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم."


    async def generate_rag_response(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        custom_model: Optional[str] = None,
        custom_temperature: Optional[float] = None,
        query_type: str = "general",  # 🎯 نوع سوال: specific, general, explanation
        prompt_name: str = "rag_response",  # 🆕 پارامتر جدید برای نام پرامپت
        agentic_mode: bool = False  # 🆕 پارامتر جدید برای حالت Agentic
    ) -> str:
        """
        Generate a RAG response using AI - uses provided context and conversation history.

        Args:
            query: User query
            context: Retrieved context from vector database
            conversation_history: Previous messages in the conversation
            custom_model: Optional custom model name (overrides default)
            custom_temperature: Optional custom temperature (overrides default)

        Returns:
            AI response string
        """
        try:
            # Determine task complexity
            task_complexity = self._determine_task_complexity(
                query,
                len(context),
                len(conversation_history) if conversation_history else 0
            )
            
            # Check cache first
            cache_key = self._get_cache_key(query, context, query_type, conversation_history)
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                return cached_response
            
            # Select model based on strategy if custom_model is not provided
            if custom_model is None:
                model_name = self._select_model_by_strategy(query_type, task_complexity, streaming=False)
            else:
                model_name = custom_model
                
            temperature = custom_temperature if custom_temperature is not None else 0.3
            logger.info(f"🔄 LangChain - Using RAG model: {model_name} (complexity: {task_complexity})")
            
            # 🎯 تطبیق max_tokens با نوع سوال و حالت Agentic
            if agentic_mode:
                # در حالت Agentic، اجازه پاسخ‌های کامل‌تر و طولانی‌تر را می‌دهیم
                max_tokens = 4000
                logger.info(f"🧠 Agentic Mode enabled: Using extended max_tokens={max_tokens}")
            else:
                # حالت عادی: پاسخ‌های کوتاه‌تر برای سرعت و مختصر بودن
                if query_type == "specific":
                    max_tokens = 2000  # سوالات خاص: پاسخ متعادل (کاهش از 4000 به 2000)
                elif query_type == "explanation":
                    max_tokens = 2500  # توضیحات: پاسخ کامل اما کوتاه‌تر (کاهش از 4000 به 2500)
                else:  # general
                    max_tokens = 3000  # سوالات عمومی: پاسخ جامع اما نه خیلی طولانی (کاهش از 8000 به 3000)
            
            logger.info(f"🎯 Max Tokens for query type '{query_type}': {max_tokens}")
            
            # Get model from ModelService
            model = model_service.get_model(
                model_name, 
                force_json=False,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            logger.info(f"🤖 Using model: {model_name} with temperature: {temperature}, max_tokens: {max_tokens}")

            # 🔥 DEBUG: Log context preview
            logger.info(f"📝 Context preview (first 500 chars): {context[:500]}...")
            logger.info(f"📝 Context length: {len(context)} characters")
            logger.info(f"❓ Query: {query}")
            logger.info(f"📚 Conversation history: {len(conversation_history) if conversation_history else 0} messages")

            # Build conversation history text using ConversationMemoryService
            history_text = conversation_memory_service.format_history_for_prompt(conversation_history)

            # 🎯 تطبیق سبک پاسخ با نوع سوال - استفاده از prompt files
            logger.info(f"🎯 Query Type: {query_type}")
            if query_type == "specific":
                response_guide = prompt_service.get_prompt("response_guides/specific_response_guide")
            elif query_type == "explanation":
                response_guide = prompt_service.get_prompt("response_guides/explanation_response_guide")
            else:  # general
                response_guide = prompt_service.get_prompt("response_guides/general_response_guide")

            # Get prompt from PromptService
            prompt_template = prompt_service.get_prompt(prompt_name)
            prompt = ChatPromptTemplate.from_template(prompt_template)

            chain = prompt | model

            result = await chain.ainvoke({
                "response_guide": response_guide,
                "history": history_text,
                "context": context,
                "query": query
            })

            # 🧹 حذف بلوک thinking از پاسخ نهایی (اگر مدل آن را تولید کرده باشد)
            response = result.content
            # حذف هر چیزی بین <thinking> و </thinking> (با پشتیبانی از multiline)
            response = re.sub(r'<thinking>.*?</thinking>', '', response, flags=re.DOTALL)
            response = response.strip()

            # Cache the response
            self._cache_response(cache_key, response)

            logger.info(f"✅ RAG response generated: {len(response)} characters")
            return response

        except Exception as e:
            logger.error(f"❌ RAG response generation failed: {e}", exc_info=True)
            return "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم. لطفاً بعداً دوباره امتحان کنید."
    
    async def generate_conversational_response_stream(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        custom_model: Optional[str] = None,
        custom_temperature: Optional[float] = None
    ):
        """
        Generate a conversational (non-RAG) streaming response using AI.
        
        این متد برای پاسخ‌های محاوره‌ای ساده است که نیازی به RAG ندارند:
        - سلام و احوال‌پرسی
        - تشکر
        - معرفی اسم
        - گفتگوی عمومی
        
        Args:
            query: User query
            conversation_history: Previous messages in the conversation
            custom_model: Optional custom model name (overrides default)
            custom_temperature: Optional custom temperature (overrides default - default: 0.7)
            
        Yields:
            Chunks of the AI response as they are generated
        """
        try:
            model_name = custom_model or settings.chat_model_loaded
            temperature = custom_temperature if custom_temperature is not None else 0.7  # دمای بالاتر برای طبیعی‌تر بودن
            logger.info(f"💬 LangChain - Using CHAT model for conversational: {model_name}")
            
            logger.info(f"💬 Conversational streaming with model: {model_name}, temperature: {temperature}")
            
            # Get model from ModelService with streaming enabled
            model = model_service.get_model(
                model_name, 
                force_json=False,
                streaming=True,
                temperature=temperature,
                max_tokens=500  # پاسخ‌های محاوره‌ای کوتاه‌تر هستند
            )
            
            # Get prompt from PromptService
            conversational_prompt_template = prompt_service.get_prompt("conversational_response")
            
            # 🧠 آماده‌سازی تاریخچه مکالمه با ConversationMemoryService
            history_text = conversation_memory_service.format_history_for_prompt(conversation_history)
            
            # ساخت prompt template با placeholders
            prompt = ChatPromptTemplate.from_template(conversational_prompt_template)
            
            chain = prompt | model
            
            # Stream response
            chunk_num = 0
            empty_chunk_count = 0
            first_content_found = False
            
            async for chunk in chain.astream({
                "history": history_text,
                "query": query
            }):
                chunk_num += 1
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)

                # فیلتر کردن chunkهای خالی (فقط تا اولین محتوای معنادار)
                if not first_content_found:
                    if not content or not isinstance(content, str) or len(content.strip()) == 0:
                        empty_chunk_count += 1
                        if empty_chunk_count == 1:
                            logger.info(f"⏭️ Skipping initial empty chunks...")
                        continue
                    else:
                        first_content_found = True
                        if empty_chunk_count > 0:
                            logger.info(f"✅ Skipped {empty_chunk_count} empty chunks, starting content stream...")

                # بعد از پیدا شدن اولین محتوا، همه chunks را ارسال می‌کنیم
                if not isinstance(content, str):
                    content = str(content)
                
                if content:
                    yield content
                    if len(content) > 5:
                        await asyncio.sleep(0.01)
            
            logger.info(f"✅ Conversational streaming completed: {chunk_num} total chunks")
                    
        except Exception as e:
            logger.error(f"❌ Conversational streaming failed: {e}", exc_info=True)
            yield "متأسفانه در حال حاضر نمی‌توانم به پیام شما پاسخ دهم."
    
    async def generate_rag_response_stream(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        custom_model: Optional[str] = None,
        custom_temperature: Optional[float] = None,
        query_type: str = "general",  # 🎯 نوع سوال: specific, general, explanation
        prompt_name: str = "rag_response",  # 🆕 پارامتر جدید برای نام پرامپت
        agentic_mode: bool = False  # 🆕 پارامتر جدید برای حالت Agentic
    ):
        """
        Generate a streaming RAG response using AI - STRICT MODE: Only use provided context.
        
        Args:
            query: User query
            context: Retrieved context from vector database
            conversation_history: Previous messages in the conversation
            custom_model: Optional custom model name (overrides default)
            custom_temperature: Optional custom temperature (overrides default)
            
        Yields:
            Chunks of the AI response as they are generated
        """
        try:
            # Determine task complexity
            task_complexity = self._determine_task_complexity(
                query,
                len(context),
                len(conversation_history) if conversation_history else 0
            )
            
            # Check cache first (for streaming, we'll use a different approach)
            cache_key = self._get_cache_key(query, context, query_type, conversation_history)
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                # Yield cached response as chunks
                for i in range(0, len(cached_response), 10):
                    yield cached_response[i:i+10]
                return
            
            # Select model based on strategy if custom_model is not provided
            if custom_model is None:
                model_name = self._select_model_by_strategy(query_type, task_complexity, streaming=True)
            else:
                model_name = custom_model
                
            temperature = custom_temperature if custom_temperature is not None else 0.3
            logger.info(f"🎯 LangChain - Using RAG model for response: {model_name} (complexity: {task_complexity})")
            
            logger.info(f"🌊 Streaming with model: {model_name}, temperature: {temperature}")
            
            # 🎯 تطبیق max_tokens با نوع سوال و حالت Agentic
            if agentic_mode:
                # در حالت Agentic، اجازه پاسخ‌های کامل‌تر و طولانی‌تر را می‌دهیم
                max_tokens = 4000
                logger.info(f"🧠 Agentic Mode enabled: Using extended max_tokens={max_tokens}")
            else:
                # حالت عادی: پاسخ‌های کوتاه‌تر برای سرعت و مختصر بودن
                if query_type == "specific":
                    max_tokens = 2000  # سوالات خاص: پاسخ متعادل (کاهش از 4000 به 2000)
                elif query_type == "explanation":
                    max_tokens = 2500  # توضیحات: پاسخ کامل اما کوتاه‌تر (کاهش از 4000 به 2500)
                else:  # general
                    max_tokens = 3000  # سوالات عمومی: پاسخ جامع اما نه خیلی طولانی (کاهش از 8000 به 3000)
            
            logger.info(f"🎯 Max Tokens for query type '{query_type}': {max_tokens}")
            
            # Get model from ModelService with streaming enabled
            model = model_service.get_model(
                model_name, 
                force_json=False,
                streaming=True,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 🔥 DEBUG: Log context preview
            logger.debug(f"📝 Context preview (first 500 chars): {context[:500]}...")
            logger.debug(f"📝 Context length: {len(context)} characters")
            logger.debug(f"❓ Query: {query}")
            
            # 🎯 تطبیق سبک پاسخ با نوع سوال - استفاده از prompt files
            logger.debug(f"🎯 Query Type: {query_type}")
            if query_type == "specific":
                response_guide = prompt_service.get_prompt("response_guides/specific_response_guide")
            elif query_type == "explanation":
                response_guide = prompt_service.get_prompt("response_guides/explanation_response_guide")
            else:  # general
                response_guide = prompt_service.get_prompt("response_guides/general_response_guide")
            
            # Get prompt from PromptService
            prompt_template = prompt_service.get_prompt(prompt_name)
            prompt = ChatPromptTemplate.from_template(prompt_template)

            # 🧠 Build conversation history با استفاده از ConversationMemoryService
            history_text = conversation_memory_service.format_history_for_prompt(conversation_history[-10:] if conversation_history else None)
            
            chain = prompt | model
            
            # Stream response با فیلتر هوشمند
            chunk_num = 0
            empty_chunk_count = 0
            first_content_found = False
            
            # 🧠 State machine برای فیلتر کردن بلوک thinking
            inside_thinking = False
            thinking_buffer = ""  # بافر برای ذخیره محتوای احتمالی thinking
            
            async for chunk in chain.astream({
                "response_guide": response_guide,
                "context": context,
                "history": history_text,
                "query": query
            }):
                chunk_num += 1
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)

                # 🔧 فیلتر کردن chunkهای خالی (فقط تا اولین محتوای معنادار)
                if not first_content_found:
                    if not content or not isinstance(content, str) or len(content.strip()) == 0:
                        empty_chunk_count += 1
                        # Skip empty chunks but log them
                        if empty_chunk_count == 1:
                            logger.debug(f"⏭️ Skipping initial empty chunks...")
                            # هشدار برای chunk های خالی زیاد (احتمال مشکل مدل)
                            if empty_chunk_count % 100 == 0:
                                logger.debug(f"⚠️ Still getting empty chunks: {empty_chunk_count} so far (chunk #{chunk_num})")
                        continue
                    else:
                        # اولین محتوای معنادار پیدا شد
                        first_content_found = True
                        if empty_chunk_count > 0:
                            logger.debug(f"✅ Skipped {empty_chunk_count} empty chunks, starting content stream...")

                # بعد از پیدا شدن اولین محتوا، همه chunks را ارسال می‌کنیم (حتی فاصله‌ها)
                if not isinstance(content, str):
                    content = str(content)
                
                # 🧹 فیلتر بلوک thinking در streaming mode
                if content:
                    # اضافه کردن به بافر برای بررسی thinking tags
                    thinking_buffer += content
                    
                    # بررسی شروع thinking block
                    if '<thinking>' in thinking_buffer and not inside_thinking:
                        inside_thinking = True
                        # ارسال محتوای قبل از thinking
                        before_thinking = thinking_buffer.split('<thinking>')[0]
                        if before_thinking:
                            yield before_thinking
                        thinking_buffer = thinking_buffer.split('<thinking>', 1)[1] if '<thinking>' in thinking_buffer else ""
                        logger.debug(f"🧠 Detected <thinking> block start, filtering...")
                        continue
                    
                    # اگر داخل thinking هستیم، بررسی پایان آن
                    if inside_thinking:
                        if '</thinking>' in thinking_buffer:
                            inside_thinking = False
                            # ارسال محتوای بعد از thinking
                            after_thinking = thinking_buffer.split('</thinking>', 1)[1] if '</thinking>' in thinking_buffer else ""
                            thinking_buffer = after_thinking
                            logger.debug(f"🧠 Detected </thinking> block end, resuming stream...")
                            if after_thinking:
                                yield after_thinking
                                thinking_buffer = ""
                        # همچنان در thinking هستیم، skip کن
                        continue
                    
                    # اگر بافر خیلی بزرگ شد و thinking پیدا نشد، محتوای آن را ارسال کن
                    if len(thinking_buffer) > 100 and not inside_thinking:
                        yield thinking_buffer
                        thinking_buffer = ""
                    elif not inside_thinking and len(thinking_buffer) < 50:
                        # اگر بافر کوچک است، منتظر بمان تا thinking کامل شود یا نشود
                        continue
                    
                    # تاخیر خیلی کم برای streaming سریع‌تر
                    if len(content) > 5:
                        await asyncio.sleep(0.01)
            
            # 🧹 ارسال محتوای باقی‌مانده در بافر (اگر thinking پیدا نشد)
            if thinking_buffer and not inside_thinking:
                yield thinking_buffer
                logger.debug(f"✅ Flushed remaining buffer: {len(thinking_buffer)} characters")
                    
            logger.debug(f"✅ Streaming completed: {chunk_num} total chunks, {empty_chunk_count} empty chunks skipped")
            
            # 🔥 اگر همه chunks خالی بودن، یعنی مدل مشکل داره
            if chunk_num > 0 and empty_chunk_count == chunk_num:
                error_msg = f"⚠️ مدل '{custom_model or settings.rag_model_loaded}' پاسخ معتبری برنگرداند. لطفاً مدل دیگری انتخاب کنید (مثل gpt-4o-mini یا google/gemini-2.0-flash-exp:free)."
                logger.debug(error_msg)
                yield error_msg
            
            # Cache the complete response
            # Rebuild the complete response from chunks for caching
            complete_response = ""
            for chunk in chain.astream({
                "response_guide": response_guide,
                "context": context,
                "history": history_text,
                "query": query
            }):
                if hasattr(chunk, 'content'):
                    complete_response += chunk.content
                else:
                    complete_response += str(chunk)
            
            # Clean the response and cache it
            complete_response = re.sub(r'<thinking>.*?</thinking>', '', complete_response, flags=re.DOTALL)
            complete_response = complete_response.strip()
            self._cache_response(cache_key, complete_response)
                    
        except Exception as e:
            logger.debug(f"❌ Streaming RAG response failed: {e}", exc_info=True)
            yield "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم."


# Global instance
langchain_service = LangChainService()