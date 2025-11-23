from typing import Optional, Dict, Any, List, Union, AsyncGenerator, Tuple
import logging
import asyncio
from datetime import datetime, timezone
from bson import ObjectId

from app.domain.entities import (
    Conversation, Message, Customer, Admin, SenderType, MessageRating
)
# نکته: برای جلوگیری از Circular Import احتمالی، سرویس‌ها را داخل متدها ایمپورت می‌کنیم
# اما تنظیمات و لاگر مشکلی ندارند
from app.core.config import settings
from app.core.logging_config import get_logger
from app.utils.query_analyzer import query_analyzer

logger = get_logger(__name__)


async def load_conversation_history(conversation_id: str, max_messages: int = 10) -> List[Dict[str, str]]:
    conversation_history = []
    try:
        if not ObjectId.is_valid(conversation_id):
            return []
            
        messages = await Message.find(
            Message.conversation_id == str(ObjectId(conversation_id))
        ).sort(+Message.created_at).limit(max_messages).to_list()
        
        for msg in messages:
            conversation_history.append({
                "role": "user" if msg.sender_type in [e.value for e in SenderType if e != SenderType.AI] else "assistant",
                "content": msg.content
            })
    except Exception as e:
        logger.warning(f"Could not load conversation history: {e}", exc_info=True)
    return conversation_history


