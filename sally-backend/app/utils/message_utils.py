"""
Utility functions for creating standardized Message objects
با metadata کامل و sender_type استاندارد
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from app.domain.entities import Message, SenderType, Customer, Admin
from app.core.config import settings


def create_user_message(
    conversation_id: str,
    content: str,
    user: Optional[Customer | Admin] = None,
    user_type: str = "guest",
    guest_session_id: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None
) -> Message:
    """
    ✅ ساخت پیام کاربر با sender_type استاندارد
    
    Args:
        conversation_id: شناسه گفتگو
        content: محتوای پیام
        user: کاربر (Customer یا Admin)
        user_type: نوع کاربر
        guest_session_id: شناسه جلسه مهمان
        extra_metadata: metadata اضافی
    """
    # ✅ تشخیص sender_type استاندارد
    if user:
        if isinstance(user, Admin):
            sender_type = SenderType.SUPER_ADMIN.value if user.role_name == "SuperAdmin" else SenderType.ADMIN.value
            sender_id = str(user.id)
            metadata = {
                "user_type": user_type,
                "admin_email": user.email,
                "admin_name": user.full_name,
                "admin_role": user.role_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:  # Customer
            sender_type = SenderType.CUSTOMER.value
            sender_id = str(user.id)
            metadata = {
                "user_type": user_type,
                "customer_email": user.email,
                "customer_name": user.full_name,
                "timestamp": datetime.utcnow().isoformat()
            }
    else:  # Guest
        sender_type = SenderType.GUEST.value
        sender_id = None
        metadata = {
            "user_type": "guest",
            "guest_session_id": guest_session_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # اضافه کردن metadata اضافی
    if extra_metadata:
        metadata.update(extra_metadata)
    
    return Message(
        conversation_id=conversation_id,
        content=content,
        sender_type=sender_type,
        sender_id=sender_id,
        is_failed=False,
        metadata=metadata
    )


def create_ai_message(
    conversation_id: str,
    content: str,
    rag_type: str = "simple",
    sources: Optional[List[Dict[str, Any]]] = None,
    confidence: Optional[float] = None,
    suggested_actions: Optional[List[str]] = None,
    token_usage: Optional[Dict[str, int]] = None,
    response_time: Optional[float] = None,
    is_failed: bool = False,
    failure_reason: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None
) -> Message:
    """
    ✅ ساخت پیام AI با metadata کامل
    
    Args:
        conversation_id: شناسه گفتگو
        content: محتوای پاسخ
        rag_type: نوع RAG (simple/agentic)
        sources: منابع استفاده شده
        confidence: میزان اطمینان
        suggested_actions: اقدامات پیشنهادی
        token_usage: مصرف توکن
        response_time: زمان پاسخ
        is_failed: آیا با خطا مواجه شد
        failure_reason: دلیل خطا
        extra_metadata: metadata اضافی
    """
    # ✅ ساخت metadata کامل
    model_name = settings.rag_model_loaded if rag_type == "agentic" else settings.chat_model_loaded
    temperature = 0.3 if rag_type == "agentic" else 0.7
    
    metadata = {
        "rag_type": rag_type,
        "model_name": model_name,
        "provider": "OpenAI",
        "api_base_url": settings.openai_base_url_loaded,
        "embedder_model": settings.embedder_model_loaded,
        "temperature": temperature,
        "max_tokens": 1000,
        "timestamp": datetime.utcnow().isoformat(),
        "sources": sources or [],
        "confidence": confidence,
        "suggested_actions": suggested_actions or [],
        "token_usage": token_usage or {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None
        },
        "response_time": response_time
    }
    
    # اضافه کردن metadata اضافی
    if extra_metadata:
        metadata.update(extra_metadata)
    
    # اگر خطا داشتیم، اطلاعات خطا را اضافه کنیم
    if is_failed and failure_reason:
        metadata["error_type"] = type(failure_reason).__name__ if isinstance(failure_reason, Exception) else "Unknown"
        metadata["error_message"] = str(failure_reason)
    
    return Message(
        conversation_id=conversation_id,
        content=content,
        sender_type=SenderType.AI.value,
        sender_id=None,
        is_failed=is_failed,
        failure_reason=failure_reason,
        metadata=metadata
    )


def create_streaming_ai_message_placeholder(
    conversation_id: str,
    rag_type: str = "simple"
) -> Message:
    """
    ✅ ساخت پیام placeholder برای streaming
    """
    return Message(
        conversation_id=conversation_id,
        content="",  # Will be filled during streaming
        sender_type=SenderType.AI.value,
        sender_id=None,
        is_failed=False,
        metadata={
            "streaming": True,
            "rag_type": rag_type,
            "model_name": settings.rag_model_loaded if rag_type == "agentic" else settings.chat_model_loaded,
            "provider": "OpenAI",
            "start_time": datetime.utcnow().isoformat()
        }
    )


def update_ai_message_after_streaming(
    message: Message,
    full_content: str,
    sources: Optional[List[Dict[str, Any]]] = None,
    confidence: Optional[float] = None,
    suggested_actions: Optional[List[str]] = None,
    token_usage: Optional[Dict[str, int]] = None,
    response_time: Optional[float] = None
) -> None:
    """
    ✅ به‌روزرسانی پیام AI بعد از streaming
    """
    message.content = full_content
    
    if message.metadata:
        message.metadata["end_time"] = datetime.utcnow().isoformat()
        message.metadata["sources"] = sources or []
        message.metadata["confidence"] = confidence
        message.metadata["suggested_actions"] = suggested_actions or []
        message.metadata["token_usage"] = token_usage or {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None
        }
        message.metadata["response_time"] = response_time
        message.metadata["streaming_completed"] = True

