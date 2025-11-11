"""
RAG Response Service for generating AI responses based on retrieved context.
این سرویس مسئولیت تولید پاسخ‌های AI بر اساس منابع بازیابی شده را بر عهده دارد.
"""

from typing import Dict, Any, List, Optional, AsyncGenerator
import re
from app.services.model_service import model_service
from app.services.prompt_service import prompt_service
from app.infrastructure.conversation_memory_service import conversation_memory_service
from app.core.logging_config import get_logger, PerformanceLogger

logger = get_logger(__name__)


class RAGResponseService:
    """
    Service for generating RAG-based AI responses.
    
    Responsibilities:
    - Generate responses based on retrieved context
    - Apply response guides based on query type
    - Handle both streaming and non-streaming responses
    - Filter out thinking blocks from responses
    - Ensure responses are context-aware and accurate
    """

    def __init__(self):
        logger.debug("🔍 RAGResponseService initialized")

    async def generate_rag_response(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        custom_model: Optional[str] = None,
        custom_temperature: Optional[float] = None,
        query_type: str = "general",  # specific, general, explanation
        prompt_name: str = "rag_response"
    ) -> str:
        """
        Generate a RAG response using AI - uses provided context and conversation history.

        Args:
            query: User query
            context: Retrieved context from vector database
            conversation_history: Previous messages in the conversation
            custom_model: Optional custom model name (overrides default)
            custom_temperature: Optional custom temperature (overrides default)
            query_type: Type of query (specific, general, explanation)
            prompt_name: Name of the prompt template to use

        Returns:
            AI response string
        """
        with PerformanceLogger(logger, "generate_rag_response", query=query[:50], context_length=len(context)):
            try:
                model_name = custom_model or "gpt-4o-mini"
                temperature = custom_temperature if custom_temperature is not None else 0.3
                logger.debug(f"🔄 RAGResponseService - Using model: {model_name}")
                
                # 🎯 Adjust max_tokens based on query type
                if query_type == "specific":
                    max_tokens = 2000
                elif query_type == "explanation":
                    max_tokens = 2500
                else:  # general
                    max_tokens = 3000
                
                logger.debug(f"🎯 Max Tokens for query type '{query_type}': {max_tokens}")
                
                # Get model from ModelService
                model = model_service.get_model(
                    model_name, 
                    force_json=False,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                logger.debug(f"🤖 Using model: {model_name} with temperature: {temperature}, max_tokens: {max_tokens}")

                # Debug log context preview
                logger.debug(f"📝 Context preview (first 500 chars): {context[:500]}...")
                logger.debug(f"📝 Context length: {len(context)} characters")
                logger.debug(f"❓ Query: {query}")
                logger.debug(f"📚 Conversation history: {len(conversation_history) if conversation_history else 0} messages")

                # Build conversation history text using ConversationMemoryService
                history_text = conversation_memory_service.format_history_for_prompt(conversation_history)

                # 🎯 Match response style with query type - use prompt files
                logger.debug(f"🎯 Query Type: {query_type}")
                if query_type == "specific":
                    response_guide = prompt_service.get_prompt("response_guides/specific_response_guide")
                elif query_type == "explanation":
                    response_guide = prompt_service.get_prompt("response_guides/explanation_response_guide")
                else:  # general
                    response_guide = prompt_service.get_prompt("response_guides/general_response_guide")

                # Get prompt from PromptService
                prompt_template = prompt_service.get_prompt(prompt_name)
                from langchain_core.prompts import ChatPromptTemplate
                prompt = ChatPromptTemplate.from_template(prompt_template)

                chain = prompt | model

                result = await chain.ainvoke({
                    "response_guide": response_guide,
                    "history": history_text,
                    "context": context,
                    "query": query
                })

                # 🧹 Remove thinking block from final response (if model generated it)
                response = result.content
                # Remove anything between <thinking> and </thinking> (with multiline support)
                response = re.sub(r'<thinking>.*?</thinking>', '', response, flags=re.DOTALL)
                response = response.strip()

                logger.debug(f"✅ RAG response generated: {len(response)} characters")
                return response

            except Exception as e:
                logger.debug(f"❌ RAG response generation failed: {e}", exc_info=True)
                return "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم. لطفاً بعداً دوباره امتحان کنید."
    
    async def generate_rag_response_stream(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        custom_model: Optional[str] = None,
        custom_temperature: Optional[float] = None,
        query_type: str = "general",  # specific, general, explanation
        prompt_name: str = "rag_response"
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming RAG response using AI - STRICT MODE: Only use provided context.
        
        Args:
            query: User query
            context: Retrieved context from vector database
            conversation_history: Previous messages in the conversation
            custom_model: Optional custom model name (overrides default)
            custom_temperature: Optional custom temperature (overrides default)
            query_type: Type of query (specific, general, explanation)
            prompt_name: Name of the prompt template to use
            
        Yields:
            Chunks of the AI response as they are generated
        """
        try:
            model_name = custom_model or "gpt-4o-mini"
            temperature = custom_temperature if custom_temperature is not None else 0.3
            logger.debug(f"🎯 RAGResponseService - Streaming with model: {model_name}")
            
            logger.debug(f"🌊 Streaming with model: {model_name}, temperature: {temperature}")
            
            # 🎯 Adjust max_tokens based on query type
            if query_type == "specific":
                max_tokens = 2000
            elif query_type == "explanation":
                max_tokens = 2500
            else:  # general
                max_tokens = 3000
            
            logger.debug(f"🎯 Max Tokens for query type '{query_type}': {max_tokens}")
            
            # Get model from ModelService with streaming enabled
            model = model_service.get_model(
                model_name, 
                force_json=False,
                streaming=True,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Debug log context preview
            logger.debug(f"📝 Context preview (first 500 chars): {context[:500]}...")
            logger.debug(f"📝 Context length: {len(context)} characters")
            logger.debug(f"❓ Query: {query}")
            
            # 🎯 Match response style with query type - use prompt files
            logger.debug(f"🎯 Query Type: {query_type}")
            if query_type == "specific":
                response_guide = prompt_service.get_prompt("response_guides/specific_response_guide")
            elif query_type == "explanation":
                response_guide = prompt_service.get_prompt("response_guides/explanation_response_guide")
            else:  # general
                response_guide = prompt_service.get_prompt("response_guides/general_response_guide")
            
            # Get prompt from PromptService
            prompt_template = prompt_service.get_prompt(prompt_name)
            from langchain_core.prompts import ChatPromptTemplate
            prompt = ChatPromptTemplate.from_template(prompt_template)

            # 🧠 Build conversation history using ConversationMemoryService
            history_text = conversation_memory_service.format_history_for_prompt(conversation_history[-10:] if conversation_history else None)
            
            chain = prompt | model
            
            # Stream response with smart filtering
            chunk_num = 0
            empty_chunk_count = 0
            first_content_found = False
            
            # 🧠 State machine for filtering thinking blocks
            inside_thinking = False
            thinking_buffer = ""  # Buffer to store potential thinking content
            
            async for chunk in chain.astream({
                "response_guide": response_guide,
                "context": context,
                "history": history_text,
                "query": query
            }):
                chunk_num += 1
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)

                # 🔧 Filter out empty chunks (only until first meaningful content)
                if not first_content_found:
                    if not content or not isinstance(content, str) or len(content.strip()) == 0:
                        empty_chunk_count += 1
                        # Skip empty chunks but log them
                        if empty_chunk_count == 1:
                            logger.debug(f"⏭️ Skipping initial empty chunks...")
                            # Warning for many empty chunks (potential model issue)
                            if empty_chunk_count % 100 == 0:
                                logger.debug(f"⚠️ Still getting empty chunks: {empty_chunk_count} so far (chunk #{chunk_num})")
                        continue
                    else:
                        # First meaningful content found
                        first_content_found = True
                        if empty_chunk_count > 0:
                            logger.debug(f"✅ Skipped {empty_chunk_count} empty chunks, starting content stream...")

                # After finding first content, send all chunks (even spaces)
                if not isinstance(content, str):
                    content = str(content)
                
                # 🧹 Filter thinking blocks in streaming mode
                if content:
                    # Add to buffer for checking thinking tags
                    thinking_buffer += content
                    
                    # Check for thinking block start
                    if '<thinking>' in thinking_buffer and not inside_thinking:
                        inside_thinking = True
                        # Send content before thinking
                        before_thinking = thinking_buffer.split('<thinking>')[0]
                        if before_thinking:
                            yield before_thinking
                        thinking_buffer = thinking_buffer.split('<thinking>', 1)[1] if '<thinking>' in thinking_buffer else ""
                        logger.debug(f"🧠 Detected <thinking> block start, filtering...")
                        continue
                    
                    # If inside thinking, check for its end
                    if inside_thinking:
                        if '</thinking>' in thinking_buffer:
                            inside_thinking = False
                            # Send content after thinking
                            after_thinking = thinking_buffer.split('</thinking>', 1)[1] if '</thinking>' in thinking_buffer else ""
                            thinking_buffer = after_thinking
                            logger.debug(f"🧠 Detected </thinking> block end, resuming stream...")
                            if after_thinking:
                                yield after_thinking
                                thinking_buffer = ""
                        # Still inside thinking, skip
                        continue
                    
                    # If buffer gets too large and no thinking found, send its content
                    if len(thinking_buffer) > 100 and not inside_thinking:
                        yield thinking_buffer
                        thinking_buffer = ""
                    elif not inside_thinking and len(thinking_buffer) < 50:
                        # If buffer is small, wait until thinking is complete or not
                        continue
                    
                    # Very small delay for faster streaming
                    if len(content) > 5:
                        await self._small_delay()
            
            # 🧹 Send remaining content in buffer (if no thinking found)
            if thinking_buffer and not inside_thinking:
                yield thinking_buffer
                logger.debug(f"✅ Flushed remaining buffer: {len(thinking_buffer)} characters")
                    
            logger.debug(f"✅ Streaming completed: {chunk_num} total chunks, {empty_chunk_count} empty chunks skipped")
            
            # 🔥 If all chunks were empty, model has issues
            if chunk_num > 0 and empty_chunk_count == chunk_num:
                error_msg = f"⚠️ مدل '{custom_model or 'default'}' پاسخ معتبری برنگرداند. لطفاً مدل دیگری انتخاب کنید (مثل gpt-4o-mini یا google/gemini-2.0-flash-exp:free)."
                logger.debug(error_msg)
                yield error_msg
                    
        except Exception as e:
            logger.debug(f"❌ Streaming RAG response failed: {e}", exc_info=True)
            yield "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم."

    async def generate_simple_rag_response(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        custom_model: Optional[str] = None,
        custom_temperature: Optional[float] = None
    ) -> str:
        """
        Generate a simple RAG response using the simple_rag_response prompt.
        
        Args:
            query: User query
            context: Retrieved context from vector database
            conversation_history: Previous messages in the conversation
            custom_model: Optional custom model name
            custom_temperature: Optional custom temperature
            
        Returns:
            AI response string
        """
        try:
            return await self.generate_rag_response(
                query=query,
                context=context,
                conversation_history=conversation_history,
                custom_model=custom_model,
                custom_temperature=custom_temperature,
                query_type="general",
                prompt_name="simple_rag_response"
            )
        except Exception as e:
            logger.debug(f"❌ Simple RAG response failed: {e}", exc_info=True)
            return "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم."

    async def validate_response_quality(
        self, 
        query: str, 
        context: str, 
        response: str
    ) -> Dict[str, Any]:
        """
        Validate the quality of a RAG response.
        
        Args:
            query: Original user query
            context: Retrieved context used for response
            response: Generated response
            
        Returns:
            Quality assessment results
        """
        quality_results = {
            "is_high_quality": True,
            "issues": [],
            "strengths": [],
            "metrics": {
                "response_length": len(response),
                "context_length": len(context),
                "query_length": len(query),
                "contains_thinking_block": "<thinking>" in response or "</thinking>" in response,
                "contains_context_keywords": any(keyword in response.lower() for keyword in context.lower().split()[:50]),  # First 50 context words
            }
        }
        
        # Basic quality checks
        if len(response) < 50:
            quality_results["is_high_quality"] = False
            quality_results["issues"].append("پاسخ خیلی کوتاه است")
            quality_results["strengths"].append("پاسخ مختصر است")
        
        if len(response) > 5000:
            quality_results["issues"].append("پاسخ خیلی طولانی است")
        
        if quality_results["metrics"]["contains_thinking_block"]:
            quality_results["is_high_quality"] = False
            quality_results["issues"].append("پاسش شامل بلوک thinking است")
        
        # Check if response addresses the query
        query_keywords = set(query.lower().split())
        response_lower = response.lower()
        keyword_coverage = sum(1 for keyword in query_keywords if keyword in response_lower)
        
        if keyword_coverage < len(query_keywords) * 0.5:  # Less than 50% keyword coverage
            quality_results["issues"].append("پاسش به طور کامل به سوال شما نمی‌پردازد")
        
        # Check if response uses context
        context_sentences = context.split('.')
        response_sentences = response.split('.')
        
        context_usage = 0
        for context_sentence in context_sentences[:5]:  # Check first 5 context sentences
            if any(context_word in response_lower for context_word in context_sentence.lower().split()[:10]):
                context_usage += 1
        
        if context_usage < 1:  # No context sentences used
            quality_results["issues"].append("پاسش از منابع ارائه شده استفاده نمی‌کند")
        
        logger.debug(f"🔍 Response quality assessment: {quality_results}")
        return quality_results

    async def _small_delay(self):
        """Small delay for better streaming experience."""
        import asyncio
        await asyncio.sleep(0.01)


# Global instance
rag_response_service = RAGResponseService()