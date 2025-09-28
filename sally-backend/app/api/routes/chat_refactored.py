from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request
from typing import Optional, List, Union
from pydantic import BaseModel
from bson import ObjectId
from app.domain.entities_refactored import (
    Customer, Admin, Conversation, Message, GuestSession, UnansweredQuestion,
    MessageRating
)
from app.core.permissions import get_current_customer, get_optional_customer, get_optional_admin
from app.use_cases.chat_use_cases_refactored import ChatUseCases
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    content: str
    conversation_id: Optional[str] = None
    guest_session_id: Optional[str] = None
    
    class Config:
        from_attributes = True


class AdminChatMessage(BaseModel):
    content: str
    conversation_id: Optional[str] = None
    rag_type: str = "simple"  # "simple" or "agentic"
    
    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    sources: List[dict] = []
    confidence: float
    suggested_actions: List[str] = []
    message_id: str


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: Request,
    message: ChatMessage,
    current_customer: Optional[Customer] = Depends(get_optional_customer),
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """Send a chat message and get AI response."""
    
    # Determine user type - prefer authenticated users over guests
    current_user = current_customer or current_admin
    user_type = "Customer" if current_customer else ("Admin" if current_admin else "guest")
    
    try:
        # Log message for monitoring
        logger.info(f"Chat message received - User type: {user_type}, Content length: {len(message.content)}, Conversation ID: {message.conversation_id}")
        
        # Validate guest session ID for guests only
        if not current_user and not message.guest_session_id:
            raise HTTPException(status_code=400, detail="guest_session_id is required for guest users")
        
        response = await ChatUseCases.send_message(
            content=message.content,
            user=current_user,
            user_type=user_type,
            conversation_id=message.conversation_id,
            guest_session_id=message.guest_session_id
        )
        
        return ChatResponse(**response)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        print(f"Unexpected error in send_message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/admin/message", response_model=ChatResponse)
async def send_admin_message(
    request: Request,
    message: AdminChatMessage,
    current_admin: Admin = Depends(get_optional_admin)
):
    """Send a chat message as admin with RAG type selection."""
    
    if not current_admin:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    
    try:
        # Log message for monitoring
        logger.info(f"Admin chat message received - Admin: {current_admin.email}, RAG type: {message.rag_type}, Content length: {len(message.content)}, Conversation ID: {message.conversation_id}")
        
        # Validate RAG type
        if message.rag_type not in ["simple", "agentic"]:
            raise HTTPException(status_code=400, detail="Invalid RAG type. Must be 'simple' or 'agentic'")
        
        response = await ChatUseCases.send_admin_message(
            content=message.content,
            admin=current_admin,
            conversation_id=message.conversation_id,
            rag_type=message.rag_type
        )
        
        return ChatResponse(**response)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Unexpected error in send_admin_message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/conversations")
