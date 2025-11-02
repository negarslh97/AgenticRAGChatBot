# chat_use_cases.py (نسخه نهایی و Refactor شده)

from typing import Optional, Dict, Any, List, Union, AsyncGenerator, Tuple
import uuid
import logging
import asyncio
from datetime import datetime

from app.domain.entities import (
    Conversation, Message, Customer, Admin, GuestSession, UnansweredQuestion,
    MessageRating, SenderType
)
from app.services.rag_service import get_rag_service
from app.core.config import settings
from app.core.logging_config import get_logger
from app.utils.query_analyzer import query_analyzer, QueryAnalysisResult

logger = get_logger(__name__)


async def load_conversation_history(conversation_id: str, max_messages: int = 10) -> List[Dict[str, str]]:
    # این تابع بدون تغییر باقی می‌ماند
    conversation_history = []
    try:
        from bson import ObjectId
        messages = await Message.find(
            Message.conversation_id == str(ObjectId(conversation_id))
        ).sort(+Message.created_at).limit(max_messages).to_list()
        
        for msg in messages:
            conversation_history.append({
                "role": "user" if msg.sender_type in [e.value for e in SenderType if e != SenderType.AI] else "assistant",
                "content": msg.content
            })
        logger.info(f"Loaded {len(conversation_history)} messages from conversation history (max: {max_messages})")
    except Exception as e:
        logger.warning(f"Could not load conversation history: {e}", exc_info=True)
    return conversation_history


