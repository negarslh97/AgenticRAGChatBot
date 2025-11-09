# langchain_utils.py

"""
⚠️ DEPRECATED MODULE ⚠️

این ماژول منسوخ شده است و استفاده از آن توصیه نمی‌شود.
لطفاً به جای آن از LangChainOrchestrator استفاده کنید.

Deprecated Classes:
- LangChainService (انتقال یافته به LangChainOrchestrator)

This module is deprecated in favor of the new integrated architecture.
Use app.infrastructure.langchain_orchestrator instead.

Migration Guide:
from app.infrastructure.langchain_orchestrator import orchestrator

# Old way (deprecated):
from app.infrastructure.langchain_utils import langchain_service
result = await langchain_service.generate_rag_response(...)

# New way (recommended):
from app.infrastructure.langchain_orchestrator import orchestrator
result = await orchestrator.process_request(...)
"""

import warnings
import logging
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)


def _warn_about_deprecation(class_name: str, replacement: str):
    """Emit deprecation warning using builtin DeprecationWarning"""
    message = f"""
⚠️ DEPRECATED: {class_name} is deprecated and will be removed in future versions.
Please use {replacement} instead.

Old usage:
    from app.infrastructure.langchain_utils import langchain_service
    result = await langchain_service.{class_name.lower()}(...)

New usage:
    from app.infrastructure.langchain_orchestrator import orchestrator
    result = await orchestrator.process_request(...)
    """
    warnings.warn(message, DeprecationWarning, stacklevel=2)
    logger.warning(f"Deprecated class {class_name} accessed - please use {replacement}")


class LangChainService:
    """
    ⚠️ DEPRECATED CLASS ⚠️
    
    This class is deprecated. All functionality has been moved to LangChainOrchestrator.
    Please use app.infrastructure.langchain_orchestrator.orchestrator instead.
    
    This class now only provides deprecation warnings and forwards calls to the new orchestrator.
    """
    
    def __init__(self):
        _warn_about_deprecation(
            "LangChainService", 
            "app.infrastructure.langchain_orchestrator.orchestrator"
        )
        
        # Import the new orchestrator for forwarding
        from .langchain_orchestrator import orchestrator as _orchestrator
        self._orchestrator = _orchestrator
    
    def get_embeddings(self):
        """_Deprecated method - use LangChainOrchestrator instead_"""
        return self._orchestrator.get_embeddings()
    
    async def generate_metadata(self, title: str, content: str) -> Dict[str, Any]:
        """_Deprecated method - use LangChainOrchestrator.process_request instead_"""
        # Forward to new orchestrator
        query = f"Generate metadata for: {title}"
        result = await self._orchestrator.process_request(
            query=query,
            context=content,
            metadata_request=True
        )
        return {
            "summary": result.content,
            "tags": [],  # TODO: Extract from orchestrator metadata
            "suggested_category": "",
            "suggested_visibility": ""
        }
    
    async def convert_text_to_markdown(self, title: str, content: str) -> str:
        """_Deprecated method - use LangChainOrchestrator.process_request instead_"""
        query = f"Convert this text to well-formatted markdown: {title}"
        result = await self._orchestrator.process_request(
            query=query,
            context=content
        )
        return result.content
    
    async def generate_chat_response(self, messages: List[Dict[str, str]], context: Optional[str] = None) -> str:
        """_Deprecated method - use LangChainOrchestrator.process_request instead_"""
        # Extract the latest user message
        latest_message = next((msg for msg in reversed(messages) if msg.get("role") == "user"), {})
        query = latest_message.get("content", "")
        
        result = await self._orchestrator.process_request(
            query=query,
            context=context,
            conversation_history=messages[:-1]  # Exclude the latest message
        )
        return result.content
    
    async def generate_chat_response_stream(self, messages: List[Dict[str, str]], context: Optional[str] = None):
        """_Deprecated method - use LangChainOrchestrator.process_streaming_request instead_"""
        # Extract the latest user message
        latest_message = next((msg for msg in reversed(messages) if msg.get("role") == "user"), {})
        query = latest_message.get("content", "")
        
        async for chunk in self._orchestrator.process_streaming_request(
            query=query,
            context=context,
            conversation_history=messages[:-1]  # Exclude the latest message
        ):
            yield chunk
    
    async def generate_rag_response(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        custom_model: Optional[str] = None,
        custom_temperature: Optional[float] = None,
        query_type: str = "general",
        prompt_name: str = "rag_response",
        agentic_mode: bool = False
    ) -> str:
        """_Deprecated method - use LangChainOrchestrator.process_request instead_"""
        result = await self._orchestrator.process_request(
            query=query,
            context=context,
            conversation_history=conversation_history,
            custom_model=custom_model,
            custom_temperature=custom_temperature,
            query_type=query_type,
            agentic_mode=agentic_mode
        )
        return result.content
    
    async def generate_rag_response_stream(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        custom_model: Optional[str] = None,
        custom_temperature: Optional[float] = None,
        query_type: str = "general",
        prompt_name: str = "rag_response",
        agentic_mode: bool = False
    ):
        """_Deprecated method - use LangChainOrchestrator.process_streaming_request instead_"""
        async for chunk in self._orchestrator.process_streaming_request(
            query=query,
            context=context,
            conversation_history=conversation_history,
            custom_model=custom_model,
            custom_temperature=custom_temperature,
            query_type=query_type,
            agentic_mode=agentic_mode
        ):
            yield chunk
    
    async def generate_conversational_response_stream(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        custom_model: Optional[str] = None,
        custom_temperature: Optional[float] = None
    ):
        """_Deprecated method - use LangChainOrchestrator.process_streaming_request instead_"""
        async for chunk in self._orchestrator.process_streaming_request(
            query=query,
            context=None,
            conversation_history=conversation_history,
            custom_model=custom_model,
            custom_temperature=custom_temperature
        ):
            yield chunk


# Global deprecated instance
langchain_service = LangChainService()

# For backward compatibility, but with warnings
__all__ = ['langchain_service', 'LangChainService']