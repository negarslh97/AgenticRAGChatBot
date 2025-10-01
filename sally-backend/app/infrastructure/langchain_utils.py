"""
LangChain utilities for AI model interactions.
این ماژول یک interface کامل و حرفه‌ای برای استفاده از LangChain فراهم می‌کند.

Features:
- Chains & Runnables برای workflow‌های پیچیده
- Callbacks برای monitoring و logging
- Memory management برای conversations
- Retry logic با exponential backoff
- Token usage tracking
- Performance monitoring
"""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel, RunnableLambda
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Tuple
import json
import asyncio
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
    - Memory management برای conversations
    - Retry logic برای reliability
    - Performance tracking
    """

    def __init__(self):
        self._models = {}
        self._embeddings = None
        self._memories = {}
        self._callbacks = get_default_callbacks()
        
        logger.info("🎯 LangChainService initialized")

    def _get_model(
        self, 
        model_name: str, 
        force_json: bool = False, 
        max_tokens: int = 500,
        temperature: float = 0.7,
        streaming: bool = False
    ) -> ChatOpenAI:
        """
        دریافت یا ایجاد یک instance از ChatOpenAI model
        
        Args:
            model_name: نام مدل
            force_json: فعال کردن JSON mode
            max_tokens: حداکثر توکن‌های خروجی
            temperature: دمای sampling
            streaming: فعال کردن streaming
            
        Returns:
            ChatOpenAI instance
        """
        cache_key = f"{model_name}_{'json' if force_json else 'text'}_{max_tokens}_{temperature}_{'stream' if streaming else 'batch'}"
        
        if cache_key not in self._models:
            logger.info(
                f"🤖 Loading model: {model_name}",
                extra={
                    'extra_data': {
                        'model': model_name,
                        'max_tokens': max_tokens,
                        'temperature': temperature,
                        'json_mode': force_json,
                        'streaming': streaming
                    }
                }
            )

            model_kwargs = {}
            if force_json:
                model_kwargs["response_format"] = {"type": "json_object"}
                logger.info("📋 JSON mode enabled")

            self._models[cache_key] = ChatOpenAI(
                model_name=model_name,
                openai_api_key=settings.openai_api_key_loaded,
                base_url=settings.openai_base_url_loaded,
                temperature=temperature,
                max_tokens=max_tokens,
                streaming=streaming,
                callbacks=self._callbacks,
                model_kwargs=model_kwargs
            )
            logger.info(f"✅ Model {model_name} ready")
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
    
    def get_or_create_memory(
        self, 
        conversation_id: str, 
        memory_type: str = "buffer"
    ) -> ConversationBufferMemory:
        """
        دریافت یا ایجاد memory برای یک conversation
        
        Args:
            conversation_id: شناسه conversation
            memory_type: نوع memory (buffer یا summary)
            
        Returns:
            Memory instance
        """
        if conversation_id not in self._memories:
            if memory_type == "summary":
                # از مدل برای خلاصه‌سازی استفاده می‌کند
                llm = self._get_model(settings.chat_model_loaded, max_tokens=150)
                self._memories[conversation_id] = ConversationSummaryMemory(
                    llm=llm,
                    memory_key="chat_history",
                    return_messages=True
                )
            else:
                self._memories[conversation_id] = ConversationBufferMemory(
                    memory_key="chat_history",
                    return_messages=True
                )
            
            logger.info(
                f"💾 Created {memory_type} memory for conversation: {conversation_id}",
                extra={'extra_data': {'conversation_id': conversation_id, 'memory_type': memory_type}}
            )
        
        return self._memories[conversation_id]
    
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

    async def generate_rag_response(self, query: str, context: str) -> str:
        """
        Generate a RAG response using AI - STRICT MODE: Only use provided context.

        Args:
            query: User query
            context: Retrieved context from vector database

        Returns:
            AI response string
        """
        try:
            model = self._get_model(settings.rag_model_loaded, force_json=False)

            prompt = ChatPromptTemplate.from_template("""
