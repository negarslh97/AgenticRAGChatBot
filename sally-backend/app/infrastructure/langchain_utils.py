"""
LangChain utilities for AI model interactions.
This module provides a clean interface for using different AI models through LangChain.
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


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
    """Service for handling AI model interactions through LangChain."""

    def __init__(self):
        self._models = {}

    def _get_model(self, model_name: str, force_json: bool = False) -> ChatOpenAI:
        """Get or create a ChatOpenAI model instance."""
        cache_key = f"{model_name}_{'json' if force_json else 'text'}"
        
        if cache_key not in self._models:
            logger.info(f"🤖 بارگذاری مدل: {model_name}")
            logger.info(f"🔑 API Key تنظیم شده: {'بله' if settings.openai_api_key_loaded else 'خیر'}")
            logger.info(f"🌐 Base URL: {settings.openai_base_url_loaded or 'پیش‌فرض OpenAI'}")

            model_kwargs = {}
            if force_json:
                # Only use JSON format for metadata generation
                model_kwargs["response_format"] = {"type": "json_object"}
                logger.info("📋 حالت JSON فعال شد")

            self._models[cache_key] = ChatOpenAI(
                model_name=model_name,
                openai_api_key=settings.openai_api_key_loaded,
                base_url=settings.openai_base_url_loaded,
                temperature=0.7,
                max_tokens=500,
                model_kwargs=model_kwargs
            )
            logger.info(f"✅ مدل {model_name} آماده استفاده است")
        else:
            logger.debug(f"♻️ استفاده از مدل کش شده: {cache_key}")
        return self._models[cache_key]

    async def generate_metadata(self, title: str, content: str) -> Dict[str, Any]:
        """
        Generate metadata for an article using AI.

        Args:
            title: Article title
            content: Article content

        Returns:
            Dict containing summary, tags, category, and visibility
        """
        try:
            selected_model = settings.metadata_model_loaded
            logger.info(f"🔍 تولید فراداده با مدل: {selected_model}")
            logger.info(f"📝 عنوان مقاله: {title[:100]}...")
            logger.info(f"📊 طول محتوا: {len(content)} کاراکتر")

            model = self._get_model(selected_model, force_json=True)
            logger.info(f"✅ مدل {selected_model} با موفقیت بارگذاری شد")

            prompt = ChatPromptTemplate.from_template("""
Generate metadata for this article in Persian (Farsi).

**Title:** {title}
**Content:** {content}

Respond with ONLY valid JSON:
{{
  "summary": "خلاصه مقاله",
  "tags": ["تگ1", "تگ2", "تگ3"],
  "suggested_category": "دسته‌بندی",
  "suggested_visibility": "دسترسی"
}}

Categories: راهنمای محصول, مشکلات فنی, حساب کاربری و صورتحساب, عمومی
Visibility: public, customer, internal
""")

            # Create the chain with JSON parser
            parser = JsonOutputParser()
            chain = prompt | model | parser

            # Run the chain
            result = await chain.ainvoke({
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

            logger.info(f"✨ فراداده تولید شد:")
            logger.info(f"📋 خلاصه: {result.get('summary', 'N/A')[:100]}...")
            logger.info(f"🏷️  تگ‌ها: {result.get('tags', [])}")
            logger.info(f"📁 دسته‌بندی: {result.get('suggested_category', 'N/A')}")
            logger.info(f"👁️  دسترسی: {result.get('suggested_visibility', 'N/A')}")

            return result

        except Exception as e:
            # Return default metadata if AI fails
            logger.error(f"❌ خطا در تولید فراداده با مدل {selected_model}: {str(e)}")
            logger.warning("⚠️ استفاده از فراداده پیش‌فرض")
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

            model = self._get_model(selected_model, force_json=False)
            logger.info(f"✅ مدل {selected_model} برای تبدیل Markdown بارگذاری شد")

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

    async def generate_rag_response(self, query: str, context: str) -> str:
        """
        Generate a RAG response using AI.

        Args:
            query: User query
            context: Retrieved context from vector database

        Returns:
            AI response string
        """
        try:
            model = self._get_model(settings.rag_model_loaded, force_json=False)

            prompt = ChatPromptTemplate.from_template("""
                Based on the following context, answer the user's question in Persian (Farsi).
                If the context doesn't contain enough information to answer the question, say so politely.

                Context:
                {context}

                Question: {query}

                Answer:""")

            chain = prompt | model

            result = await chain.ainvoke({
                "context": context,
                "query": query
            })

            return result.content

        except Exception as e:
            return "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم. لطفاً بعداً دوباره امتحان کنید."


# Global instance
langchain_service = LangChainService()