class ChatUseCases:
    
    # ======================================================================================
    # ✅ متد جدید و مرکزی برای اجرای پایپ‌لاین RAG
    # ======================================================================================
    @staticmethod
    async def _execute_rag_pipeline_stream(
        query: str,
        conversation: Conversation,
        user_message: Message,
        rag_service: Any,
        query_analysis: dict,
        conversation_history: list,
        is_public_only: bool,
        rag_type: str,
        custom_model: Optional[str] = None,
        custom_temperature: Optional[float] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        این متد خصوصی، هسته اصلی و مشترک پایپ‌لاین RAG را برای هر دو نوع کاربر (ادمین و عادی) اجرا می‌کند.
        این کار از تکرار کد جلوگیری می‌کند.
        """
        response_start_time = datetime.utcnow()
        full_response = ""
        sources = []
        confidence = 0.5
        
        try:
            logger.info("Proceeding with RAG pipeline - Factual query detected")
            
            # 1. Retrieve documents
            relevant_docs = await rag_service.retrieve_relevant_documents(
                query, is_public_only=is_public_only
            )
            
            if relevant_docs:
                # 2. Format sources and calculate confidence
                sources = rag_service._format_sources_markdown(relevant_docs)
                query_type_analysis = query_analysis['analysis']['type']
                confidence_analysis = rag_service._calculate_advanced_confidence(
                    query=query,
                    retrieved_docs=relevant_docs,
                    query_type=query_type_analysis['query_type']
                )
                confidence = confidence_analysis['confidence_score']
                logger.info(f"Confidence: {confidence:.2f} ({confidence_analysis['confidence_level']})")
                
                yield {"type": "sources", "sources": sources, "confidence": confidence}
                
                # 3. Build context for LLM
                context_parts = [
                    f"=== بخش {i} ===\nعنوان: {doc['title']}\nمسیر: {doc.get('path', 'N/A')}\nامتیاز: {doc.get('score', 0):.2f}\n\nمحتوا:\n{doc['content']}\n\n---\n"
                    for i, doc in enumerate(relevant_docs[:20], 1)
                ]
                context_text = "\n".join(context_parts)
                
                # 4. Generate response from LLM
                from app.infrastructure.langchain_utils import langchain_service
                prompt_name = "simple_rag_response" if rag_type == "simple" else "rag_response"
                logger.info(f"Using prompt: {prompt_name} for rag_type: {rag_type}")
                
                async for chunk in langchain_service.generate_rag_response_stream(
                    query, 
                    context_text,
                    conversation_history=conversation_history,
                    custom_model=custom_model,
                    custom_temperature=custom_temperature,
                    query_type=query_type_analysis['query_type'],
                    prompt_name=prompt_name
                ):
                    full_response += chunk
                    yield {"type": "chunk", "content": chunk}
            else:
                full_response = "متأسفانه اطلاعات مرتبط یافت نشد."
                yield {"type": "chunk", "content": full_response}
            
            # 5. Save AI message
            response_time_seconds = (datetime.utcnow() - response_start_time).total_seconds()
            can_get_more_details = rag_type == "simple" and bool(sources)
            
            ai_message = Message(
                conversation_id=str(conversation.id),
                content=full_response,
                sender_type=SenderType.AI.value,
                response_time=response_time_seconds,
                metadata={
                    "sources": sources,
                    "confidence": confidence,
                    "rag_type": rag_type,
                    "streaming": True,
                    "model": custom_model or settings.rag_model_loaded,
                    "temperature": custom_temperature,
                    "response_time": response_time_seconds,
                    "can_get_more_details": can_get_more_details,
                    **query_analysis['analysis'] # افزودن جزئیات تحلیل
                }
            )
            await ai_message.insert()
            logger.info(f"Response time: {response_time_seconds:.2f} seconds")
            
            # 6. Send complete event
            yield {
                "type": "complete",
                "message_id": str(ai_message.id),
                "full_response": full_response,
                "confidence": confidence,
                "can_get_more_details": can_get_more_details,
                "rag_type": rag_type
            }

        except Exception as e:
            logger.error(f"RAG pipeline error: {e}", exc_info=True)
            error_msg = f"خطا: {str(e)}"
            response_time_seconds = (datetime.utcnow() - response_start_time).total_seconds()

            ai_message = Message(
                conversation_id=str(conversation.id),
                content=error_msg,
                sender_type=SenderType.AI.value,
                is_failed=True,
                failure_reason=str(e),
                response_time=response_time_seconds,
                metadata={"streaming": True, "rag_type": rag_type}
            )
            await ai_message.insert()
            yield {"type": "error", "message": str(e), "message_id": str(ai_message.id)}

    @staticmethod
    async def send_admin_message_stream(
        content: str,
        admin: Admin,
        conversation_id: Optional[str] = None,
        rag_type: str = "simple",
        model: Optional[str] = None,
        temperature: Optional[float] = 0.7
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        پردازش پیام ادمین با پشتیبانی از استریمینگ (نسخه تمیز و Refactor شده).
        """
        temperature = 0.2 if temperature > 0.3 else temperature
        logger.info(f"Starting admin streaming chat (Model: {model or 'default'}, Temp: {temperature})")

        # 1. Get or create conversation
        if conversation_id:
            conversation = await Conversation.get(conversation_id)
        else:
            smart_title = query_analyzer.generate_conversation_title(content, max_length=60)
            conversation = Conversation(
                admin_id=str(admin.id),
                title=smart_title,
                rag_type=rag_type,
                model_name=model or settings.rag_model_loaded,
                temperature=temperature
            )
            await conversation.insert()
            logger.info(f"Created admin conversation: {conversation.id} - '{smart_title}'")

        # 2. Load history and analyze query
        conversation_history = await load_conversation_history(str(conversation.id))
        history_for_cache = tuple((msg['role'], msg['content']) for msg in conversation_history)
        query_analysis_result = await query_analyzer.analyze(content, history_for_cache)
        query_analysis = query_analysis_result.model_dump()
        logger.info(f"Query intent: {query_analysis['intent']} (needs_rag: {query_analysis['needs_rag']})")
        
        # 3. Handle conversational bypass
        if not query_analysis['needs_rag']:
            logger.info("💬 Conversational query detected - bypassing RAG and generating a conversational response.")

            # 1. Save user message first
            sender_type = SenderType.SUPER_ADMIN.value if admin.role_name == "SuperAdmin" else SenderType.ADMIN.value
            user_message = Message(
                conversation_id=str(conversation.id),
                content=content,
                sender_type=sender_type,
                sender_id=str(admin.id)
            )
            await user_message.insert()

            # 2. Send init event to frontend
            yield {
                "type": "init",
                "conversation_id": str(conversation.id),
                "message_id": str(user_message.id)
            }

            # 3. Generate conversational response using LLM
            from app.infrastructure.langchain_utils import langchain_service
            full_response = ""
            
            # ما از تابع استریم مکالمه‌ای استفاده می‌کنیم
            async for chunk in langchain_service.generate_conversational_response_stream(
                query=content,
                conversation_history=conversation_history, # ارسال تاریخچه برای حفظ حافظه
                custom_model=model,
                custom_temperature=0.7 # دمای بالاتر برای خلاقیت بیشتر در مکالمه
            ):
                full_response += chunk
                yield {
                    "type": "chunk",
                    "content": chunk
                }

            # 4. Save AI's final response to the database
            ai_message = Message(
                conversation_id=str(conversation.id),
                sender_type=SenderType.AI.value,
                content=full_response,
                metadata={"rag_type": "conversational", "model": model or settings.chat_model_loaded}
            )
            await ai_message.insert()

            # 5. Send complete event
            yield {
                "type": "complete",
                "message_id": str(ai_message.id),
                "full_response": full_response,
                "sources": [],
                "confidence": 1.0, # اطمینان در پاسخ محاوره‌ای بالاست
                "routing": "conversational"
            }
            return # End the function here

        # 4. Save user message
        sender_type = SenderType.SUPER_ADMIN.value if admin.role_name == "SuperAdmin" else SenderType.ADMIN.value
        user_message = Message(
            conversation_id=str(conversation.id),
            content=content,
            sender_type=sender_type,
            sender_id=str(admin.id),
            metadata={
                "rag_type": rag_type,
                **query_analysis['analysis']
            }
        )
        await user_message.insert()
        
        # 5. Send init event
        yield {"type": "init", "conversation_id": str(conversation.id), "message_id": str(user_message.id)}
        
        # 6. Execute central RAG pipeline
        rag_service = get_rag_service(admin, rag_type)
        async for event in ChatUseCases._execute_rag_pipeline_stream(
            query=content,
            conversation=conversation,
            user_message=user_message,
            rag_service=rag_service,
            query_analysis=query_analysis,
            conversation_history=conversation_history,
            is_public_only=False, # ادمین به همه اسناد دسترسی دارد
            rag_type=rag_type,
            custom_model=model,
            custom_temperature=temperature
        ):
            yield event

    # ======================================================================================
    # ✅ متد send_message_stream نیز برای استفاده از متد مرکزی بازنویسی می‌شود
    # ======================================================================================
    @staticmethod
    async def send_message_stream(
        content: str,
        user: Optional[Union[Customer, Admin]] = None,
        user_type: str = "guest",
        conversation_id: Optional[str] = None,
        guest_session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        پردازش پیام کاربر عادی/مهمان با پشتیبانی از استریمینگ (نسخه تمیز و Refactor شده).
        """
        logger.info(f"Starting streaming chat for {user_type}")
        rag_type = "simple" # کاربران عادی همیشه از simple RAG استفاده می‌کنند

        # 1. Get or create conversation
        if conversation_id:
            conversation = await Conversation.get(conversation_id)
        else:
            title = content[:50] + "..."
            user_id = str(user.id) if user else None
            conversation = Conversation(
                customer_id=user_id if user_type == "Customer" else None,
                guest_session_id=guest_session_id if user_type == "guest" else None,
                title=title, rag_type=rag_type
            )
            await conversation.insert()
        
        # 2. Load history and analyze query (با رفع باگ)
        conversation_history = await load_conversation_history(str(conversation.id))
        history_for_cache = tuple((msg['role'], msg['content']) for msg in conversation_history)
        query_analysis_result = await query_analyzer.analyze(content, history_for_cache)
        query_analysis = query_analysis_result.model_dump()
        logger.info(f"Query intent: {query_analysis['intent']} (needs_rag: {query_analysis['needs_rag']})")

        # 3. Handle conversational bypass
        if not query_analysis['needs_rag']:
            logger.info("💬 Conversational query detected - bypassing RAG and generating a conversational response.")

            # 1. Save user message first
            sender_id = str(user.id) if user else None
            sender_type_map = {"Customer": SenderType.CUSTOMER, "Admin": SenderType.ADMIN, "guest": SenderType.GUEST}
            sender_type = sender_type_map.get(user_type, SenderType.GUEST).value
            
            user_message = Message(
                conversation_id=str(conversation.id),
                content=content,
                sender_type=sender_type,
                sender_id=sender_id
            )
            await user_message.insert()

            # 2. Send init event to frontend
            yield {
                "type": "init",
                "conversation_id": str(conversation.id),
                "message_id": str(user_message.id)
            }

            # 3. Generate conversational response using LLM
            from app.infrastructure.langchain_utils import langchain_service
            full_response = ""
            
            async for chunk in langchain_service.generate_conversational_response_stream(
                query=content,
                conversation_history=conversation_history, # ارسال تاریخچه برای حفظ حافظه
                custom_model=settings.chat_model_loaded,
                custom_temperature=0.7
            ):
                full_response += chunk
                yield {
                    "type": "chunk",
                    "content": chunk
                }

            # 4. Save AI's final response to the database
            ai_message = Message(
                conversation_id=str(conversation.id),
                sender_type=SenderType.AI.value,
                content=full_response,
                metadata={"rag_type": "conversational", "model": settings.chat_model_loaded}
            )
            await ai_message.insert()

            # 5. Send complete event
            yield {
                "type": "complete",
                "message_id": str(ai_message.id),
                "full_response": full_response,
                "sources": [],
                "confidence": 1.0,
                "routing": "conversational"
            }
            return # End the function here

        # 4. Save user message
        sender_id = str(user.id) if user else None
        sender_type_map = {"Customer": SenderType.CUSTOMER, "Admin": SenderType.ADMIN, "guest": SenderType.GUEST}
        sender_type = sender_type_map.get(user_type, SenderType.GUEST).value
        
        user_message = Message(
            conversation_id=str(conversation.id),
            content=content,
            sender_type=sender_type,
            sender_id=sender_id,
            metadata={"rag_type": rag_type, **query_analysis['analysis']}
        )
        await user_message.insert()

        # 5. Send init event
        yield {"type": "init", "conversation_id": str(conversation.id), "message_id": str(user_message.id)}

        # 6. Execute central RAG pipeline
        rag_service = get_rag_service(user, rag_type)
        async for event in ChatUseCases._execute_rag_pipeline_stream(
            query=content,
            conversation=conversation,
            user_message=user_message,
            rag_service=rag_service,
            query_analysis=query_analysis,
            conversation_history=conversation_history,
            is_public_only=(not user), # کاربران مهمان فقط اسناد عمومی را می‌بینند
            rag_type=rag_type
        ):
            yield event

    @staticmethod
    async def get_conversation_history(
        conversation_id: str,
        user_type: str = "guest",
        user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get conversation message history."""

        from bson import ObjectId
        conversation = await Conversation.get(ObjectId(conversation_id))
        if not conversation:
            logger.info(f"Conversation not found: {conversation_id}")
            raise ValueError("Conversation not found")

        # Check access permissions
        if user_type == "Customer" and user_id:
            # For authenticated customers, allow access to conversations
            # This allows customers to see conversations in the chat interface
            pass
        elif user_type == "Admin" and user_id:
            # Admins can access any conversation
            pass
        else:
            # For guests, allow access to guest conversations only if guest_session_id matches
            if not conversation.guest_session_id:
                raise ValueError("Access denied")
            if guest_session_id and conversation.guest_session_id != guest_session_id:
                raise ValueError("Access denied - guest session ID mismatch")

        # Get messages for this conversation
        messages = await Message.find(
            Message.conversation_id == str(conversation.id)
        ).sort(Message.created_at).to_list()

        logger.info(f"Found {len(messages)} messages for conversation {conversation_id}")

        result = [
            {
                "id": str(msg.id),
                "content": msg.content,
                "sender_type": msg.sender_type,
                "sender_id": msg.sender_id,
                "is_failed": msg.is_failed,
                "failure_reason": msg.failure_reason,
                "rating": msg.rating.dict() if msg.rating else None,
                "created_at": msg.created_at.isoformat(),
                "metadata": msg.metadata
            }
            for msg in messages
        ]

        logger.info(f"Returning {len(result)} messages for conversation {conversation_id}")
        logger.info(f"Message details: {result}")

        return result

    @staticmethod
    async def get_user_conversations(customer: Customer) -> List[Dict[str, Any]]:
        """Get customer's conversation list."""
        logger.info(f"Getting conversations for customer: {customer.id}")
        conversations = await Conversation.find(
            Conversation.customer_id == str(customer.id)
        ).sort(-Conversation.updated_at).to_list()

        logger.info(f"Found {len(conversations)} conversations for customer {customer.id}")

        return [
            {
                "id": str(conv.id),
                "title": conv.title,
                "tags": conv.tags,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat()
            }
            for conv in conversations
        ]

    @staticmethod
    async def get_admin_conversations(admin: Admin) -> List[Dict[str, Any]]:
        """Get admin's conversation list."""
        conversations = await Conversation.find(
            Conversation.admin_id == str(admin.id)
        ).sort(-Conversation.updated_at).to_list()

        return [
            {
                "id": str(conv.id),
                "title": conv.title,
                "tags": conv.tags,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat()
            }
            for conv in conversations
        ]

    @staticmethod
    async def get_message_rating_stats(conversation_id: str) -> Dict[str, Any]:
        """Get rating statistics for messages in a conversation."""
        try:
            from bson import ObjectId

            # Get all messages in the conversation
            messages = await Message.find(
                Message.conversation_id == conversation_id,
                Message.sender_type == "AI",
                Message.rating != None
            ).to_list()

            if not messages:
                return {
                    "total_rated_messages": 0,
                    "average_rating": 0.0,
                    "rating_distribution": {},
                    "total_ratings": 0
                }

            ratings = [msg.rating.rating for msg in messages if msg.rating]
            rating_counts = {}

            for rating in range(1, 6):
                rating_counts[rating] = ratings.count(rating)

            return {
                "total_rated_messages": len(messages),
                "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0.0,
                "rating_distribution": rating_counts,
                "total_ratings": len(ratings)
            }

        except Exception as e:
            logger.error(f"Error getting rating stats: {e}")
            return {
                "total_rated_messages": 0,
                "average_rating": 0.0,
                "rating_distribution": {},
                "total_ratings": 0,
                "error": str(e)
            }