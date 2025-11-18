"""
Orchestrator Service for coordinating different AI services.
این سرویس مسئولیت هماهنگی بین سرویس‌های مختلف AI را بر عهده دارد.
"""

from typing import Dict, Any, List, Optional, AsyncGenerator
from app.services.metadata_service import metadata_service
from app.services.markdown_conversion_service import markdown_conversion_service
from app.services.chat_response_service import chat_response_service
from app.services.rag_response_service import rag_response_service
from app.infrastructure.conversation_memory_service import conversation_memory_service
from app.core.logging_config import get_logger, PerformanceLogger

logger = get_logger(__name__)


class OrchestratorService:
    """
    Central orchestrator for coordinating different AI services.
    
    Responsibilities:
    - Coordinate between different service classes
    - Manage service dependencies and workflows
    - Handle service failures and fallbacks
    - Provide unified interface for complex operations
    - Monitor service performance and health
    """

    def __init__(self):
        logger.debug("🎯 OrchestratorService initialized")
        
        # Service instances
        self.metadata_service = metadata_service
        self.markdown_conversion_service = markdown_conversion_service
        self.chat_response_service = chat_response_service
        self.rag_response_service = rag_response_service
        self.conversation_memory_service = conversation_memory_service

    async def process_article(
        self, 
        title: str, 
        content: str, 
        convert_to_markdown: bool = True
    ) -> Dict[str, Any]:
        """
        Process an article through multiple services.
        
        Args:
            title: Article title
            content: Article content
            convert_to_markdown: Whether to convert content to markdown
            
        Returns:
            Processing results including metadata and converted content
        """
        with PerformanceLogger(logger, "process_article", title=title[:50], content_length=len(content)):
            try:
                results = {
                    "title": title,
                    "original_content": content,
                    "metadata": None,
                    "converted_content": None,
                    "processing_successful": False,
                    "errors": []
                }
                
                # Step 1: Generate metadata
                try:
                    logger.debug("📝 Generating article metadata...")
                    metadata = await self.metadata_service.generate_metadata(title, content)
                    results["metadata"] = metadata
                    logger.debug("✅ Metadata generated successfully")
                except Exception as e:
                    error_msg = f"Metadata generation failed: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.debug(f"❌ {error_msg}")
                
                # Step 2: Convert to markdown (if requested)
                if convert_to_markdown:
                    try:
                        logger.debug("🔄 Converting content to markdown...")
                        converted_content = await self.markdown_conversion_service.convert_text_to_markdown(title, content)
                        results["converted_content"] = converted_content
                        logger.debug("✅ Content converted to markdown successfully")
                    except Exception as e:
                        error_msg = f"Markdown conversion failed: {str(e)}"
                        results["errors"].append(error_msg)
                        logger.debug(f"❌ {error_msg}")
                        # Use original content as fallback
                        results["converted_content"] = content
                
                # Step 3: Validate results
                if results["metadata"] or results["converted_content"]:
                    results["processing_successful"] = True
                
                logger.debug(f"📊 Article processing completed: {len(results['errors'])} errors")
                return results
                
            except Exception as e:
                logger.debug(f"❌ Article processing failed: {e}", exc_info=True)
                return {
                    "title": title,
                    "original_content": content,
                    "metadata": None,
                    "converted_content": content,
                    "processing_successful": False,
                    "errors": [f"Processing failed: {str(e)}"]
                }

    async def handle_conversation(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        context: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None,
        custom_model: Optional[str] = None,
        custom_temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Handle a conversation query by orchestrating appropriate services.
        
        Args:
            query: User query
            conversation_history: Previous messages
            context: Optional RAG context
            user_context: Additional user context
            custom_model: Optional custom model
            custom_temperature: Optional custom temperature
            
        Returns:
            Conversation handling results
        """
        with PerformanceLogger(logger, "handle_conversation", query=query[:50]):
            try:
                results = {
                    "query": query,
                    "response": None,
                    "response_type": None,
                    "intent": None,
                    "services_used": [],
                    "processing_successful": False,
                    "errors": []
                }
                
                # Step 1: Analyze conversation intent
                try:
                    logger.debug("🎯 Analyzing conversation intent...")
                    intent_analysis = await self.chat_response_service.analyze_conversation_intent(query, conversation_history)
                    results["intent"] = intent_analysis
                    logger.debug(f"✅ Intent analysis: {intent_analysis}")
                except Exception as e:
                    error_msg = f"Intent analysis failed: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.debug(f"❌ {error_msg}")
                    # Use default intent
                    intent_analysis = {"intent": "general", "confidence": 0.5, "requires_context": False}
                
                # Step 2: Determine response strategy
                response_strategy = self._determine_response_strategy(intent_analysis, context)
                results["response_type"] = response_strategy["type"]
                
                # Step 3: Generate response using appropriate service
                try:
                    logger.debug(f"🎯 Generating {response_strategy['type']} response...")
                    
                    if response_strategy["type"] == "conversational":
                        # Use chat response service
                        response = await self.chat_response_service.generate_chat_response(
                            messages=[{"role": "user", "content": query}],
                            context=context,
                            custom_model=custom_model,
                            custom_temperature=custom_temperature
                        )
                        results["services_used"].append("chat_response_service")
                        
                    elif response_strategy["type"] == "rag":
                        # Use RAG response service
                        response = await self.rag_response_service.generate_rag_response(
                            query=query,
                            context=context or "",
                            conversation_history=conversation_history,
                            custom_model=custom_model,
                            custom_temperature=custom_temperature,
                            query_type=intent_analysis.get("intent", "general")
                        )
                        results["services_used"].append("rag_response_service")
                        
                    elif response_strategy["type"] == "streaming_conversational":
                        # Handle streaming separately
                        response_chunks = []
                        async for chunk in self.chat_response_service.generate_chat_response_stream(
                            query=query,
                            conversation_history=conversation_history,
                            custom_model=custom_model,
                            custom_temperature=custom_temperature
                        ):
                            response_chunks.append(chunk)
                        response = "".join(response_chunks)
                        results["services_used"].append("chat_response_service_streaming")
                        
                    elif response_strategy["type"] == "streaming_rag":
                        # Handle streaming RAG separately
                        response_chunks = []
                        async for chunk in self.rag_response_service.generate_rag_response_stream(
                            query=query,
                            context=context or "",
                            conversation_history=conversation_history,
                            custom_model=custom_model,
                            custom_temperature=custom_temperature,
                            query_type=intent_analysis.get("intent", "general")
                        ):
                            response_chunks.append(chunk)
                        response = "".join(response_chunks)
                        results["services_used"].append("rag_response_service_streaming")
                    
                    results["response"] = response
                    logger.debug(f"✅ Response generated successfully: {len(response)} characters")
                    
                except Exception as e:
                    error_msg = f"Response generation failed: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.debug(f"❌ {error_msg}")
                    # Use fallback response
                    results["response"] = "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم. لطفاً بعداً دوباره امتحان کنید."
                
                # Step 4: Validate response quality (if RAG response)
                if response_strategy["type"] in ["rag", "streaming_rag"] and context:
                    try:
                        quality_assessment = await self.rag_response_service.validate_response_quality(
                            query=query,
                            context=context,
                            response=results["response"]
                        )
                        results["quality_assessment"] = quality_assessment
                        logger.debug(f"✅ Response quality assessed: {quality_assessment}")
                    except Exception as e:
                        logger.debug(f"❌ Quality assessment failed: {e}")
                
                # Step 5: Update conversation memory
                try:
                    if conversation_history and results["response"]:
                        # Add the interaction to memory for future context
                        updated_history = conversation_history.copy()
                        updated_history.append({"role": "user", "content": query})
                        updated_history.append({"role": "assistant", "content": results["response"]})
                        
                        # Keep only recent history to prevent context overflow
                        if len(updated_history) > 20:
                            updated_history = updated_history[-20:]
                        
                        results["updated_conversation_history"] = updated_history
                        logger.debug("✅ Conversation memory updated")
                except Exception as e:
                    logger.debug(f"❌ Conversation memory update failed: {e}")
                
                results["processing_successful"] = True
                logger.debug(f"📊 Conversation handling completed: {len(results['errors'])} errors")
                return results
                
            except Exception as e:
                logger.debug(f"❌ Conversation handling failed: {e}", exc_info=True)
                return {
                    "query": query,
                    "response": "متأسفانه در حال حاضر نمی‌توانم به سوال شما پاسخ دهم. لطفاً بعداً دوباره امتحان کنید.",
                    "response_type": "error",
                    "intent": None,
                    "services_used": [],
                    "processing_successful": False,
                    "errors": [f"Conversation handling failed: {str(e)}"]
                }

    def _determine_response_strategy(
        self, 
        intent_analysis: Dict[str, Any], 
        context: Optional[str]
    ) -> Dict[str, Any]:
        """
        Determine the appropriate response strategy based on intent and context.
        
        Args:
            intent_analysis: Intent analysis results
            context: Optional RAG context
            
        Returns:
            Response strategy configuration
        """
        intent = intent_analysis.get("intent", "general")
        requires_context = intent_analysis.get("requires_context", False)
        
        # Determine response type
        if context and requires_context:
            response_type = "rag"
        elif context:
            # Context available but not required - use RAG for better accuracy
            response_type = "rag"
        else:
            response_type = "conversational"
        
        # Determine if streaming should be used
        use_streaming = intent in ["greeting", "gratitude", "farewell"]  # Simple intents benefit from streaming
        
        if use_streaming:
            response_type = f"streaming_{response_type}"
        
        strategy = {
            "type": response_type,
            "intent": intent,
            "requires_context": requires_context,
            "use_streaming": use_streaming,
            "confidence": intent_analysis.get("confidence", 0.5)
        }
        
        logger.debug(f"🎯 Response strategy determined: {strategy}")
        return strategy

    async def get_service_health(self) -> Dict[str, Any]:
        """
        Get health status of all services.
        
        Returns:
            Health status for all services
        """
        health_status = {
            "orchestrator": {"status": "healthy", "message": "Orchestrator service is running"},
            "services": {},
            "overall_status": "healthy"
        }
        
        services_to_check = {
            "metadata_service": self.metadata_service,
            "markdown_conversion_service": self.markdown_conversion_service,
            "chat_response_service": self.chat_response_service,
            "rag_response_service": self.rag_response_service,
            "conversation_memory_service": self.conversation_memory_service
        }
        
        for service_name, service_instance in services_to_check.items():
            try:
                # Basic health check - try to access the service
                if hasattr(service_instance, '__class__'):
                    health_status["services"][service_name] = {
                        "status": "healthy",
                        "message": f"{service_name} is available",
                        "class": service_instance.__class__.__name__
                    }
                else:
                    health_status["services"][service_name] = {
                        "status": "unhealthy",
                        "message": f"{service_name} is not properly initialized",
                        "class": "unknown"
                    }
            except Exception as e:
                health_status["services"][service_name] = {
                    "status": "unhealthy",
                    "message": f"{service_name} health check failed: {str(e)}",
                    "class": service_instance.__class__.__name__ if hasattr(service_instance, '__class__') else "unknown"
                }
                health_status["overall_status"] = "degraded"
        
        # Check if all services are healthy
        all_healthy = all(service["status"] == "healthy" for service in health_status["services"].values())
        if not all_healthy:
            health_status["overall_status"] = "degraded"
        
        logger.debug(f"🏥 Service health check completed: {health_status['overall_status']}")
        return health_status


# Global instance
orchestrator_service = OrchestratorService()