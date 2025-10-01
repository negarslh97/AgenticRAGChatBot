from typing import Optional, Dict, Any, List, Union, AsyncGenerator
import uuid
import logging
import asyncio
from datetime import datetime

from app.domain.entities import (
    Conversation, Message, Customer, Admin, GuestSession, UnansweredQuestion,
    MessageRating
)
from app.infrastructure.rag_service import get_rag_service
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Debug logging for ChatPage RTL issues
logger.info("=== CHATPAGE RTL DEBUG LOG ===")
logger.info("ISSUES IDENTIFIED:")
logger.info("1. Main content margin classes (line 182): mr-80/mr-0 should be ml-80/ml-0")
logger.info("2. Message alignment (line 258): flex justification may be incorrect for RTL")
logger.info("3. Message order classes (line 264): order-1/order-2 may need adjustment")
logger.info("4. Text alignment (line 268): text-left/text-right may be inverted")

logger.info("=== APPLIED FIXES ===")
logger.info("1. FIXED: Changed mr-80/mr-0 to ml-80/ml-0 for proper RTL sidebar layout")
logger.info("2. FIXED: Swapped justify-start/justify-end for correct message alignment")
logger.info("3. FIXED: Swapped order-1/order-2 for proper message ordering in RTL")
logger.info("4. FIXED: Swapped text-left/text-right for correct timestamp alignment")
logger.info("=== VALIDATION REQUIRED ===")
logger.info("User should verify that:")
logger.info("- Sidebar appears on the right side")
logger.info("- User messages are right-aligned with timestamps on the right")
logger.info("- Assistant messages are left-aligned with timestamps on the left")
logger.info("- Layout transitions work smoothly when sidebar toggles")

