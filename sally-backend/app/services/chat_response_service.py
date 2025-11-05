"""
Chat Response Service for generating conversational AI responses.
این سرویس مسئولیت تولید پاسخ‌های محاوره‌ای AI را بر عهده دارد.
"""

from typing import Dict, Any, List, Optional, AsyncGenerator
from app.infrastructure.model_service import model_service
from app.infrastructure.prompt_service import prompt_service
from app.infrastructure.conversation_memory_service import conversation_memory_service
from app.core.logging_config import get_logger, PerformanceLogger

logger = get_logger(__name__)


class ChatResponseService:
    """
    Service for generating conversational AI responses.
    
    Responsibilities:
    - Generate natural, friendly chat responses
    - Maintain conversation context and history
    - Handle different types of conversational queries
    - Ensure consistent personality and tone
    - Support both streaming and non-streaming responses
    """

    def __init__(self):
        logger.debug("💬 ChatResponseService initialized")

    async def generate_chat_response(
        self, 
        messages: List[Dict[str, str]], 
        context: Optional[str] = None,
        custom_model: Optional[str] = None,
        custom_temperature: Optional[float] = None
    ) -> str:
        """
        Generate a chat response using AI.

        Args:
            messages: List of chat messages
            context: Optional context from RAG
            custom_model: Optional custom model name
            custom_temperature: Optional custom temperature

        Returns:
            AI response string
        """
        with PerformanceLogger(logger, "generate_chat_response", message_count=len(messages)):
            try:
                model_name = custom_model or "gpt-4o-mini"
                temperature = custom_temperature if custom_temperature is not None else 0.7
                
                model = model_service.get_model(model_name, force_json=False, temperature=temperature)
                logger.debug(f"🗣️ ChatResponseService - Using model: {model_name}, temperature: {temperature}")

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
                from langchain_core.prompts import ChatPromptTemplate
                prompt = ChatPromptTemplate.from_messages(langchain_messages)
                chain = prompt | model

                # Get response
                result = await chain.ainvoke({})
                return result.content

            except Exception as e:
                logger.debug(f"❌ Chat response generation failed: {e}", exc_info=True)
                return "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم. لطفاً بعداً دوباره امتحان کنید."
    
    async def generate_chat_response_stream(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        custom_model: Optional[str] = None,
        custom_temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming chat response using AI.
        
        Args:
            query: User query
            conversation_history: Previous messages in the conversation
            custom_model: Optional custom model name
            custom_temperature: Optional custom temperature
            
        Yields:
            Chunks of the AI response as they are generated
        """
        try:
            model_name = custom_model or "gpt-4o-mini"
            temperature = custom_temperature if custom_temperature is not None else 0.7
            
            logger.debug(f"💬 ChatResponseService - Streaming with model: {model_name}, temperature: {temperature}")
            
            # Get model from ModelService with streaming enabled
            model = model_service.get_model(
                model_name, 
                force_json=False,
                streaming=True,
                temperature=temperature,
                max_tokens=500  # Chat responses are typically shorter
            )
            
            # Get prompt from PromptService
            conversational_prompt_template = prompt_service.get_prompt("conversational_response")
            
            # 🧠 Prepare conversation history using ConversationMemoryService
            history_text = conversation_memory_service.format_history_for_prompt(conversation_history)
            
            # Construct prompt template with placeholders
            from langchain_core.prompts import ChatPromptTemplate
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

                # Filter out empty chunks (only until first meaningful content)
                if not first_content_found:
                    if not content or not isinstance(content, str) or len(content.strip()) == 0:
                        empty_chunk_count += 1
                        if empty_chunk_count == 1:
                            logger.debug(f"⏭️ Skipping initial empty chunks...")
                        continue
                    else:
                        first_content_found = True
                        if empty_chunk_count > 0:
                            logger.debug(f"✅ Skipped {empty_chunk_count} empty chunks, starting content stream...")

                # After finding first content, send all chunks
                if not isinstance(content, str):
                    content = str(content)
                
                if content:
                    yield content
                    if len(content) > 5:
                        await self._small_delay()
            
            logger.debug(f"✅ Chat streaming completed: {chunk_num} total chunks")
                    
        except Exception as e:
            logger.debug(f"❌ Chat streaming failed: {e}", exc_info=True)
            yield "متأسفانه در حال حاضر نمی‌توانم به پیام شما پاسخ دهم."

    async def generate_conversational_response(
        self,
        query: str,
        user_name: Optional[str] = None,
        conversation_context: Optional[Dict[str, Any]] = None,
        custom_model: Optional[str] = None,
        custom_temperature: Optional[float] = None
    ) -> str:
        """
        Generate a conversational response with enhanced context.
        
        Args:
            query: User query
            user_name: Optional user name for personalization
            conversation_context: Additional context about the conversation
            custom_model: Optional custom model name
            custom_temperature: Optional custom temperature
            
        Returns:
            AI response string
        """
        try:
            # Prepare enhanced context
            enhanced_context = {
                "is_first_message": conversation_context.get("is_first_message", False) if conversation_context else False,
                "user_preferences": conversation_context.get("user_preferences", {}) if conversation_context else {},
                "previous_topics": conversation_context.get("previous_topics", []) if conversation_context else [],
            }
            
            # Build messages list
            messages = [{"role": "user", "content": query}]
            
            # Add system message with enhanced context
            system_message = prompt_service.get_prompt("chat_system_message")
            
            if user_name:
                system_message += f"\n\n**اطلاعات کاربر:**\n- نام کاربر: {user_name}"
            
            if enhanced_context["is_first_message"]:
                system_message += "\n\n**نکته:** این اولین پیام کاربر در این مکالمه است. پاسخ خود را با معرفی خود شروع کنید."
            
            if enhanced_context["previous_topics"]:
                system_message += f"\n\n**موضوعات قبلی مکالمه:**\n- {', '.join(enhanced_context['previous_topics'][-3:])}"  # Last 3 topics
            
            # Convert to LangChain format
            langchain_messages = [{"role": "system", "content": system_message}]
            langchain_messages.extend(messages)
            
            # Generate response
            model_name = custom_model or "gpt-4o-mini"
            temperature = custom_temperature if custom_temperature is not None else 0.7
            
            model = model_service.get_model(model_name, force_json=False, temperature=temperature)
            
            from langchain_core.prompts import ChatPromptTemplate
            prompt = ChatPromptTemplate.from_messages(langchain_messages)
            chain = prompt | model
            
            result = await chain.ainvoke({})
            return result.content
            
        except Exception as e:
            logger.debug(f"❌ Enhanced conversational response failed: {e}", exc_info=True)
            return "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم."

    async def analyze_conversation_intent(
        self, 
        query: str, 
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Analyze the intent of a user query in the context of conversation history.
        
        Args:
            query: User query
            conversation_history: Previous messages in the conversation
            
        Returns:
            Intent analysis results
        """
        try:
            # Simple intent analysis based on query patterns
            query_lower = query.lower()
            
            intent_analysis = {
                "intent": "general",
                "confidence": 0.5,
                "requires_context": False,
                "suggested_response_type": "conversational"
            }
            
            # Check for greeting patterns
            greeting_patterns = ["سلام", "درود", "علیکم السلام", "hi", "hello", "hey"]
            if any(greeting in query_lower for greeting in greeting_patterns):
                intent_analysis["intent"] = "greeting"
                intent_analysis["confidence"] = 0.9
                intent_analysis["suggested_response_type"] = "friendly_greeting"
            
            # Check for gratitude patterns
            gratitude_patterns = ["ممنون", "سپاسگزارم", "مرسی", "thanks", "thank you"]
            if any(gratitude in query_lower for gratitude in gratitude_patterns):
                intent_analysis["intent"] = "gratitude"
                intent_analysis["confidence"] = 0.9
                intent_analysis["suggested_response_type"] = "appreciation"
            
            # Check for farewell patterns
            farewell_patterns = ["خداحافظ", "پایان", "bye", "goodbye"]
            if any(farewell in query_lower for farewell in farewell_patterns):
                intent_analysis["intent"] = "farewell"
                intent_analysis["confidence"] = 0.9
                intent_analysis["suggested_response_type"] = "friendly_farewell"
            
            # Check for question patterns
            question_patterns = ["چطور", "چگونه", "چرا", "چه", "کجا", "چه زمانی", "how", "why", "what", "when", "where"]
            if any(pattern in query_lower for pattern in question_patterns):
                intent_analysis["intent"] = "question"
                intent_analysis["confidence"] = 0.7
                intent_analysis["requires_context"] = True
                intent_analysis["suggested_response_type"] = "informative"
            
            # Check for statement patterns
            statement_patterns = ["فکر میکنم", "به نظرم", "I think", "I believe"]
            if any(pattern in query_lower for pattern in statement_patterns):
                intent_analysis["intent"] = "statement"
                intent_analysis["confidence"] = 0.6
                intent_analysis["suggested_response_type"] = "conversational"
            
            logger.debug(f"🎯 Intent analysis for query '{query[:50]}...': {intent_analysis}")
            return intent_analysis
            
        except Exception as e:
            logger.debug(f"❌ Intent analysis failed: {e}", exc_info=True)
            return {
                "intent": "general",
                "confidence": 0.5,
                "requires_context": False,
                "suggested_response_type": "conversational"
            }

    async def _small_delay(self):
        """Small delay for better streaming experience."""
        import asyncio
        await asyncio.sleep(0.01)


# Global instance
chat_response_service = ChatResponseService()