from typing import Optional, Dict, Any, List
import uuid
import logging

from app.domain.entities import Conversation, Message, User, UnansweredQuestion
from app.infrastructure.rag_service import get_rag_service

logger = logging.getLogger(__name__)

class ChatUseCases:
    @staticmethod
    async def send_message(
        content: str,
        user: Optional[User] = None,
        conversation_id: Optional[str] = None,
        guest_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a chat message and generate AI response."""
        
        # Create or get conversation
        if conversation_id:
            try:
                conversation = await Conversation.get(conversation_id)
                if not conversation:
                    raise ValueError("Conversation not found")
            except Exception as e:
                raise ValueError(f"Error retrieving conversation: {str(e)}")
        else:
            # For authenticated users, create conversation with user_id
            if user:
                conversation = Conversation(
                    user_id=str(user.id),
                    guest_session_id=None,
                    title=content[:50] + "..." if len(content) > 50 else content
                )
                try:
                    await conversation.insert()
                    logger.info(f"Created new conversation with ID: {conversation.id} for user {user.id}")
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
                        user_id=None,
                        guest_session_id=guest_session_id,
                        title=content[:50] + "..." if len(content) > 50 else content
                    )
                    try:
                        await conversation.insert()
                        logger.info(f"Created new conversation with ID: {conversation.id} for guest session {guest_session_id}")
                    except Exception as e:
                        raise ValueError(f"Error creating conversation: {str(e)}")
        
        # Save user message
        user_message = Message(
            conversation_id=str(conversation.id),
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
                "user_role": user.role.value,
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
                conversation_id=str(conversation.id),
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
                    user_id=str(user.id) if user else None,
                    guest_session_id=guest_session_id,
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
                conversation_id=str(conversation.id),
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
        user: Optional[User] = None,
        guest_session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get conversation message history."""
        
        conversation = await Conversation.get(conversation_id)
        if not conversation:
            logger.info(f"Conversation not found: {conversation_id}")
            logger.info(f"All conversations: {await Conversation.find().to_list()}")
            raise ValueError("Conversation not found")
        
        # Check access permissions
        if user:
            # For authenticated users, check if they own the conversation
            if conversation.user_id and conversation.user_id != str(user.id):
                raise ValueError("Access denied")
        else:
            # For guests, allow access to guest conversations only if guest_session_id matches
            if not conversation.guest_session_id:
                raise ValueError("Access denied")
            if guest_session_id and conversation.guest_session_id != guest_session_id:
                raise ValueError("Access denied - guest session ID mismatch")
        
        # Ensure conversation_id is in the correct format
        from bson import ObjectId
        try:
            # Always use string comparison for conversation_id to avoid ObjectId conversion issues
            query = Message.conversation_id == conversation_id
            logger.info(f"Using string query for conversation_id: {conversation_id}")
        except Exception as e:
            logger.error(f"Error creating query for conversation_id {conversation_id}: {e}")
            query = Message.conversation_id == conversation_id
        
        # Add debug logging
        logger.info(f"Looking for messages with query: {query}")
        
        messages = await Message.find(query).sort(Message.created_at).to_list()
        logger.info(f"Found {len(messages)} messages for conversation {conversation_id}")
        
        # Convert ObjectId to string for each message
        messages = [msg for msg in messages]
        
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
    async def get_user_conversations(user: User) -> List[Dict[str, Any]]:
        """Get user's conversation list."""
        conversations = await Conversation.find(
            Conversation.user_id == str(user.id)
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
