"""
LangChain utilities for AI model interactions.
این ماژول یک interface کامل و حرفه‌ای برای استفاده از LangChain فراهم می‌کند.

Features:
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
from enum import Enum
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.core.config import settings
from app.core.logging_config import get_logger, PerformanceLogger
from app.infrastructure.langchain_callbacks import get_default_callbacks

logger = get_logger(__name__)


class ModelProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"          # OpenAI رسمی (gpt-4o, gpt-3.5-turbo, ...)
    OPENROUTER = "openrouter"  # OpenRouter (Grok, Gemini, Claude, Llama, Mistral, ...)
    OLLAMA = "ollama"          # Ollama محلی


def detect_model_provider(model_name: str) -> ModelProvider:
    """
    تشخیص provider از روی نام مدل
    
    🔍 منطق تشخیص:
    - ollama:*       → Ollama (محلی)
    - gpt-*          → OpenAI (رسمی)
    - سایر مدل‌ها     → OpenRouter (Grok, Gemini, Claude, Llama, Mistral, DeepSeek, Qwen, ...)
    
    Args:
        model_name: نام مدل (e.g., "gpt-4o", "x-ai/grok-beta", "google/gemini-2.0")
    
    Returns:
        ModelProvider enum
    """
    if not model_name:
        return ModelProvider.OPENAI  # Default
    
    model_lower = model_name.lower()
    
    # ✅ Ollama: prefix با "ollama:"
    if model_lower.startswith("ollama:"):
        return ModelProvider.OLLAMA
    
    # ✅ OpenAI رسمی: شروع با "gpt-" (gpt-4o, gpt-3.5-turbo, gpt-4-turbo, ...)
    if model_lower.startswith("gpt-"):
        return ModelProvider.OPENAI
    
    # ✅ OpenRouter: همه بقیه مدل‌ها
    # (google/gemini, x-ai/grok, anthropic/claude, meta-llama/*, mistralai/*, deepseek/*, qwen/*, openai/o1-*, ...)
    return ModelProvider.OPENROUTER


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
    Service برای مدیریت کامل تعاملات AI از طریق LangChain
    
    این کلاس شامل:
    - Model management با caching
    - Callback integration برای monitoring
    - Retry logic برای reliability
    - Performance tracking
    """

    def __init__(self):
        self._models = {}
        self._embeddings = None
        self._callbacks = get_default_callbacks()
        
        logger.info("🎯 LangChainService initialized")

    def _get_model(
        self, 
        model_name: str, 
        force_json: bool = False, 
        max_tokens: int = 500,
        temperature: float = 0.7,
        streaming: bool = False
    ) -> Union[ChatOpenAI, Any]:
        """
        دریافت یا ایجاد یک instance از LLM model (پشتیبانی از همه provider ها)
        
        Args:
            model_name: نام مدل (e.g., "gpt-4o", "ollama:llama3.2", "claude-3-5-sonnet")
            force_json: فعال کردن JSON mode (فقط برای OpenAI)
            max_tokens: حداکثر توکن‌های خروجی
            temperature: دمای sampling
            streaming: فعال کردن streaming
            
        Returns:
            LLM instance (ChatOpenAI, ChatOllama, ChatAnthropic, etc.)
        """
        cache_key = f"{model_name}_{'json' if force_json else 'text'}_{max_tokens}_{temperature}_{'stream' if streaming else 'batch'}"
        
        if cache_key not in self._models:
            provider = detect_model_provider(model_name)
            
            logger.info(
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
                # ✅ Ollama محلی (using new langchain-ollama package)
                try:
                    from langchain_ollama import ChatOllama
                    
                    # حذف prefix "ollama:" از نام مدل
                    actual_model_name = model_name.replace("ollama:", "").replace("Ollama:", "")
                    
                    ollama_url = settings.ollama_url_loaded
                    
                    self._models[cache_key] = ChatOllama(
                        model=actual_model_name,
                        base_url=ollama_url,
                        temperature=temperature,
                        num_predict=max_tokens,  # Ollama uses num_predict instead of max_tokens
                    )
                    logger.info(f"✅ Ollama model {actual_model_name} ready at {ollama_url}")
                    
                except ImportError:
                    logger.error("❌ langchain-ollama not installed. Install with: pip install -U langchain-ollama")
                    raise Exception("Ollama support requires langchain-ollama package")
            
            elif provider == ModelProvider.OPENROUTER:
                # ✅ OpenRouter (Grok, Gemini, Claude, Llama, Mistral, DeepSeek, Qwen, O1, ...)
                # 🔑 از OPENAI_API_KEY و OPENAI_BASE_URL استفاده می‌کند
                model_kwargs = {}
                if force_json:
                    model_kwargs["response_format"] = {"type": "json_object"}
                    logger.info("📋 JSON mode enabled")

                self._models[cache_key] = ChatOpenAI(
                    model_name=model_name,
                    openai_api_key=settings.openai_api_key_loaded,      # 🔑 OpenRouter API Key
                    base_url=settings.openai_base_url_loaded,           # 🔗 OpenRouter Base URL
                    temperature=temperature,
                    max_tokens=max_tokens,
                    streaming=streaming,
                    callbacks=self._callbacks,
                    model_kwargs=model_kwargs
                )
                logger.info(f"✅ OpenRouter model {model_name} ready (via {settings.openai_base_url_loaded})")
            
            else:  # ModelProvider.OPENAI (رسمی)
                # ✅ OpenAI رسمی (gpt-4o, gpt-3.5-turbo, ...)
                # 🔑 از Embedder_API_KEY و Embedder_OPENAI_BASE_URL استفاده می‌کند
                model_kwargs = {}
                if force_json:
                    model_kwargs["response_format"] = {"type": "json_object"}
                    logger.info("📋 JSON mode enabled")

                self._models[cache_key] = ChatOpenAI(
                    model_name=model_name,
                    openai_api_key=settings.embedder_api_key_loaded or settings.openai_api_key_loaded,        # 🔑 OpenAI Official API Key
                    base_url=settings.embedder_openai_base_url_loaded or settings.openai_base_url_loaded,     # 🔗 OpenAI Official Base URL
                    temperature=temperature,
                    max_tokens=max_tokens,
                    streaming=streaming,
                    callbacks=self._callbacks,
                    model_kwargs=model_kwargs
                )
                logger.info(f"✅ OpenAI model {model_name} ready (Official API)")
        else:
            logger.debug(f"♻️ Using cached model: {cache_key}")
        
        return self._models[cache_key]
    
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

                # استفاده از 1000 توکن برای metadata generation
                model = self._get_model(selected_model, force_json=True, max_tokens=1000)
                logger.info(f"✅ Model loaded successfully: {selected_model}")

                prompt = ChatPromptTemplate.from_template("""
                    شما یک متخصص تولید متادیتای مقالات هستید. برای مقاله زیر، متادیتای کامل تولید کنید.

                    **عنوان مقاله:** {title}
                    **محتوای مقاله:** {content}

                    **دستورالعمل‌های مهم برای تولید خلاصه:**
                    1. خلاصه باید یک پاراگراف منسجم و روان باشد (نه فهرست یا نقطه‌چین)
                    2. خلاصه باید در 2-4 جمله، محتوای اصلی مقاله را توضیح دهد
                    3. خلاصه باید مفید و قابل فهم باشد حتی اگر مقاله کامل خوانده نشده باشد
                    4. از کلمات کلیدی مهم مقاله استفاده کنید
                    5. خلاصه باید به زبان فارسی روان باشد

                    **مثال خلاصه خوب:**
                    "این راهنما نحوه استقرار و راه‌اندازی نرم‌افزار مدیریت فروش را شرح می‌دهد. ابتدا تنظیمات اولیه سیستم انجام می‌شود و سپس کاربران و محصولات به سیستم اضافه می‌گردند."

                    **مثال خلاصه بد (استفاده نکنید):**
                    "استقرار نرم افزار مدیریت فروش
                    1. تنظیمات
                    2. راه‌اندازی"

                    **دستورالعمل‌های تگ‌ها:**
                    - 3 تا 5 تگ کلیدی و مرتبط انتخاب کنید
                    - تگ‌ها باید مفاهیم اصلی مقاله را پوشش دهند
                    - از کلمات ساده و قابل جستجو استفاده کنید

                    **دستورالعمل‌های دسته‌بندی:**
                    - یکی از دسته‌بندی‌های زیر را انتخاب کنید:
                    * "راهنمای محصول" - برای آموزش استفاده از محصول
                    * "مشکلات فنی" - برای حل مشکلات و عیب‌یابی
                    * "حساب کاربری و صورتحساب" - برای مسائل مالی و حساب کاربری
                    * "عمومی" - برای سایر موضوعات

                    **دستورالعمل‌های سطح دسترسی:**
                    - یکی از موارد زیر را انتخاب کنید:
                    * "public" - برای اطلاعات عمومی و غیرمحرمانه
                    * "customer" - فقط برای مشتریان وارد شده
                    * "internal" - فقط برای کارمندان و تیم داخلی

                    **فقط JSON زیر را برگردانید (بدون توضیح اضافی):**
                    {{
                    "summary": "خلاصه کامل به صورت پاراگراف منسجم",
                    "tags": ["تگ1", "تگ2", "تگ3"],
                    "suggested_category": "دسته‌بندی",
                    "suggested_visibility": "دسترسی"
                    }}
                """)

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

            # استفاده از max_tokens بالا برای markdown conversion (4096 توکن)
            model = self._get_model(selected_model, force_json=False, max_tokens=4096)
            logger.info(f"✅ مدل {selected_model} برای تبدیل Markdown بارگذاری شد (max_tokens: 4096)")

            prompt = ChatPromptTemplate.from_template("""
                شما یک متخصص تبدیل متن به فرمت Markdown هستید. متن ساده زیر را به فرمت Markdown تبدیل کنید:

                **عنوان مقاله:** {title}

                **محتوای متن:**
                {content}

                **دستورالعمل‌ها:**
                1. عنوان اصلی را با # مشخص کنید
                2. زیرعنوان‌ها را با ##، ###، #### مشخص کنید
                3. فهرست‌ها را با - یا 1. مشخص کنید
                4. متن مهم را با **bold** یا *italic* مشخص کنید
                5. کدها را با ``` مشخص کنید
                6. جداول را با فرمت Markdown ایجاد کنید
                7. لینک‌ها را با [متن](URL) مشخص کنید
                8. نقل قول‌ها را با > مشخص کنید

                **فقط محتوای Markdown را برگردانید، بدون توضیح اضافی:**
            """)

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
            model = self._get_model(settings.chat_model_loaded, force_json=False)

            # Create prompt for chat
            system_message = "You are a helpful customer support assistant. Answer questions in Persian (Farsi)."

            if context:
                system_message += f"\n\nRelevant context:\n{context}"

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
            # استفاده از مدل با streaming enabled
            model = self._get_model(
                settings.chat_model_loaded, 
                force_json=False,
                streaming=True
            )
            
            # Create prompt for chat
            system_message = "You are a helpful customer support assistant. Answer questions in Persian (Farsi)."
            
            if context:
                system_message += f"\n\nRelevant context:\n{context}"
            
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
        query_type: str = "general"  # 🎯 نوع سوال: specific, general, explanation
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
            model_name = custom_model or settings.rag_model_loaded
            temperature = custom_temperature if custom_temperature is not None else 0.3
            
            # 🎯 تطبیق max_tokens با نوع سوال
            if query_type == "specific":
                max_tokens = 800  # سوالات خاص: پاسخ کوتاه
            elif query_type == "explanation":
                max_tokens = 1500  # توضیحات: پاسخ متوسط
            else:  # general
                max_tokens = 4000  # سوالات عمومی: پاسخ جامع (افزایش یافته)
            
            logger.info(f"🎯 Max Tokens for query type '{query_type}': {max_tokens}")
            
            model = self._get_model(
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

            # Build conversation history text
            history_text = ""
            if conversation_history and len(conversation_history) > 0:
                history_text = "\n**تاریخچه مکالمه:**\n"
                for msg in conversation_history:
                    role_fa = "کاربر" if msg["role"] == "user" else "سالی"
                    history_text += f"{role_fa}: {msg['content']}\n"
                history_text += "\n"

            # 🎯 تطبیق سبک پاسخ با نوع سوال
            logger.info(f"🎯 Query Type: {query_type}")
            if query_type == "specific":
                response_guide = """
📏 **راهنمای طول و سبک پاسخ:**
   - ⚠️ CRITICAL: این یک سوال خاص است - پاسخ باید کوتاه و مستقیم باشد
   - فقط به سوال پرسیده شده پاسخ دهید، نه بیشتر
   - ابتدا پاسخ مستقیم را در 1-2 جمله ارائه دهید
   - سپس فقط یک توضیح کوتاه 2-3 جمله‌ای (اگر لازم است)
   - از ارائه "نحوه انجام"، "راهنمای گام به گام"، یا "بخش‌های اضافی" خودداری کنید
   - از ساختارهای پیچیده (بخش 1، بخش 2) استفاده نکنید
   - پاسخ کل: حداکثر 2-3 پاراگراف کوتاه (100-150 کلمه)
   
**مثال پاسخ خوب:**
سوال: "چرا X ضروری است؟"
پاسخ: "X به این دلیل ضروری است که [دلیل اصلی]. این کار باعث می‌شود [نتیجه]."
"""
            elif query_type == "explanation":
                response_guide = """
📏 **راهنمای طول و سبک پاسخ:**
   - این یک درخواست توضیح است - پاسخ متوسط با مراحل واضح ارائه دهید
   - ابتدا خلاصه‌ای کوتاه بدهید، سپس مراحل/نکات را شماره‌گذاری کنید
   - هر مرحله را به طور مختصر توضیح دهید
   - پاسخ کل باید 3-5 پاراگراف باشد
"""
            else:  # general
                response_guide = """
📏 **راهنمای طول و سبک پاسخ:**
   - این یک سوال عمومی است - پاسخ جامع و کامل ارائه دهید
   - تمام جنبه‌های موضوع را پوشش دهید
   - از ساختار سلسله مراتبی با عناوین و زیرعنوان‌ها استفاده کنید
   - پاسخ می‌تواند 5-10 پاراگراف یا بیشتر باشد
"""

            prompt = ChatPromptTemplate.from_template("""شما "سالی"، یک دستیار هوشمند پشتیبانی مشتریان حرفه‌ای هستید که با دقت و جامعیت بالا پاسخ می‌دهد.

{response_guide}

**رویکرد پاسخ‌دهی شما:**

✅ **جامع و کامل باشید:**
   - تمام جزئیات مرتبط را از همه بخش‌های Context استخراج کنید
   - به تمام بخش‌های سوال پاسخ دهید  
   - اگر چندین بخش مرتبط وجود دارد، همه را ذکر کنید
   - اگر اطلاعات در بخش‌های مختلف Context پراکنده است، آنها را ترکیب کنید
   - ⚠️ **مهم:** Context شامل چندین بخش است (بخش 1، بخش 2، ...) - حتماً همه بخش‌ها را مطالعه و در پاسخ لحاظ کنید

✅ **با کلمات خودتان بازنویسی کنید:**
   - از مفاهیم و اطلاعات Context استفاده کنید اما آنها را با کلمات خودتان بیان کنید
   - پاسخ را روان و طبیعی بنویسید نه copy-paste از متن
   - مثال‌ها و توضیحات موجود را حفظ کنید اما به شیوه‌ای قابل فهم‌تر ارائه دهید

✅ **ساختاریافته و خوانا باشید:**
   - از عناوین و زیرعنوان‌های مناسب استفاده کنید
   - از فهرست‌های شماره‌دار یا نقطه‌ای برای سازماندهی بهتر استفاده کنید
   - اطلاعات کلیدی را برجسته کنید (با **bold**)
   - پاسخ را به صورت منطقی و سلسله مراتبی سازماندهی کنید
   - برای هر مفهوم اصلی یک بخش جداگانه بسازید

🎓 **CRITICAL - آموزش‌دهنده باشید، نه فقط پاسخ‌دهنده:**
   - ⭐ **اجباری:** برای هر مفهوم کلیدی، حتماً یک **مثال عملی** با سناریوی واقعی بیاورید
   - ⭐ **اجباری:** هر فرآیند را با توضیح **نتیجه نهایی** تکمیل کنید (مثلاً "در نتیجه، سیستم...")
   - ⭐ **اجباری:** برای هر قابلیت، **چرا مهم است** را توضیح دهید (مثلاً "این به شما کمک می‌کند...")
   - ⭐ **قالب مثال:**
     * ❌ ضعیف: "گزینه X برای Y است."
     * ✅ قوی: "گزینه X برای Y است. **مثال عملی:** فرض کنید شما یک فروشگاه لوازم خانگی دارید و می‌خواهید... [سناریو]. با فعال کردن این گزینه... [نحوه کار]. در نتیجه، سیستم... [نتیجه]. **فایده:** این کار به شما کمک می‌کند تا... [مزیت تجاری]."

✅ **فقط بر اساس Context:**
   - Context شامل چندین بخش است - همه را بررسی کنید
   - هرگز اطلاعات خارج از Context اضافه نکنید
   - اگر چیزی در Context نیست، صریحاً بگویید

🚫 **ممنوعیت‌های مطلق (CRITICAL - جداً رعایت کنید):**
   - ⛔ شما باید صرفاً و منحصراً بر اساس اطلاعات موجود در Context پاسخ دهید
   - ⛔ اکیداً از ابداع هرگونه قابلیت، فرآیند، دلیل، یا راه‌حلی که به صراحت در Context ذکر نشده، خودداری کنید
   - ⛔ هرگز از دانش عمومی خود استفاده نکنید - فقط حقایق دقیق ذکر شده در Context را گزارش دهید
   - ⛔ از اضافه کردن مفاهیم مانند "قوانین"، "مالیات"، "گمرک"، "قانونی" خودداری کنید مگر اینکه دقیقاً در Context باشند
   - اگر پاسخ سوال به طور مستقیم در Context وجود ندارد، بیان کنید: "بر اساس اطلاعات موجود، اطلاعاتی در این مورد ذکر نشده است"
   - **مثال ممنوع:** Context: "معین‌های متفاوت" → شما نمی‌توانید بگویید "به دلیل قوانین مالیاتی متفاوت است"
   - **مثال صحیح:** Context: "معین‌های متفاوت" → شما باید بگویید "معین‌های متفاوت است" - همین!

✅ **به تاریخچه مکالمه توجه کنید:**
   - اگر کاربر به مکالمه قبلی اشاره می‌کند، آن را در نظر بگیرید
   - اگر سوال ادامه بحث قبلی است، پیوستگی را حفظ کنید

{history}

**منابع اطلاعاتی (شامل چندین بخش مرتبط):**
{context}

**سوال کاربر:** {query}

**⚠️ یادآوری‌های حیاتی - لطفاً دقیقاً رعایت کنید:**

🎯 **این یک راهنمای کامل است، نه خلاصه:**
   - هدف شما ارائه یک راهنمای فنی کامل و دقیق است، نه یک خلاصه
   - از حذف کردن جزئیات، حتی اگر به نظر کوچک می‌آیند، جداً خودداری کنید
   - هر توضیح، هر "چرا"، هر مسیر دسترسی، هر نکته فنی را ذکر کنید

📊 **ساختار دقیق مانند یک مستند فنی:**
   - از شماره‌گذاری واضح استفاده کنید (1. 2. 3. و 1.1، 1.2، ...)
   - هر مفهوم مجزا باید یک بخش جداگانه داشته باشد
   - برای هر تنظیم/ویژگی، **چرا** و **چگونه** آن را توضیح دهید

🔍 **جزئیات کلیدی که نباید فراموش شوند:**
   - مسیرهای دسترسی در نرم‌افزار (مثل: از اطلاعات پایه → گزینه X)
   - دلیل و کاربرد هر تنظیم (مثلاً "چرا" نوع داخلی/صادراتی مهم است)
   - تفاوت‌های مهم (مثل تفاوت بین سند بر مبنای مشتری vs بازاریاب)
   - تمام گزینه‌های ممکن (مثلاً اگر 3 روش محاسبه وجود دارد، هر 3 را با جزئیات توضیح دهید)

✅ **تکمیل پاسخ:**
   - پاسخ را با یک نتیجه‌گیری کامل (2-3 جمله) تمام کنید
   - نتیجه‌گیری باید خلاصه ارزش و کاربرد اصلی موضوع باشد
   - نتیجه‌گیری را حتماً تمام کنید و در نیمه‌راه متوقف نشوید

**پاسخ جامع و کامل شما (به صورت یک راهنمای فنی مفصل):**""")

            chain = prompt | model

            result = await chain.ainvoke({
                "response_guide": response_guide,
                "history": history_text,
                "context": context,
                "query": query
            })

            logger.info(f"✅ RAG response generated: {len(result.content)} characters")
            return result.content

        except Exception as e:
            logger.error(f"❌ RAG response generation failed: {e}", exc_info=True)
            return "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم. لطفاً بعداً دوباره امتحان کنید."
    
    async def generate_rag_response_stream(
        self, 
        query: str, 
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        custom_model: Optional[str] = None,
        custom_temperature: Optional[float] = None,
        query_type: str = "general"  # 🎯 نوع سوال: specific, general, explanation
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
            model_name = custom_model or settings.rag_model_loaded
            temperature = custom_temperature if custom_temperature is not None else 0.3
            
            logger.info(f"🌊 Streaming with model: {model_name}, temperature: {temperature}")
            
            # 🎯 تطبیق max_tokens با نوع سوال
            if query_type == "specific":
                max_tokens = 800  # سوالات خاص: پاسخ کوتاه
            elif query_type == "explanation":
                max_tokens = 1500  # توضیحات: پاسخ متوسط
            else:  # general
                max_tokens = 4000  # سوالات عمومی: پاسخ جامع (افزایش یافته)
            
            logger.info(f"🎯 Max Tokens for query type '{query_type}': {max_tokens}")
            
            # استفاده از مدل با streaming enabled
            model = self._get_model(
                model_name, 
                force_json=False,
                streaming=True,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 🔥 DEBUG: Log context preview
            logger.info(f"📝 Context preview (first 500 chars): {context[:500]}...")
            logger.info(f"📝 Context length: {len(context)} characters")
            logger.info(f"❓ Query: {query}")
            
            # 🎯 تطبیق سبک پاسخ با نوع سوال
            logger.info(f"🎯 Query Type: {query_type}")
            if query_type == "specific":
                response_guide = """
📏 **راهنمای طول و سبک پاسخ:**
   - ⚠️ CRITICAL: این یک سوال خاص است - پاسخ باید کوتاه و مستقیم باشد
   - فقط به سوال پرسیده شده پاسخ دهید، نه بیشتر
   - ابتدا پاسخ مستقیم را در 1-2 جمله ارائه دهید
   - سپس فقط یک توضیح کوتاه 2-3 جمله‌ای (اگر لازم است)
   - از ارائه "نحوه انجام"، "راهنمای گام به گام"، یا "بخش‌های اضافی" خودداری کنید
   - از ساختارهای پیچیده (بخش 1، بخش 2) استفاده نکنید
   - پاسخ کل: حداکثر 2-3 پاراگراف کوتاه (100-150 کلمه)
   
**مثال پاسخ خوب:**
سوال: "چرا X ضروری است؟"
پاسخ: "X به این دلیل ضروری است که [دلیل اصلی]. این کار باعث می‌شود [نتیجه]."
"""
            elif query_type == "explanation":
                response_guide = """
📏 **راهنمای طول و سبک پاسخ:**
   - این یک درخواست توضیح است - پاسخ متوسط با مراحل واضح ارائه دهید
   - ابتدا خلاصه‌ای کوتاه بدهید، سپس مراحل/نکات را شماره‌گذاری کنید
   - هر مرحله را به طور مختصر توضیح دهید
   - پاسخ کل باید 3-5 پاراگراف باشد
"""
            else:  # general
                response_guide = """
📏 **راهنمای طول و سبک پاسخ:**
   - این یک سوال عمومی است - پاسخ جامع و کامل ارائه دهید
   - تمام جنبه‌های موضوع را پوشش دهید
   - از ساختار سلسله مراتبی با عناوین و زیرعنوان‌ها استفاده کنید
   - پاسخ می‌تواند 5-10 پاراگراف یا بیشتر باشد
"""
            
            prompt = ChatPromptTemplate.from_template("""شما "سالی"، یک دستیار هوشمند پشتیبانی مشتریان حرفه‌ای هستید که با دقت و جامعیت بالا پاسخ می‌دهد.

{response_guide}

**رویکرد پاسخ‌دهی شما:**

✅ **جامع و کامل باشید:**
   - تمام جزئیات مرتبط را از همه بخش‌های Context استخراج کنید
   - به تمام بخش‌های سوال پاسخ دهید  
   - اگر چندین بخش مرتبط وجود دارد، همه را ذکر کنید
   - اگر اطلاعات در بخش‌های مختلف Context پراکنده است، آنها را ترکیب کنید
   - ⚠️ **مهم:** Context شامل چندین بخش است (بخش 1، بخش 2، ...) - حتماً همه بخش‌ها را مطالعه و در پاسخ لحاظ کنید

✅ **با کلمات خودتان بازنویسی کنید:**
   - از مفاهیم و اطلاعات Context استفاده کنید اما آنها را با کلمات خودتان بیان کنید
   - پاسخ را روان و طبیعی بنویسید نه copy-paste از متن
   - مثال‌ها و توضیحات موجود را حفظ کنید اما به شیوه‌ای قابل فهم‌تر ارائه دهید

✅ **ساختاریافته و خوانا باشید:**
   - از عناوین و زیرعنوان‌های مناسب استفاده کنید
   - از فهرست‌های شماره‌دار یا نقطه‌ای برای سازماندهی بهتر استفاده کنید
   - اطلاعات کلیدی را برجسته کنید (با **bold**)
   - پاسخ را به صورت منطقی و سلسله مراتبی سازماندهی کنید
   - برای هر مفهوم اصلی یک بخش جداگانه بسازید

🎓 **CRITICAL - آموزش‌دهنده باشید، نه فقط پاسخ‌دهنده:**
   - ⭐ **اجباری:** برای هر مفهوم کلیدی، حتماً یک **مثال عملی** با سناریوی واقعی بیاورید
   - ⭐ **اجباری:** هر فرآیند را با توضیح **نتیجه نهایی** تکمیل کنید (مثلاً "در نتیجه، سیستم...")
   - ⭐ **اجباری:** برای هر قابلیت، **چرا مهم است** را توضیح دهید (مثلاً "این به شما کمک می‌کند...")
   - ⭐ **قالب مثال:**
     * ❌ ضعیف: "گزینه X برای Y است."
     * ✅ قوی: "گزینه X برای Y است. **مثال عملی:** فرض کنید شما یک فروشگاه لوازم خانگی دارید و می‌خواهید... [سناریو]. با فعال کردن این گزینه... [نحوه کار]. در نتیجه، سیستم... [نتیجه]. **فایده:** این کار به شما کمک می‌کند تا... [مزیت تجاری]."

✅ **فقط بر اساس Context:**
   - Context شامل چندین بخش است - همه را بررسی کنید
   - هرگز اطلاعات خارج از Context اضافه نکنید
   - اگر چیزی در Context نیست، صریحاً بگویید

🚫 **ممنوعیت‌های مطلق (CRITICAL - جداً رعایت کنید):**
   - ⛔ شما باید صرفاً و منحصراً بر اساس اطلاعات موجود در Context پاسخ دهید
   - ⛔ اکیداً از ابداع هرگونه قابلیت، فرآیند، دلیل، یا راه‌حلی که به صراحت در Context ذکر نشده، خودداری کنید
   - ⛔ هرگز از دانش عمومی خود استفاده نکنید - فقط حقایق دقیق ذکر شده در Context را گزارش دهید
   - ⛔ از اضافه کردن مفاهیم مانند "قوانین"، "مالیات"، "گمرک"، "قانونی" خودداری کنید مگر اینکه دقیقاً در Context باشند
   - اگر پاسخ سوال به طور مستقیم در Context وجود ندارد، بیان کنید: "بر اساس اطلاعات موجود، اطلاعاتی در این مورد ذکر نشده است"
   - **مثال ممنوع:** Context: "معین‌های متفاوت" → شما نمی‌توانید بگویید "به دلیل قوانین مالیاتی متفاوت است"
   - **مثال صحیح:** Context: "معین‌های متفاوت" → شما باید بگویید "معین‌های متفاوت است" - همین!

**منابع اطلاعاتی (شامل چندین بخش مرتبط):**
{context}

**سوال کاربر:** {query}

**⚠️ یادآوری‌های حیاتی - لطفاً دقیقاً رعایت کنید:**

🎯 **این یک راهنمای کامل است، نه خلاصه:**
   - هدف شما ارائه یک راهنمای فنی کامل و دقیق است، نه یک خلاصه
   - از حذف کردن جزئیات، حتی اگر به نظر کوچک می‌آیند، جداً خودداری کنید
   - هر توضیح، هر "چرا"، هر مسیر دسترسی، هر نکته فنی را ذکر کنید

📊 **ساختار دقیق مانند یک مستند فنی:**
   - از شماره‌گذاری واضح استفاده کنید (1. 2. 3. و 1.1، 1.2، ...)
   - هر مفهوم مجزا باید یک بخش جداگانه داشته باشد
   - برای هر تنظیم/ویژگی، **چرا** و **چگونه** آن را توضیح دهید

🔍 **جزئیات کلیدی که نباید فراموش شوند:**
   - مسیرهای دسترسی در نرم‌افزار (مثل: از اطلاعات پایه → گزینه X)
   - دلیل و کاربرد هر تنظیم (مثلاً "چرا" نوع داخلی/صادراتی مهم است)
   - تفاوت‌های مهم (مثل تفاوت بین سند بر مبنای مشتری vs بازاریاب)
   - تمام گزینه‌های ممکن (مثلاً اگر 3 روش محاسبه وجود دارد، هر 3 را با جزئیات توضیح دهید)

✅ **تکمیل پاسخ:**
   - پاسخ را با یک نتیجه‌گیری کامل (2-3 جمله) تمام کنید
   - نتیجه‌گیری باید خلاصه ارزش و کاربرد اصلی موضوع باشد
   - نتیجه‌گیری را حتماً تمام کنید و در نیمه‌راه متوقف نشوید

**تاریخچه مکالمه (برای درک بهتر context سوالات قبلی):**
{conversation_history}

**پاسخ جامع و کامل شما (به صورت یک راهنمای فنی مفصل):**""")
            
            # Build conversation history text
            history_text = ""
            if conversation_history and len(conversation_history) > 0:
                history_text = "\n**تاریخچه مکالمه:**\n"
                for msg in conversation_history:
                    role_fa = "کاربر" if msg["role"] == "user" else "سالی"
                    history_text += f"{role_fa}: {msg['content']}\n"
                history_text += "\n"
            else:
                history_text = "هیچ تاریخچه‌ای موجود نیست. این اولین پیام است.\n\n"
            
            logger.info(f"📚 Conversation history: {len(conversation_history) if conversation_history else 0} messages")
            
            chain = prompt | model
            
            # Stream response با فیلتر هوشمند
            chunk_num = 0
            empty_chunk_count = 0
            first_content_found = False
            
            async for chunk in chain.astream({
                "response_guide": response_guide,
                "context": context,
                "conversation_history": history_text,
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
                            logger.info(f"⏭️ Skipping initial empty chunks...")
                        # هشدار برای chunk های خالی زیاد (احتمال مشکل مدل)
                        if empty_chunk_count % 100 == 0:
                            logger.warning(f"⚠️ Still getting empty chunks: {empty_chunk_count} so far (chunk #{chunk_num})")
                        continue
                    else:
                        # اولین محتوای معنادار پیدا شد
                        first_content_found = True
                        if empty_chunk_count > 0:
                            logger.info(f"✅ Skipped {empty_chunk_count} empty chunks, starting content stream...")

                # بعد از پیدا شدن اولین محتوا، همه chunks را ارسال می‌کنیم (حتی فاصله‌ها)
                if not isinstance(content, str):
                    content = str(content)
                
                # Yield content directly for faster streaming
                if content:  # حتی فاصله‌ها و newline‌ها
                    yield content
                    # تاخیر خیلی کم برای streaming سریع‌تر
                    if len(content) > 5:
                        await asyncio.sleep(0.01)
                    
            logger.info(f"✅ Streaming completed: {chunk_num} total chunks, {empty_chunk_count} empty chunks skipped")
            
            # 🔥 اگر همه chunks خالی بودن، یعنی مدل مشکل داره
            if chunk_num > 0 and empty_chunk_count == chunk_num:
                error_msg = f"⚠️ مدل '{custom_model or settings.rag_model_loaded}' پاسخ معتبری برنگرداند. لطفاً مدل دیگری انتخاب کنید (مثل gpt-4o-mini یا google/gemini-2.0-flash-exp:free)."
                logger.error(error_msg)
                yield error_msg
                    
        except Exception as e:
            logger.error(f"❌ Streaming RAG response failed: {e}", exc_info=True)
            yield "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم."


# Global instance
langchain_service = LangChainService()