async def get_conversations(
    current_customer: Optional[Customer] = Depends(get_optional_customer),
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """Get conversations - authenticated users only"""
    try:
        # Determine user type and get appropriate conversations
        if current_customer:
            conversations = await ChatUseCases.get_user_conversations(current_customer)
        elif current_admin:
            conversations = await ChatUseCases.get_admin_conversations(current_admin)
        else:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        return {"conversations": conversations}
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class TitleUpdateRequest(BaseModel):
    title: str


class MessageRatingRequest(BaseModel):
    rating: int  # 1-5 scale
    comment: Optional[str] = None

@router.put("/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: str,
    title_request: TitleUpdateRequest,
    current_customer: Customer = Depends(get_current_customer)
):
    """Update conversation title."""
    try:
        # Get the conversation to check ownership
        conversation = await Conversation.get(ObjectId(conversation_id))
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Check if customer owns the conversation
        if conversation.customer_id != str(current_customer.id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Update the title
        conversation.title = title_request.title
        conversation.updated_at = datetime.utcnow()
        await conversation.save()

        return {"message": "Title updated successfully"}
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/conversations/{conversation_id}/generate-title-tags")
async def generate_conversation_title_tags(
    conversation_id: str,
    current_customer: Optional[Customer] = Depends(get_optional_customer),
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """Generate AI-powered title and tags for a conversation."""
    try:
        # Get the conversation to check ownership
        conversation = await Conversation.get(ObjectId(conversation_id))
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Check permissions
        if current_customer and conversation.customer_id != str(current_customer.id):
            raise HTTPException(status_code=403, detail="Access denied")
        elif not current_customer and not current_admin:
            # For guests, check guest session ownership
            raise HTTPException(status_code=403, detail="Access denied - authentication required")

        # Generate title and tags
        result = await ChatUseCases.generate_conversation_title_and_tags(conversation_id)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "message": "Title and tags generated successfully",
            "title": result["title"],
            "tags": result["tags"]
        }
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        print(f"Error generating title and tags: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/messages/{message_id}/rate")
async def rate_message(
    message_id: str,
    rating_request: MessageRatingRequest,
    current_customer: Optional[Customer] = Depends(get_optional_customer),
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """Rate an AI message response."""
    try:
        # Validate rating range
        if not 1 <= rating_request.rating <= 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

        # Get the message
        message = await Message.get(ObjectId(message_id))
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        # Check if message is from AI
        if message.sender_type != "ai":
            raise HTTPException(status_code=400, detail="Only AI messages can be rated")

        # Get the conversation to check ownership
        conversation = await Conversation.get(ObjectId(message.conversation_id))
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Check permissions - only conversation owner can rate messages
        rater_id = None
        if current_customer and conversation.customer_id == str(current_customer.id):
            rater_id = str(current_customer.id)
        elif current_admin:
            rater_id = str(current_admin.id)
        else:
            raise HTTPException(status_code=403, detail="Access denied - only conversation participants can rate messages")

        # Create or update rating
        message.rating = MessageRating(
            rating=rating_request.rating,
            comment=rating_request.comment,
            rated_by=rater_id,
            rated_at=datetime.utcnow()
        )

        await message.save()

        return {
            "message": "Rating submitted successfully",
            "rating": rating_request.rating,
            "comment": rating_request.comment
        }

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        print(f"Error rating message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/conversations/{conversation_id}/rating-stats")
async def get_conversation_rating_stats(
    conversation_id: str,
    current_customer: Optional[Customer] = Depends(get_optional_customer),
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """Get rating statistics for a conversation."""
    try:
        # Get the conversation to check ownership
        conversation = await Conversation.get(ObjectId(conversation_id))
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Check permissions
        if current_customer and conversation.customer_id != str(current_customer.id):
            raise HTTPException(status_code=403, detail="Access denied")
        elif not current_customer and not current_admin:
            raise HTTPException(status_code=403, detail="Access denied - authentication required")

        # Get rating statistics
        stats = await ChatUseCases.get_message_rating_stats(conversation_id)

        return {
            "conversation_id": conversation_id,
            "rating_stats": stats
        }

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        print(f"Error getting rating stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    current_customer: Optional[Customer] = Depends(get_optional_customer),
    current_admin: Optional[Admin] = Depends(get_optional_admin),
    guest_session_id: Optional[str] = None
):
    """Get messages from a conversation."""
    try:
        # Determine user type and ID for access control
        user_type = "Customer" if current_customer else ("Admin" if current_admin else "Guest")
        user_id = str(current_customer.id) if current_customer else (str(current_admin.id) if current_admin else None)
        
        logger.info(f"Getting conversation history - Conversation ID: {conversation_id}, User type: {user_type}")
        
        # Validate guest session ID for guests
        if not current_customer and not current_admin and not guest_session_id:
            raise HTTPException(status_code=400, detail="guest_session_id is required for guest users")
        
        messages = await ChatUseCases.get_conversation_history(
            conversation_id, 
            user_type=user_type, 
            user_id=user_id, 
            guest_session_id=guest_session_id
        )
        logger.info(f"Returning {len(messages)} messages for conversation {conversation_id}")
        
        return {"messages": messages}
    except ValueError as e:
        logger.error(f"Chat API error: {e}")
        if "Conversation not found" in str(e):
            raise HTTPException(status_code=404, detail="Conversation not found")
        elif "Access denied" in str(e):
            raise HTTPException(status_code=403, detail="Access denied")
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Unexpected error in chat API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# WebSocket functionality - temporarily disabled
# TODO: Implement WebSocket support when real-time features are needed
"""
# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except:
            self.disconnect(websocket)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # WebSocket endpoint temporarily disabled
    await websocket.close(code=1001)  # Going away
"""