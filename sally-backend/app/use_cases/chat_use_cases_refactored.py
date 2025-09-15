from typing import Optional, Dict, Any, List, Union
import uuid
import logging

from app.domain.entities_refactored import (
    Conversation, Message, Customer, Admin, GuestSession, UnansweredQuestion
)
from app.infrastructure.rag_service import get_rag_service

logger = logging.getLogger(__name__)

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
                    customer_id=user.id if user_type == "Customer" else None,
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
        
        # Save user message
        user_message = Message(
            conversation_id=conversation.id,
            content=content,
            is_from_user=True
        )
        await user_message.insert()
        logger.info(f"Saved user message with ID: {user_message.id} in conversation {conversation.id}")
        logger.info(f"User message data: conversation_id={user_message.conversation_id}, content={user_message.content}")
        
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
        try:
            rag_response = await rag_service.generate_response(content, context)
            ai_content = rag_response["response"]
            sources = rag_response.get("sources", [])
            confidence = rag_response.get("confidence", 0.5)
            suggested_actions = rag_response.get("suggested_actions", [])
            
            # Save AI response
            ai_message = Message(
                conversation_id=conversation.id,
                content=ai_content,
                is_from_user=False,
                metadata={
                    "sources": sources,
                    "confidence": confidence,
                    "suggested_actions": suggested_actions,
                    "rag_type": "agentic" if user else "simple"
                }
            )
            await ai_message.insert()
            logger.info(f"Saved AI message with ID: {ai_message.id} in conversation {conversation.id}")
            logger.info(f"AI message data: conversation_id={ai_message.conversation_id}, content={ai_message.content}")
            
            # Log unanswered question if confidence is low
            if confidence < 0.3:
                unanswered = UnansweredQuestion(
                    question=content,
                    customer_id=user.id if user and user_type == "Customer" else None,
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
            # Fallback response
            fallback_content = "I apologize, but I'm having trouble processing your request right now. Please try again or contact our support team for assistance."
            
            ai_message = Message(
                conversation_id=conversation.id,
                content=fallback_content,
                is_from_user=False,
                metadata={"error": str(e), "fallback": True}
            )
            await ai_message.insert()
            
            return {
                "conversation_id": str(conversation.id),
                "message": fallback_content,
                "sources": [],
                "confidence": 0.1,
                "suggested_actions": ["contact_support"],
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
            # For authenticated customers, check if they own the conversation
            if conversation.customer_id and conversation.customer_id != ObjectId(user_id):
                raise ValueError("Access denied")
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
            Message.conversation_id == conversation.id
        ).sort(Message.created_at).to_list()
        
        logger.info(f"Found {len(messages)} messages for conversation {conversation_id}")
        
        result = [
            {
                "id": str(msg.id),
                "content": msg.content,
                "is_from_user": msg.is_from_user,
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
            Conversation.customer_id == customer.id
        ).sort(-Conversation.updated_at).to_list()
        
        return [
            {
                "id": str(conv.id),
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat()
            }
            for conv in conversations
        ]