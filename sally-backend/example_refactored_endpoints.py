#!/usr/bin/env python3
"""
Complete working example of the refactored GET /api/chats endpoint
demonstrating the new multi-user system with RBAC.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId

# Import the refactored models and dependencies
from app.domain.entities_refactored import Customer, Conversation, Message, Admin
from app.core.permissions import get_current_customer, get_optional_auth_header, get_current_admin_with_permission, Permission
from app.core.security import verify_token, create_access_token

# Create FastAPI app instance
app = FastAPI(title="SallyChat Refactored Endpoints Example")


# Pydantic models for API responses
class ConversationResponse(BaseModel):
    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int
    last_message: Optional[str] = None


class ChatListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int
    customer_info: dict


# Example of the refactored GET /api/chats endpoint
@app.get("/api/chats", response_model=ChatListResponse)
async def get_customer_chats(
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Get all conversations for the currently authenticated customer.
    
    This endpoint demonstrates:
    1. Proper customer authentication
    2. Data ownership validation
    3. Efficient database queries with relationships
    4. Proper response formatting
    """
    
    # Get customer's conversations with message counts and last messages
    conversations = await Conversation.find(
        Conversation.customer_id == current_customer.id
    ).sort(-Conversation.updated_at).to_list()
    
    # Build response with additional conversation details
    conversation_responses = []
    
    for conv in conversations:
        # Get message count for this conversation
        message_count = await Message.find(
            Message.conversation_id == conv.id
        ).count()
        
        # Get the last message for preview
        last_message = await Message.find(
            Message.conversation_id == conv.id
        ).sort(-Message.created_at).limit(1).to_list()
        
        last_message_content = None
        if last_message:
            last_message_content = last_message[0].content[:100] + "..." if len(last_message[0].content) > 100 else last_message[0].content
        
        conversation_responses.append(ConversationResponse(
            id=str(conv.id),
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=message_count,
            last_message=last_message_content
        ))
    
    return ChatListResponse(
        conversations=conversation_responses,
        total=len(conversation_responses),
        customer_info={
            "id": str(current_customer.id),
            "email": current_customer.email,
            "full_name": current_customer.full_name
        }
    )


# Example of enhanced security with conversation ownership validation
@app.get("/api/chats/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Get messages for a specific conversation with ownership validation.
    
    This ensures customers can only access their own conversations.
    """
    
    try:
        conv_obj_id = ObjectId(conversation_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid conversation ID format"
        )
    
    # Find the conversation and verify ownership
    conversation = await Conversation.get(conv_obj_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Critical security check: ensure the customer owns this conversation
    if conversation.customer_id != current_customer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not own this conversation"
        )
    
    # Get all messages for this conversation
    messages = await Message.find(
        Message.conversation_id == conversation.id
    ).sort(Message.created_at).to_list()
    
    # Format messages for response
    message_responses = []
    for msg in messages:
        message_responses.append({
            "id": str(msg.id),
            "content": msg.content,
            "is_from_user": msg.is_from_user,
            "created_at": msg.created_at.isoformat(),
            "metadata": msg.metadata
        })
    
    return {
        "conversation_id": conversation_id,
        "messages": message_responses,
        "total_messages": len(message_responses),
        "conversation_title": conversation.title
    }


# Example of admin endpoint with permission checking
@app.get("/api/admin/chats/all")
async def get_all_conversations(
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.VIEW_CUSTOMERS))
):
    """
    Admin endpoint to view all conversations across all customers.
    
    Requires Admin authentication and specific permission.
    """
    
    # Admin can see all conversations
    all_conversations = await Conversation.find_all().sort(-Conversation.updated_at).to_list()
    
    conversation_responses = []
    for conv in all_conversations:
        # Get customer info for each conversation
        customer = None
        if conv.customer_id:
            customer = await Customer.get(conv.customer_id)
        
        # Get message count
        message_count = await Message.find(
            Message.conversation_id == conv.id
        ).count()
        
        conversation_responses.append({
            "id": str(conv.id),
            "customer": {
                "id": str(customer.id) if customer else None,
                "email": customer.email if customer else "Unknown",
                "full_name": customer.full_name if customer else "Unknown"
            },
            "title": conv.title,
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.updated_at.isoformat(),
            "message_count": message_count
        })
    
    return {
        "conversations": conversation_responses,
        "total": len(conversation_responses),
        "admin_info": {
            "id": str(current_admin.id),
            "email": current_admin.email,
            "role": "Admin"  # Would be populated from actual role
        }
    }


# Example of creating a test customer and conversation
async def create_test_data():
    """Create test data to demonstrate the new system."""
    
    # Create a test customer (check if exists first to avoid duplicate key error)
    test_customer = await Customer.find_one(Customer.email == "test.customer@example.com")
    
    if not test_customer:
        # Create new test customer if it doesn't exist
        test_customer = Customer(
            email="test.customer@example.com",
            hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "testpassword"
            full_name="Test Customer",
            username="test_customer_unique",  # Add unique username to avoid duplicate key error
            is_active=True
        )
        await test_customer.insert()
    
    # Create a test conversation (check if exists first)
    test_conversation = await Conversation.find_one(
        Conversation.customer_id == str(test_customer.id),
        Conversation.title == "Test Conversation About Support Issue"
    )
    
    if not test_conversation:
        # Create new conversation if it doesn't exist
        test_conversation = Conversation(
            customer_id=str(test_customer.id),
            title="Test Conversation About Support Issue",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        await test_conversation.insert()
    
    # Add some test messages
    messages = [
        Message(
            conversation_id=str(test_conversation.id),  # Convert ObjectId to string
            content="Hello, I need help with my account",
            is_from_user=True,
            created_at=datetime.utcnow()
        ),
        Message(
            conversation_id=str(test_conversation.id),  # Convert ObjectId to string
            content="I'd be happy to help you with your account. What seems to be the issue?",
            is_from_user=False,
            created_at=datetime.utcnow()
        ),
        Message(
            conversation_id=str(test_conversation.id),  # Convert ObjectId to string
            content="I can't log in to my account",
            is_from_user=True,
            created_at=datetime.utcnow()
        )
    ]
    
    for msg in messages:
        await msg.insert()
    
    print("Test data created successfully!")
    return test_customer, test_conversation


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_refactored_endpoints():
        """Test the refactored endpoints."""
        
        # Initialize database
        from app.infrastructure.database_refactored import init_db
        await init_db()
        
        # Create test data
        customer, conversation = await create_test_data()
        
        # Generate a test JWT token for the customer
        token = create_access_token(
            data={"sub": str(customer.id), "type": "customer"}
        )
        
        print(f"Test customer created: {customer.email}")
        print(f"Test conversation created: {conversation.id}")
        print(f"Test JWT token: {token[:50]}...")
        
        # Test the authentication system
        from app.core.permissions import get_current_customer_from_token
        verified_customer = await get_current_customer_from_token(token)
        
        if verified_customer:
            print(f"✓ Customer authentication successful: {verified_customer.email}")
        else:
            print("✗ Customer authentication failed")
        
        print("\nRefactored endpoint examples created successfully!")
        print("Use the JWT token to test the GET /api/chats endpoint")
    
    # Run the test
    asyncio.run(test_refactored_endpoints())