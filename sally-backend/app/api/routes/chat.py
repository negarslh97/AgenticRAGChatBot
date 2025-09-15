from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request
from typing import Optional, List
from pydantic import BaseModel
from app.domain.entities import User, Conversation
from app.api.dependencies import get_current_user, get_optional_user
from app.use_cases.chat_use_cases import ChatUseCases
import json
from datetime import datetime

router = APIRouter()


class ChatMessage(BaseModel):
    content: str
    conversation_id: Optional[str] = None
    guest_session_id: Optional[str] = None
    
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
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Send a chat message and get AI response."""
    
    try:
        # Debug logging
        print(f"DEBUG: Raw request body: {await request.body()}")
        print(f"DEBUG: Received message request: {message}")
        print(f"DEBUG: Current user: {current_user}")
        print(f"DEBUG: Guest session ID: {message.guest_session_id}")
        print(f"DEBUG: Guest session ID type: {type(message.guest_session_id)}")
        print(f"DEBUG: Message content: {message.content}")
        print(f"DEBUG: Conversation ID: {message.conversation_id}")
        
        # Validate guest session ID for guests only
        if not current_user and not message.guest_session_id:
            raise HTTPException(status_code=400, detail="guest_session_id is required for guest users")
        
        response = await ChatUseCases.send_message(
            content=message.content,
            user=current_user,
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


@router.get("/conversations")
async def get_conversations(current_user: User = Depends(get_current_user)):
    """Get user's conversation history."""
    try:
        conversations = await ChatUseCases.get_user_conversations(current_user)
        return {"conversations": conversations}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: str,
    title: str,
    current_user: User = Depends(get_current_user)
):
    """Update conversation title."""
    try:
        # Get the conversation to check ownership
        conversation = await Conversation.get(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Check if user owns the conversation
        if conversation.user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update the title
        conversation.title = title
        conversation.updated_at = datetime.utcnow()
        await conversation.save()
        
        return {"message": "Title updated successfully"}
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    current_user: Optional[User] = Depends(get_optional_user),
    guest_session_id: Optional[str] = None
):
    """Get messages from a conversation."""
    try:
        print(f"DEBUG: Getting messages for conversation: {conversation_id}")
        print(f"DEBUG: Current user: {current_user.email if current_user else 'Guest'}")
        print(f"DEBUG: Guest session ID: {guest_session_id}")
        
        # Validate guest session ID for guests
        if not current_user and not guest_session_id:
            raise HTTPException(status_code=400, detail="guest_session_id is required for guest users")
        
        messages = await ChatUseCases.get_conversation_history(conversation_id, current_user, guest_session_id)
        print(f"DEBUG: Found {len(messages)} messages")
        
        return {"messages": messages}
    except ValueError as e:
        print(f"DEBUG: ValueError: {e}")
        if "Conversation not found" in str(e):
            raise HTTPException(status_code=404, detail="Conversation not found")
        elif "Access denied" in str(e):
            raise HTTPException(status_code=403, detail="Access denied")
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        print(f"DEBUG: Exception: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


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
    """WebSocket endpoint for real-time chat."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Extract user info if available (in real implementation, verify JWT token)
            user_id = message_data.get("user_id")
            user = None
            if user_id:
                user = await User.get(user_id)
            
            # Process message
            response = await ChatUseCases.send_message(
                content=message_data.get("content", ""),
                user=user,
                conversation_id=message_data.get("conversation_id"),
                guest_session_id=message_data.get("guest_session_id")
            )
            
            # Send response back
            await manager.send_personal_message(json.dumps({
                "type": "message_response",
                "data": response
            }), websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        await manager.send_personal_message(json.dumps({
            "type": "error",
            "message": "An error occurred processing your message"
        }), websocket)
        manager.disconnect(websocket)