شما یک دستیار پشتیبانی مشتریان هستید که **فقط و فقط** بر اساس اطلاعات داده شده پاسخ می‌دهید.

**قوانین مهم:**
1. فقط از اطلاعات موجود در Context زیر استفاده کنید
2. اگر جواب در Context موجود نیست، حتماً بگویید: "متأسفانه اطلاعات مورد نیاز در پایگاه دانش من موجود نیست"
3. هیچ‌گاه از دانش عمومی یا اطلاعات خارج از Context استفاده نکنید
4. اگر مطمئن نیستید، ترجیح دهید بگویید نمی‌دانید
5. پاسخ را به صورت متن ساده (Plain Text) بنویسید - بدون استفاده از Markdown، ستاره (**، *)، هشتگ (#) یا علامت‌های فرمت‌دهی
6. از جملات کامل و روان استفاده کنید

Context (پایگاه دانش):
{context}

سوال کاربر: {query}

پاسخ (متن ساده - بدون فرمت Markdown):""")

            chain = prompt | model

            result = await chain.ainvoke({
                "context": context,
                "query": query
            })

            return result.content

        except Exception as e:
            return "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم. لطفاً بعداً دوباره امتحان کنید."
    
    async def generate_rag_response_stream(self, query: str, context: str):
        """
        Generate a streaming RAG response using AI - STRICT MODE: Only use provided context.
        
        Args:
            query: User query
            context: Retrieved context from vector database
            
        Yields:
            Chunks of the AI response as they are generated
        """
        try:
            # استفاده از مدل با streaming enabled
            model = self._get_model(
                settings.rag_model_loaded, 
                force_json=False,
                streaming=True
            )
            
            prompt = ChatPromptTemplate.from_template("""
شما یک دستیار پشتیبانی مشتریان هستید که **فقط و فقط** بر اساس اطلاعات داده شده پاسخ می‌دهید.

**قوانین مهم:**
1. فقط از اطلاعات موجود در Context زیر استفاده کنید
2. اگر جواب در Context موجود نیست، حتماً بگویید: "متأسفانه اطلاعات مورد نیاز در پایگاه دانش من موجود نیست"
3. هیچ‌گاه از دانش عمومی یا اطلاعات خارج از Context استفاده نکنید
4. اگر مطمئن نیستید، ترجیح دهید بگویید نمی‌دانید
5. پاسخ را به صورت متن ساده (Plain Text) بنویسید - بدون استفاده از Markdown، ستاره (**، *)، هشتگ (#) یا علامت‌های فرمت‌دهی
6. از جملات کامل و روان استفاده کنید

Context (پایگاه دانش):
{context}

سوال کاربر: {query}

پاسخ (متن ساده - بدون فرمت Markdown):""")
            
            chain = prompt | model
            
            # Stream response
            chunk_num = 0
            async for chunk in chain.astream({
                "context": context,
                "query": query
            }):
                chunk_num += 1
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                
                # 🔥 DEBUG: Log chunk size
                logger.info(f"🎯 LangChain chunk #{chunk_num}: '{content}' ({len(content)} chars)")
                
                # 🔥 تقسیم chunks بزرگ به کلمات برای نمایش روان‌تر
                if len(content) > 1:
                    # اگر chunk شامل فاصله باشه (چند کلمه)، تقسیمش می‌کنیم
                    if ' ' in content:
                        words = content.split(' ')
                        for i, word in enumerate(words):
                            if word:  # skip empty strings
                                # آخرین کلمه بدون فاصله، بقیه با فاصله
                                yield word + (' ' if i < len(words) - 1 else '')
                                await asyncio.sleep(0.03)  # تاخیر برای نمایش کلمه‌به‌کلمه
                    else:
                        # اگر فاصله نداره، همون‌طور yield کن
                        yield content
                else:
                    # chunks تک‌کاراکتری رو مستقیم yield می‌کنیم
                    yield content
                    
        except Exception as e:
            logger.error(f"❌ Streaming RAG response failed: {e}", exc_info=True)
            yield "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم."


# Global instance
langchain_service = LangChainService()