class ChatUseCases:
    @staticmethod
    async def generate_conversation_title_and_tags(conversation_id: str) -> Dict[str, Any]:
        """Generate AI-powered title and tags for a conversation based on its messages."""
        try:
            from bson import ObjectId

            # Get conversation
            conversation = await Conversation.get(ObjectId(conversation_id))
            if not conversation:
                return {"error": "Conversation not found"}

            # Get messages from conversation
            messages = await Message.find(
                Message.conversation_id == conversation_id
            ).sort(Message.created_at).to_list()

            if len(messages) < 2:  # Need at least user message + AI response
                return {"title": conversation.title or "New Conversation", "tags": []}

            # Prepare conversation content for AI
            conversation_text = ""
            for msg in messages[:10]:  # Use first 10 messages to avoid token limits
                sender = "User" if msg.sender_type != "ai" else "Assistant"
                conversation_text += f"{sender}: {msg.content}\n"

            # Initialize OpenAI client
            if not settings.openai_api_key_loaded:
                return {"title": conversation.title or "New Conversation", "tags": []}

            # For now, use simple fallback for title/tags generation
            # TODO: Fix OpenAI client compatibility issues
            logger.info("Using fallback for title/tags generation")
            return {"title": conversation.title or "New Conversation", "tags": []}

            # For now, just return the existing title and empty tags
            return {"title": conversation.title or "New Conversation", "tags": conversation.tags or []}

        except Exception as e:
            logger.error(f"Error generating title and tags: {e}")
            return {"title": "New Conversation", "tags": [], "error": str(e)}

    @staticmethod
    async def send_admin_message(
        content: str,
        admin: Admin,
        conversation_id: Optional[str] = None,
        rag_type: str = "simple"
    ) -> Dict[str, Any]:
        """Process an admin chat message with RAG type selection."""
        
        # Create or get conversation
        if conversation_id:
            try:
                from bson import ObjectId
                conversation = await Conversation.get(ObjectId(conversation_id))
                if not conversation:
                    raise ValueError("Conversation not found")
            except Exception as e:
                raise ValueError(f"Error retrieving conversation: {str(e)}")
        else:
            # Create new conversation for admin
            conversation = Conversation(
                customer_id=None,  # Admin conversations don't have customer_id
                admin_id=str(admin.id),
                title=content[:50] + "..." if len(content) > 50 else content,
                tags=[f"admin-{rag_type}-rag"],
                guest_session_id=None
            )
            await conversation.insert()
            logger.info(f"Created new admin conversation: {conversation.id}")

        # Save user message
        user_message = Message(
            conversation_id=str(conversation.id),
            content=content,
            sender_type="admin",
            sender_id=str(admin.id),
            is_failed=False,
            failure_reason=None,
            metadata={
                "rag_type": rag_type,
                "admin_email": admin.email,
                "admin_name": admin.full_name
            }
        )
        await user_message.insert()
        logger.info(f"Saved admin message: {user_message.id}")

        # Prepare context for RAG service
        context = {
            "user_id": str(admin.id),
            "user_type": "Admin",
            "conversation_id": str(conversation.id),
            "rag_type": rag_type
        }

        # Get appropriate RAG service based on type
        if rag_type == "simple":
            from app.infrastructure.rag_service import SimpleRAGService
            rag_service = SimpleRAGService()
        else:  # agentic
            from app.infrastructure.rag_service import AgenticRAGService
            rag_service = AgenticRAGService()

        # Generate AI response
        ai_message = None
        try:
            rag_response = await rag_service.generate_response(content, context)
            ai_content = rag_response["response"]
            sources = rag_response.get("sources", [])
            confidence = rag_response.get("confidence", 0.5)
            suggested_actions = rag_response.get("suggested_actions", [])

            # Create rich metadata
            rich_metadata = {
                "sources": sources,
                "confidence": confidence,
                "suggested_actions": suggested_actions,
                "rag_type": rag_type,
                "model_name": settings.rag_model_loaded,
                "provider": "OpenAI",
                "api_base_url": settings.openai_base_url_loaded,
                "temperature": 0.7,
                "max_tokens": 1000,
                "response_time": None,
                "token_usage": {
                    "prompt_tokens": None,
                    "completion_tokens": None,
                    "total_tokens": None
                },
                "processing_details": {
                    "retrieval_method": "agentic_rag" if rag_type == "agentic" else "simple_rag",
                    "knowledge_base_used": bool(sources),
                    "fallback_used": False
                },
                "timestamp": datetime.utcnow().isoformat(),
                "admin_test_mode": True
            }

            # Save AI response
            ai_message = Message(
                conversation_id=str(conversation.id),
                content=ai_content,
                sender_type="ai",
                sender_id=None,
                is_failed=False,
                failure_reason=None,
                metadata=rich_metadata
            )
            await ai_message.insert()
            logger.info(f"Saved AI message with ID: {ai_message.id}")

            return {
                "conversation_id": str(conversation.id),
                "message": ai_content,
                "sources": sources,
                "confidence": confidence,
                "suggested_actions": suggested_actions,
                "message_id": str(ai_message.id),
                "metadata": {
                    "rag_type": rag_type,
                    "model_name": rich_metadata["model_name"],
                    "provider": rich_metadata["provider"],
                    "token_usage": rich_metadata["token_usage"]
                }
            }

        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            
            # Save failed AI message
            error_message = f"خطا در تولید پاسخ: {str(e)}"
            ai_message = Message(
                conversation_id=str(conversation.id),
                content=error_message,
                sender_type="ai",
                sender_id=None,
                is_failed=True,
                failure_reason=str(e),
                metadata={
                    "rag_type": rag_type,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                    "admin_test_mode": True
                }
            )
            await ai_message.insert()

            return {
                "conversation_id": str(conversation.id),
                "message": error_message,
                "sources": [],
                "confidence": 0.0,
                "suggested_actions": ["contact_support"],
                "message_id": str(ai_message.id),
                "metadata": {
                    "rag_type": rag_type,
                    "error": str(e)
                }
            }

    @staticmethod
    async def send_message(
        content: str,
        user: Optional[Union[Customer, Admin]] = None,
        user_type: str = "guest",
        conversation_id: Optional[str] = None,
        guest_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a chat message and generate AI response."""
        
        # Create or get conversation
        if conversation_id:
            try:
                from bson import ObjectId
                conversation = await Conversation.get(ObjectId(conversation_id))
                if not conversation:
                    raise ValueError("Conversation not found")
            except Exception as e:
                raise ValueError(f"Error retrieving conversation: {str(e)}")
        else:
            # For authenticated users, create conversation with appropriate user ID
            if user and user_type in ["Customer", "Admin"]:
                conversation = Conversation(
                    customer_id=str(user.id) if user_type == "Customer" else None,
                    guest_session_id=None,
                    title=content[:50] + "..." if len(content) > 50 else content
                )
                try:
                    await conversation.insert()
                    logger.info(f"Created new conversation with ID: {conversation.id} for {user_type} {user.id}")
                except Exception as e:
                    raise ValueError(f"Error creating conversation: {str(e)}")
            
            # For guests, check if there's an existing conversation with this guest_session_id
            elif guest_session_id:
                existing_conversation = await Conversation.find_one(
                    Conversation.guest_session_id == guest_session_id
                )
                if existing_conversation:
                    conversation = existing_conversation
                    logger.info(f"Reusing existing conversation {conversation.id} for guest session {guest_session_id}")
                else:
                    # Create new conversation for guest
                    conversation = Conversation(
                        customer_id=None,
                        guest_session_id=guest_session_id,
                        title=content[:50] + "..." if len(content) > 50 else content
                    )
                    try:
                        await conversation.insert()
                        logger.info(f"Created new conversation with ID: {conversation.id} for guest session {guest_session_id}")
                    except Exception as e:
                        raise ValueError(f"Error creating conversation: {str(e)}")
            else:
                raise ValueError("No user or guest session provided")
        
        # Determine sender type and ID
        if user and user_type == "Customer":
            sender_type = "Customer"
            sender_id = str(user.id)
        elif user and user_type == "Admin":
            # Check if it's super admin
            admin_doc = await Admin.get(user.id)
            if admin_doc and admin_doc.role_name == "SuperAdmin":
                sender_type = "SuperAdmin"
            else:
                sender_type = "Admin"
            sender_id = str(user.id)
        else:
            sender_type = "Guest"
            sender_id = None

        # Save user message
        user_message = Message(
            conversation_id=str(conversation.id),
            content=content,
            sender_type=sender_type,
            sender_id=sender_id,
            metadata={
                "user_type": user_type,
                "ip_address": None,  # Could be added from request
                "user_agent": None,  # Could be added from request
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        await user_message.insert()
        logger.info(f"Saved user message with ID: {user_message.id} in conversation {conversation.id}")
        logger.info(f"User message data: sender_type={user_message.sender_type}, sender_id={user_message.sender_id}")
        
        # Get appropriate RAG service
        rag_service = get_rag_service(user)
        
        # Prepare context for agentic RAG
        context = {}
        if user:
            context = {
                "user_id": str(user.id),
                "user_type": user_type,
                "user_role": "Admin" if user_type == "Admin" else "Customer",
                "conversation_id": str(conversation.id)
            }
        
        # Generate AI response
        ai_message = None
        try:
            rag_response = await rag_service.generate_response(content, context)
            ai_content = rag_response["response"]
            sources = rag_response.get("sources", [])
            confidence = rag_response.get("confidence", 0.5)
            suggested_actions = rag_response.get("suggested_actions", [])

            # Create rich metadata
            rich_metadata = {
                "sources": sources,
                "confidence": confidence,
                "suggested_actions": suggested_actions,
                "rag_type": "agentic" if user else "simple",
                "model_name": settings.chat_model_loaded,
                "provider": "OpenRouter",
                "api_base_url": settings.openai_base_url_loaded,
                "temperature": 0.7,  # Default temperature
                "max_tokens": 1000,  # Default max tokens
                "response_time": None,  # Could be measured
                "token_usage": {
                    "prompt_tokens": None,  # Would need to be extracted from API response
                    "completion_tokens": None,
                    "total_tokens": None
                },
                "processing_details": {
                    "retrieval_method": "vector_search" if user else "direct",
                    "knowledge_base_used": bool(sources),
                    "fallback_used": False
                },
                "timestamp": datetime.utcnow().isoformat()
            }

            # Save AI response
            ai_message = Message(
                conversation_id=str(conversation.id),
                content=ai_content,
                sender_type="ai",
                sender_id=None,
                is_failed=False,
                failure_reason=None,
                metadata=rich_metadata
            )
            await ai_message.insert()
            logger.info(f"Saved AI message with ID: {ai_message.id} in conversation {conversation.id}")
            logger.info(f"AI message data: confidence={confidence}, sources_count={len(sources)}")

            # Generate AI-powered title and tags for the conversation
            try:
                title_tags_result = await ChatUseCases.generate_conversation_title_and_tags(str(conversation.id))
                logger.info(f"Generated title and tags: {title_tags_result}")
            except Exception as e:
                logger.warning(f"Failed to generate title and tags: {e}")

            # Log unanswered question if confidence is low
            if confidence < 0.3:
                unanswered = UnansweredQuestion(
                    question=content,
                    customer_id=str(user.id) if user and user_type == "Customer" else None,
                    guest_session_id=guest_session_id if not user else None,
                    context={"conversation_id": str(conversation.id), "confidence": confidence}
                )
                await unanswered.insert()
            
            return {
                "conversation_id": str(conversation.id),
                "message": ai_content,
                "sources": sources,
                "confidence": confidence,
                "suggested_actions": suggested_actions,
                "message_id": str(ai_message.id)
            }
            
        except Exception as e:
            # Fallback response with failure tracking
            fallback_content = "متأسفانه در حال حاضر به سرویس هوش مصنوعی دسترسی ندارم، اما می‌توانم به شما کمک کنم. لطفاً سوال خود را مطرح کنید یا با تیم پشتیبانی تماس بگیرید."

            # Create rich error metadata
            error_metadata = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "fallback": True,
                "rag_type": "failed",
                "model_name": settings.chat_model_loaded,
                "provider": "OpenRouter",
                "api_base_url": settings.openai_base_url_loaded,
                "temperature": 0.7,
                "max_tokens": 1000,
                "response_time": None,
                "token_usage": {
                    "prompt_tokens": None,
                    "completion_tokens": None,
                    "total_tokens": None
                },
                "processing_details": {
                    "retrieval_method": "failed",
                    "knowledge_base_used": False,
                    "fallback_used": True,
                    "failure_stage": "ai_generation"
                },
                "timestamp": datetime.utcnow().isoformat()
            }

            ai_message = Message(
                conversation_id=str(conversation.id),
                content=fallback_content,
                sender_type="ai",
                sender_id=None,
                is_failed=True,
                failure_reason=str(e),
                metadata=error_metadata
            )
            await ai_message.insert()

            logger.error(f"AI generation failed: {e}")
            return {
                "conversation_id": str(conversation.id),
                "message": fallback_content,
                "sources": [],
                "confidence": 0.0,
                "suggested_actions": ["contact_support"],
                "message_id": str(ai_message.id),
                "is_failed": True,
                "failure_reason": str(e)
            }
    
    @staticmethod
    async def send_message_stream(
        content: str,
        user: Optional[Union[Customer, Admin]] = None,
        user_type: str = "guest",
        conversation_id: Optional[str] = None,
        guest_session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a chat message and stream AI response in real-time.
        
        Yields:
            Dict containing streaming events with types: 'init', 'chunk', 'sources', 'done', 'error'
        """
        
        logger.info(f"🌊 Starting streaming chat for {user_type}")
        
        # Create or get conversation (same as send_message)
        if conversation_id:
            try:
                from bson import ObjectId
                conversation = await Conversation.get(ObjectId(conversation_id))
                if not conversation:
                    yield {"type": "error", "message": "Conversation not found"}
                    return
            except Exception as e:
                yield {"type": "error", "message": f"Error retrieving conversation: {str(e)}"}
                return
        else:
            # Create new conversation
            if user and user_type in ["Customer", "Admin"]:
                conversation = Conversation(
                    customer_id=str(user.id) if user_type == "Customer" else None,
                    guest_session_id=None,
                    title=content[:50] + "..." if len(content) > 50 else content
                )
                try:
                    await conversation.insert()
                    logger.info(f"✅ Created conversation: {conversation.id}")
                except Exception as e:
                    yield {"type": "error", "message": f"Error creating conversation: {str(e)}"}
                    return
            elif guest_session_id:
                # Check for existing guest conversation
                existing_conversation = await Conversation.find_one(
                    Conversation.guest_session_id == guest_session_id
                )
                if existing_conversation:
                    conversation = existing_conversation
                else:
                    conversation = Conversation(
                        customer_id=None,
                        guest_session_id=guest_session_id,
                        title=content[:50] + "..." if len(content) > 50 else content
                    )
                    await conversation.insert()
            else:
                yield {"type": "error", "message": "No user or guest session provided"}
                return
        
        # Determine sender type
        if user and user_type == "Customer":
            sender_type = "Customer"
            sender_id = str(user.id)
        elif user and user_type == "Admin":
            admin_doc = await Admin.get(user.id)
            if admin_doc and admin_doc.role_name == "SuperAdmin":
                sender_type = "SuperAdmin"
            else:
                sender_type = "Admin"
            sender_id = str(user.id)
        else:
            sender_type = "Guest"
            sender_id = None
        
        # Save user message
        user_message = Message(
            conversation_id=str(conversation.id),
            content=content,
            sender_type=sender_type,
            sender_id=sender_id,
            metadata={
                "user_type": user_type,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        await user_message.insert()
        logger.info(f"💾 Saved user message: {user_message.id}")
        
        # Send initial event
        yield {
            "type": "init",
            "conversation_id": str(conversation.id),
            "message_id": str(user_message.id)
        }
        
        # Get RAG service
        rag_service = get_rag_service(user)
        
        # Prepare context
        context = {}
        if user:
            context = {
                "user_id": str(user.id),
                "user_type": user_type,
                "conversation_id": str(conversation.id)
            }
        
        # Stream AI response
        full_response = ""
        sources = []
        confidence = 0.5

        try:
            # Retrieve relevant documents first
            logger.info("📚 Retrieving documents...")
            relevant_docs = await rag_service.retrieve_relevant_documents(
                content,
                is_public_only=(not user)
            )

            # DEBUG: چک کردن منابع پیدا شده
            logger.info(f"🔍 DEBUG: Found {len(relevant_docs)} documents from Weaviate")
            for i, doc in enumerate(relevant_docs[:3]):
                logger.info(f"   Doc {i+1}: ID={doc.get('id')}, Title='{doc.get('title', '')[:50]}...'")
            
            if relevant_docs:
                sources = rag_service._format_sources_markdown(relevant_docs[:3])
                confidence = 0.9
                
                # Send sources event
                yield {
                    "type": "sources",
                    "sources": sources,
                    "confidence": confidence
                }
                
                # Build context
                context_text = "\n\n".join([
                    f"Document: {doc['title']}\nContent: {doc['content']}"
                    for doc in relevant_docs[:3]
                ])
                
                # Stream RAG response (chunks are already split word-by-word in langchain_utils)
                logger.info("🤖 Streaming STRICT RAG response...")
                from app.infrastructure.langchain_utils import langchain_service
                
                async for chunk in langchain_service.generate_rag_response_stream(content, context_text):
                    full_response += chunk
                    # chunks قبلاً در langchain_utils به کلمات تقسیم شده‌اند
                    yield {
                        "type": "chunk",
                        "content": chunk
                    }
            else:
                # STRICT MODE: اگر سندی نیست، از LLM استفاده نمی‌کنیم
                logger.warning("❌ No documents found - STRICT MODE: Not using general LLM knowledge")
                full_response = "متأسفانه اطلاعات مربوط به سوال شما در پایگاه دانش موجود نیست. لطفاً سوال خود را واضح‌تر بیان کنید یا با تیم پشتیبانی تماس بگیرید."
                
                yield {
                    "type": "chunk",
                    "content": full_response
                }
                
                confidence = 0.0
            
            # Save AI message
            ai_message = Message(
                conversation_id=str(conversation.id),
                content=full_response,
                sender_type="ai",
                sender_id=None,
                is_failed=False,
                metadata={
                    "sources": sources,
                    "confidence": confidence,
                    "rag_type": "agentic" if user else "simple",
                    "streaming": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            await ai_message.insert()
            
            # Send completion event
            yield {
                "type": "complete",
                "message_id": str(ai_message.id),
                "full_response": full_response,
                "confidence": confidence
            }
            
            logger.info(f"✅ Streaming completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}", exc_info=True)
            
            # Save failed AI message
            error_message = f"خطا در تولید پاسخ: {str(e)}"
            ai_message = Message(
                conversation_id=str(conversation.id),
                content=error_message,
                sender_type="ai",
                sender_id=None,
                is_failed=True,
                failure_reason=str(e),
                metadata={
                    "streaming": True,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            await ai_message.insert()
            
            yield {
                "type": "error",
                "message": str(e),
                "message_id": str(ai_message.id)
            }
    
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
        conversations = await Conversation.find(
            Conversation.customer_id == str(customer.id)
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
                Message.sender_type == "ai",
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