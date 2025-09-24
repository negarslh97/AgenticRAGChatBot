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


class LangChainService:
    """Service for handling AI model interactions through LangChain."""

    def __init__(self):
        self._models = {}

    def _get_model(self, model_name: str) -> ChatOpenAI:
        """Get or create a ChatOpenAI model instance."""
        if model_name not in self._models:
            logger.info(f"🤖 بارگذاری مدل: {model_name}")
            logger.info(f"🔑 API Key تنظیم شده: {'بله' if settings.openai_api_key_loaded else 'خیر'}")
            logger.info(f"🌐 Base URL: {settings.openai_base_url_loaded or 'پیش‌فرض OpenAI'}")

            self._models[model_name] = ChatOpenAI(
                model_name=model_name,
                openai_api_key=settings.openai_api_key_loaded,
                openai_api_base=settings.openai_base_url_loaded,
                temperature=0.7,
                max_tokens=500,
            )
            logger.info(f"✅ مدل {model_name} آماده استفاده است")
        else:
            logger.debug(f"♻️ استفاده از مدل کش شده: {model_name}")
        return self._models[model_name]

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
            print(f"🔍 تولید فراداده با مدل: {selected_model}")
            print(f"📝 عنوان مقاله: {title[:100]}...")
            print(f"📊 طول محتوا: {len(content)} کاراکتر")
            logger.info(f"🔍 تولید فراداده با مدل: {selected_model}")
            logger.info(f"📝 عنوان مقاله: {title[:100]}...")
            logger.info(f"📊 طول محتوا: {len(content)} کاراکتر")

            model = self._get_model(selected_model)
            print(f"✅ مدل {selected_model} با موفقیت بارگذاری شد")
            logger.info(f"✅ مدل {selected_model} با موفقیت بارگذاری شد")

            prompt = ChatPromptTemplate.from_template("""
                You are an expert content strategist for a knowledge base. Your task is to analyze the following article and generate structured metadata in Persian (Farsi).

                **Instructions:**
                1. Generate a concise, professional **summary**.
                2. Generate 3 to 5 relevant **tags**.
                3. Suggest a **category** from the provided list.
                4. Suggest a **visibility** level based on the content.
                5. Your output **MUST** be a single, valid JSON object and nothing else.

                **Available Options:**
                - Categories: ["راهنمای محصول", "مشکلات فنی", "حساب کاربری و صورتحساب", "عمومی"]
                - Visibility: ["public", "customer", "internal"]

                **Article to Analyze:**
                - Title: {title}
                - Content: {content}

                **Required JSON Output:**
                {{
                "summary": "...",
                "tags": ["...", "..."],
                "suggested_category": "...",
                "suggested_visibility": "..."
                }}
            """)

            # Create the chain
            parser = JsonOutputParser(pydantic_object=MetadataOutput)
            chain = prompt | model | parser

            # Run the chain
            result = await chain.ainvoke({
                "title": title,
                "content": content
            })

            print(f"✨ فراداده تولید شد:")
            print(f"   📋 خلاصه: {result.get('summary', 'N/A')[:100]}...")
            print(f"   🏷️  تگ‌ها: {result.get('tags', [])}")
            print(f"   📁 دسته‌بندی: {result.get('suggested_category', 'N/A')}")
            print(f"   👁️  دسترسی: {result.get('suggested_visibility', 'N/A')}")
            logger.info(f"✨ فراداده تولید شد:")
            logger.info(f"   📋 خلاصه: {result.get('summary', 'N/A')[:100]}...")
            logger.info(f"   🏷️  تگ‌ها: {result.get('tags', [])}")
            logger.info(f"   📁 دسته‌بندی: {result.get('suggested_category', 'N/A')}")
            logger.info(f"   👁️  دسترسی: {result.get('suggested_visibility', 'N/A')}")

            return result

        except Exception as e:
            # Return default metadata if AI fails
            logger.error(f"❌ خطا در تولید فراداده با مدل {selected_model}: {str(e)}")
            logger.warning("⚠️ استفاده از فراداده پیش‌فرض")
            return {
                "summary": f"محتوای استخراج شده از فایل: {title}",
                "tags": ["آپلود شده", "فایل"],
                "suggested_category": "عمومی",
                "suggested_visibility": "internal"
            }

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
            model = self._get_model(settings.chat_model_loaded)

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
            model = self._get_model(settings.rag_model_loaded)

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