class ChatUseCases:
    
    # ======================================================================================
    # ✅ متد مرکزی اجرای RAG (مشترک بین ادمین و مشتری)
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
        هسته مرکزی پردازش RAG که خروجی را استریم می‌کند.
        """
        response_start_time = datetime.utcnow()
        full_response = ""
        sources = []
        confidence = 0.5
        
        try:
            logger.debug(f"🔄 Executing RAG Pipeline | Type: {rag_type} | Public Only: {is_public_only}")
            
            # 1. Retrieve documents
            relevant_docs = await rag_service.retrieve_relevant_documents(
                query, is_public_only=is_public_only
            )
            
            if relevant_docs:
                # 2. Format sources and calculate confidence
                sources = rag_service._format_sources_markdown(relevant_docs)
                
                # محاسبه اطمینان (Confidence)
                query_type_analysis = query_analysis.get('analysis', {}).get('type', {})
                confidence_analysis = rag_service._calculate_advanced_confidence(
                    query=query,
                    retrieved_docs=relevant_docs,
                    query_type=query_type_analysis.get('query_type', 'general')
                )
                confidence = confidence_analysis['confidence_score']
                
                # ارسال منابع به کلاینت
                yield {"type": "sources", "sources": sources, "confidence": confidence}
                
                # 3. Build context
                context_parts = [
                    f"=== Document {i} ===\nTitle: {doc['title']}\nScore: {doc.get('score', 0):.2f}\nContent:\n{doc['content']}\n---"
                    for i, doc in enumerate(relevant_docs[:15], 1)
                ]
                context_text = "\n".join(context_parts)
                
                # 4. Generate response via Orchestrator
                from app.infrastructure.langchain_orchestrator import orchestrator
                
                # انتخاب پرامپت مناسب
                prompt_name = "agentic_rag_response" if rag_type == "agentic" else "simple_rag_response"
                final_model = custom_model or conversation.model_name or settings.rag_model_loaded
                final_temp = custom_temperature if custom_temperature is not None else conversation.temperature

                logger.info(f"🤖 LLM Request | Prompt: {prompt_name} | Model: {final_model}")

                # استفاده از روش استریم برای جلوگیری از چسبیدن کلمات
                async for chunk in orchestrator.process_streaming_request(
                    query=query,
                    context=context_text,
                    conversation_history=conversation_history,
                    custom_prompt=prompt_name,
                    custom_model=final_model,
                    custom_temperature=final_temp
                ):
                    full_response += chunk
                    yield {"type": "chunk", "content": chunk}
            else:
                full_response = "متأسفانه اطلاعات مرتبطی در پایگاه دانش یافت نشد."
                yield {"type": "chunk", "content": full_response}
            
            # 5. Save AI message
            response_time_seconds = (datetime.utcnow() - response_start_time).total_seconds()
            
            ai_message = Message(
                conversation_id=str(conversation.id),
                content=full_response,
                sender_type=SenderType.AI.value,
                response_time=response_time_seconds,
                metadata={
                    "sources": sources,
                    "confidence": confidence,
                    "rag_type": rag_type,
                    "model": custom_model or settings.rag_model_loaded,
                    "response_time": response_time_seconds,
                    **query_analysis.get('analysis', {})
                }
            )
            await ai_message.insert()
            
            # 6. Send complete event
            yield {
                "type": "complete",
                "message_id": str(ai_message.id),
                "full_response": full_response,
                "confidence": confidence,
                "rag_type": rag_type
            }

        except Exception as e:
            logger.error(f"❌ RAG Pipeline Error: {e}", exc_info=True)
            error_msg = f"خطا در پردازش درخواست: {str(e)}"
            
            ai_message = Message(
                conversation_id=str(conversation.id),
                content=error_msg,
                sender_type=SenderType.AI.value,
                is_failed=True,
                failure_reason=str(e)
            )
            await ai_message.insert()
            yield {"type": "error", "message": str(e), "message_id": str(ai_message.id)}

    # ======================================================================================
    # ADMIN METHODS
    # ======================================================================================

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
        پردازش پیام ادمین (استریمینگ)
        """
        # 1. Conversation Management
        if conversation_id:
            conversation = await Conversation.get(ObjectId(conversation_id))
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            # Update settings if changed
            updated = False
            if model and conversation.model_name != model:
                conversation.model_name = model
                updated = True
            if conversation.rag_type != rag_type:
                conversation.rag_type = rag_type
                updated = True
            if updated:
                await conversation.save()
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

        # 2. History & Analysis
        conversation_history = await load_conversation_history(str(conversation.id))
        history_for_cache = tuple((msg['role'], msg['content']) for msg in conversation_history)
        query_analysis_result = await query_analyzer.analyze(content, history_for_cache)
        query_analysis = query_analysis_result.model_dump()

        # 3. Save User Message
        sender_type = SenderType.SUPER_ADMIN.value if getattr(admin, 'role_name', '') == "SuperAdmin" else SenderType.ADMIN.value
        user_message = Message(
            conversation_id=str(conversation.id),
            content=content,
            sender_type=sender_type,
            sender_id=str(admin.id),
            metadata={"rag_type": rag_type, **query_analysis.get('analysis', {})}
        )
        await user_message.insert()
        
        yield {"type": "init", "conversation_id": str(conversation.id), "message_id": str(user_message.id)}

        # 4. Check for Conversational Bypass (No RAG needed)
        if not query_analysis.get('needs_rag', True):
            logger.debug("💬 Bypass RAG -> Conversational Response")
            from app.infrastructure.langchain_orchestrator import orchestrator
            
            result = await orchestrator.process_request(
                query=content,
                conversation_history=conversation_history,
                custom_prompt="basic_response",
                custom_model=model,
                custom_temperature=temperature
            )
            
            ai_message = Message(
                conversation_id=str(conversation.id),
                content=result.content,
                sender_type=SenderType.AI.value,
                metadata={"rag_type": "conversational"}
            )
            await ai_message.insert()
            
            yield {"type": "chunk", "content": result.content}
            yield {"type": "complete", "message_id": str(ai_message.id), "full_response": result.content, "confidence": 1.0}
            return

        # 5. Execute RAG Pipeline
        from app.services.rag_service import get_rag_service
        rag_service = get_rag_service(admin, rag_type)
        
        async for event in ChatUseCases._execute_rag_pipeline_stream(
            query=content,
            conversation=conversation,
            user_message=user_message,
            rag_service=rag_service,
            query_analysis=query_analysis,
            conversation_history=conversation_history,
            is_public_only=False, # Admin sees all
            rag_type=rag_type,
            custom_model=model,
            custom_temperature=temperature
        ):
            yield event

    @staticmethod
    async def send_admin_message(
        content: str,
        admin: Admin,
        conversation_id: Optional[str] = None,
        rag_type: str = "simple",
        model: Optional[str] = None,
        temperature: Optional[float] = 0.7
    ) -> Dict[str, Any]:
        """Wrapper for non-streaming admin chat."""
        full_response = ""
        sources = []
        confidence = 0.0
        message_id = ""
        conv_id = conversation_id

        async for event in ChatUseCases.send_admin_message_stream(
            content, admin, conversation_id, rag_type, model, temperature
        ):
            if event["type"] == "init":
                conv_id = event["conversation_id"]
            elif event["type"] == "chunk":
                full_response += event.get("content", "")
            elif event["type"] == "sources":
                sources = event.get("sources", [])
                confidence = event.get("confidence", 0.0)
            elif event["type"] == "complete":
                message_id = event["message_id"]
                if "full_response" in event:
                    full_response = event["full_response"]

        return {
            "conversation_id": conv_id,
            "message": full_response,
            "sources": sources,
            "confidence": confidence,
            "message_id": message_id
        }

    # ======================================================================================
    # CUSTOMER / GUEST METHODS
    # ======================================================================================

    @staticmethod
    async def send_message_stream(
        content: str,
        user: Optional[Union[Customer, Admin]] = None,
        user_type: str = "guest",
        conversation_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        پردازش پیام مشتری/مهمان (استریمینگ)
        """
        rag_type = "simple" # Customers always use simple RAG (or detailed via flag, but handled as simple logic)
        actual_model = model or settings.chat_model_loaded
        
        # 1. Conversation Management
        if conversation_id:
            conversation = await Conversation.get(ObjectId(conversation_id))
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
            # Update model if explicitly requested (though usually restricted for customers)
            if model and conversation.model_name != model:
                conversation.model_name = model
                await conversation.save()
        else:
            title = content[:50] + "..."
            conversation = Conversation(
                customer_id=str(user.id) if user_type == "Customer" else None,
                guest_session_id=guest_session_id if user_type == "guest" else None,
                title=title,
                rag_type=rag_type,
                model_name=actual_model,
                temperature=temperature or 0.7
            )
            await conversation.insert()

        # 2. History & Analysis
        conversation_history = await load_conversation_history(str(conversation.id))
        history_for_cache = tuple((msg['role'], msg['content']) for msg in conversation_history)
        query_analysis_result = await query_analyzer.analyze(content, history_for_cache)
        query_analysis = query_analysis_result.model_dump()

        # 3. Save User Message
        sender_type_map = {"Customer": SenderType.CUSTOMER, "Admin": SenderType.ADMIN, "guest": SenderType.GUEST}
        sender_type = sender_type_map.get(user_type, SenderType.GUEST).value
        
        user_message = Message(
            conversation_id=str(conversation.id),
            content=content,
            sender_type=sender_type,
            sender_id=str(user.id) if user else None,
            metadata={"rag_type": rag_type, **query_analysis.get('analysis', {})}
        )
        await user_message.insert()

        yield {"type": "init", "conversation_id": str(conversation.id), "message_id": str(user_message.id)}

        # 4. Check for Conversational Bypass
        if not query_analysis.get('needs_rag', True):
            from app.infrastructure.langchain_orchestrator import orchestrator
            result = await orchestrator.process_request(
                query=content,
                conversation_history=conversation_history,
                custom_prompt="basic_response",
                custom_model=actual_model
            )
            
            ai_message = Message(
                conversation_id=str(conversation.id),
                content=result.content,
                sender_type=SenderType.AI.value,
                metadata={"rag_type": "conversational"}
            )
            await ai_message.insert()
            
            yield {"type": "chunk", "content": result.content}
            yield {"type": "complete", "message_id": str(ai_message.id), "full_response": result.content, "confidence": 1.0}
            return

        # 5. Execute RAG Pipeline (using central method)
        from app.services.rag_service import get_rag_service
        # For guests/customers, we rely on the service to filter PUBLIC articles only
        rag_service = get_rag_service(user) 
        
        async for event in ChatUseCases._execute_rag_pipeline_stream(
            query=content,
            conversation=conversation,
            user_message=user_message,
            rag_service=rag_service,
            query_analysis=query_analysis,
            conversation_history=conversation_history,
            is_public_only=True, # 🔥 Critical: Customers only see public docs
            rag_type=rag_type,
            custom_model=actual_model,
            custom_temperature=temperature
        ):
            yield event

    @staticmethod
    async def send_message(
        content: str,
        user: Optional[Union[Customer, Admin]] = None,
        user_type: str = "guest",
        conversation_id: Optional[str] = None,
        guest_session_id: Optional[str] = None,
        rag_type: str = "simple",
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """Wrapper for non-streaming customer/guest chat."""
        full_response = ""
        sources = []
        confidence = 0.0
        message_id = ""
        conv_id = conversation_id

        async for event in ChatUseCases.send_message_stream(
            content, user, user_type, conversation_id, guest_session_id, model, temperature
        ):
            if event["type"] == "init":
                conv_id = event["conversation_id"]
            elif event["type"] == "chunk":
                full_response += event.get("content", "")
            elif event["type"] == "sources":
                sources = event.get("sources", [])
                confidence = event.get("confidence", 0.0)
            elif event["type"] == "complete":
                message_id = event["message_id"]
                if "full_response" in event:
                    full_response = event["full_response"]

        return {
            "conversation_id": conv_id,
            "message": full_response,
            "sources": sources,
            "confidence": confidence,
            "message_id": message_id
        }

    # ======================================================================================
    # HELPER METHODS (GETTERS)
    # ======================================================================================

    @staticmethod
    async def get_conversation_history(
        conversation_id: str,
        user_type: str = "guest",
        user_id: Optional[str] = None,
        guest_session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get conversation message history."""
        
        if not ObjectId.is_valid(conversation_id):
            raise ValueError("Invalid conversation ID")

        conversation = await Conversation.get(ObjectId(conversation_id))
        if not conversation:
            raise ValueError("Conversation not found")

        # Check access permissions
        if user_type == "Customer" and user_id:
            if conversation.customer_id != user_id:
                raise ValueError("Access denied")
        elif user_type == "Admin" and user_id:
            if conversation.admin_id != user_id:
                raise ValueError("Access denied")
        else:
            # Guest check
            if not conversation.guest_session_id:
                 raise ValueError("Access denied")
            if guest_session_id and conversation.guest_session_id != guest_session_id:
                raise ValueError("Access denied")

        messages = await Message.find(
            Message.conversation_id == str(conversation.id)
        ).sort(Message.created_at).to_list()

        return [
            {
                "id": str(msg.id),
                "content": msg.content,
                "sender_type": msg.sender_type,
                "sender_id": msg.sender_id,
                "is_failed": msg.is_failed,
                "failure_reason": msg.failure_reason,
                "rating": msg.rating.dict() if msg.rating else None,
                "created_at": msg.created_at.isoformat(),
                "metadata": {
                    **(msg.metadata or {}),
                    "rag_type": msg.metadata.get("rag_type") if msg.metadata else conversation.rag_type
                }
            }
            for msg in messages
        ]

    @staticmethod
    async def get_user_conversations(customer: Customer) -> List[Dict[str, Any]]:
        conversations = await Conversation.find(
            Conversation.customer_id == str(customer.id)
        ).sort(-Conversation.updated_at).to_list()

        return [ChatUseCases._format_conversation_list_item(c) for c in conversations]

    @staticmethod
    async def get_admin_conversations(admin: Admin) -> List[Dict[str, Any]]:
        conversations = await Conversation.find(
            Conversation.admin_id == str(admin.id)
        ).sort(-Conversation.updated_at).to_list()

        return [ChatUseCases._format_conversation_list_item(c) for c in conversations]
    
    @staticmethod
    def _format_conversation_list_item(conv: Conversation) -> Dict[str, Any]:
        return {
            "id": str(conv.id),
            "title": conv.title,
            "tags": conv.tags,
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.updated_at.isoformat(),
            "type": "Agentic" if conv.rag_type == "agentic" else "Simple RAG",
            "rag_type": conv.rag_type,
            "model_name": conv.model_name,
            "temperature": conv.temperature
        }

    @staticmethod
    async def get_message_rating_stats(conversation_id: str) -> Dict[str, Any]:
        try:
            messages = await Message.find(
                Message.conversation_id == conversation_id,
                Message.sender_type == "AI",
                Message.rating != None
            ).to_list()

            if not messages:
                return {"total_rated_messages": 0, "average_rating": 0.0, "rating_distribution": {}, "total_ratings": 0}

            ratings = [msg.rating.rating for msg in messages if msg.rating]
            rating_counts = {i: ratings.count(i) for i in range(1, 6)}

            return {
                "total_rated_messages": len(messages),
                "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0.0,
                "rating_distribution": rating_counts,
                "total_ratings": len(ratings)
            }
        except Exception as e:
            logger.error(f"Error getting rating stats: {e}")
            return {"error": str(e)}

    @staticmethod
    async def generate_conversation_title_and_tags(conversation_id: str) -> Dict[str, Any]:
        try:
            if not ObjectId.is_valid(conversation_id):
                 return {"error": "Invalid conversation ID"}
            
            conversation = await Conversation.get(ObjectId(conversation_id))
            if not conversation:
                return {"error": "Conversation not found"}

            messages = await Message.find(Message.conversation_id == conversation_id).sort(+Message.created_at).limit(10).to_list()
            message_texts = [msg.content for msg in messages if msg.content]
            
            if not message_texts:
                return {"error": "No content"}

            combined_text = " ".join(message_texts[-5:])
            title = query_analyzer.generate_conversation_title(combined_text, max_length=60)

            # Simple keyword matching for tags
            tags = []
            text_lower = combined_text.lower()
            if any(x in text_lower for x in ["مشکل", "ارور", "خطا"]): tags.append("پشتیبانی فنی")
            if any(x in text_lower for x in ["قیمت", "خرید", "هزینه"]): tags.append("فروش")
            if any(x in text_lower for x in ["چطور", "آموزش", "راهنما"]): tags.append("آموزش")
            if not tags: tags.append("عمومی")

            conversation.title = title
            conversation.tags = tags
            await conversation.save()

            return {"title": title, "tags": tags}
        except Exception as e:
            logger.error(f"Error generating title: {e}")
            return {"error": str(e)}