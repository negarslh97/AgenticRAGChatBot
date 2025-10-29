"""
Chat Management Schemas
======================

Enhanced Pydantic schemas for chat-related functionality.
Includes comprehensive validation rules and custom validators.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    """Enum for message types."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    AI = "ai"


class ChatMessage(BaseModel):
    """Schema for chat message."""
    
    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Message content (1-10000 characters)",
        example="Hello, I need help with my account."
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Conversation ID (ObjectId as string)",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    guest_session_id: Optional[str] = Field(
        None,
        description="Guest session ID for anonymous users",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    message_type: MessageType = Field(
        MessageType.USER,
        description="Message type",
        example=MessageType.USER
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata",
        example={"rag_type": "basic", "confidence": 0.95}
    )
    
    @validator('content')
    def validate_content(cls, v):
        """Validate message content."""
        if not v.strip():
            raise ValueError('Message content cannot be empty')
        
        # Remove extra whitespace
        content = ' '.join(v.strip().split())
        
        if len(content) < 1:
            raise ValueError('Message content must be at least 1 character long')
        
        if len(content) > 10000:
            raise ValueError('Message content must be at most 10000 characters long')
        
        return content
    
    @validator('conversation_id')
    def validate_conversation_id(cls, v):
        """Validate conversation ID format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Conversation ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Conversation ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Conversation ID must contain only hexadecimal characters')
        
        return v
    
    @validator('guest_session_id')
    def validate_guest_session_id(cls, v):
        """Validate guest session ID format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Guest session ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Guest session ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Guest session ID must contain only hexadecimal characters')
        
        return v


class ChatResponse(BaseModel):
    """Schema for chat response."""
    
    message_id: str = Field(..., description="Message ID", example="60c72b2f9b1d8e001f8e4cde")
    conversation_id: str = Field(..., description="Conversation ID", example="60c72b2f9b1d8e001f8e4cde")
    content: str = Field(..., description="Response content", example="Hello! How can I help you today?")
    message_type: MessageType = Field(..., description="Message type", example=MessageType.ASSISTANT)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata", example={"rag_type": "basic", "confidence": 0.95})
    created_at: Optional[datetime] = Field(None, description="Message creation timestamp")


class ChatHistoryResponse(BaseModel):
    """Schema for chat history response."""
    
    conversation_id: str = Field(..., description="Conversation ID", example="60c72b2f9b1d8e001f8e4cde")
    messages: List[ChatResponse] = Field(..., description="List of messages")
    title: Optional[str] = Field(None, description="Conversation title", example="Account Help")
    created_at: Optional[datetime] = Field(None, description="Conversation creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Conversation update timestamp")


class MessageRating(BaseModel):
    """Schema for message rating."""
    
    message_id: str = Field(..., description="Message ID", example="60c72b2f9b1d8e001f8e4cde")
    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Rating (1-5 stars)",
        example=4
    )
    feedback: Optional[str] = Field(
        None,
        max_length=1000,
        description="Additional feedback",
        example="The response was helpful but could be more detailed."
    )
    
    @validator('rating')
    def validate_rating(cls, v):
        """Validate rating value."""
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v
    
    @validator('message_id')
    def validate_message_id(cls, v):
        """Validate message ID format."""
        if not v.strip():
            raise ValueError('Message ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Message ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Message ID must contain only hexadecimal characters')
        
        return v


class MessageRatingResponse(BaseModel):
    """Schema for message rating response."""
    
    message_id: str = Field(..., description="Message ID", example="60c72b2f9b1d8e001f8e4cde")
    rating: int = Field(..., description="Rating (1-5 stars)", example=4)
    feedback: Optional[str] = Field(None, description="Additional feedback", example="The response was helpful but could be more detailed.")
    created_at: Optional[datetime] = Field(None, description="Rating creation timestamp")


class ConversationStats(BaseModel):
    """Schema for conversation statistics."""
    
    total_conversations: int = Field(..., description="Total number of conversations", example=150)
    total_messages: int = Field(..., description="Total number of messages", example=1250)
    average_messages_per_conversation: float = Field(..., description="Average messages per conversation", example=8.33)
    active_conversations: int = Field(..., description="Number of active conversations", example=25)
    completed_conversations: int = Field(..., description="Number of completed conversations", example=125)
    conversations_today: int = Field(..., description="Conversations created today", example=5)
    conversations_this_week: int = Field(..., description="Conversations created this week", example=35)
    conversations_this_month: int = Field(..., description="Conversations created this month", example=120)
    top_active_hours: List[Dict[str, Any]] = Field(..., description="Top active hours", example=[{"hour": 14, "count": 25}, {"hour": 15, "count": 20}])
    user_participation_stats: List[Dict[str, Any]] = Field(..., description="User participation statistics", example=[{"user_id": "60c72b2f9b1d8e001f8e4cde", "messages": 45}, {"user_id": "60c72b2f9b1d8e001f8e4cdf", "messages": 32}])


class UserActivity(BaseModel):
    """Schema for user activity."""
    
    id: str = Field(..., description="User ID", example="60c72b2f9b1d8e001f8e4cde")
    name: str = Field(..., description="User name", example="John Doe")
    email: str = Field(..., description="User email", example="john@example.com")
    user_type: str = Field(..., description="User type", example="Customer")
    total_conversations: int = Field(..., description="Total conversations", example=15)
    total_messages: int = Field(..., description="Total messages", example=125)
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    is_active: bool = Field(..., description="User active status", example=True)
    average_messages_per_conversation: float = Field(..., description="Average messages per conversation", example=8.33)


class RecentConversation(BaseModel):
    """Schema for recent conversation."""
    
    id: str = Field(..., description="Conversation ID", example="60c72b2f9b1d8e001f8e4cde")
    customer_name: str = Field(..., description="Customer name", example="John Doe")
    customer_email: str = Field(..., description="Customer email", example="john@example.com")
    admin_name: Optional[str] = Field(None, description="Admin name", example="Support Agent")
    start_time: datetime = Field(..., description="Conversation start time")
    end_time: Optional[datetime] = Field(None, description="Conversation end time")
    message_count: int = Field(..., description="Number of messages", example=15)
    status: str = Field(..., description="Conversation status", example="active")
    duration: Optional[str] = Field(None, description="Conversation duration", example="00:15:30")


class RAGType(str, Enum):
    """Enum for RAG types."""
    BASIC = "basic"
    ADVANCED = "advanced"
    AGENTIC = "agentic"
    AGENTIC_STREAM = "agentic_stream"


class AdvancedAgenticRequest(BaseModel):
    """Schema for advanced agentic RAG request."""
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="User query (1-5000 characters)",
        example="I need help with my account settings and billing information."
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Conversation ID (ObjectId as string)",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    rag_type: RAGType = Field(
        RAGType.AGENTIC,
        description="RAG type",
        example=RAGType.AGENTIC
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata",
        example={"temperature": 0.7, "max_tokens": 2000}
    )
    
    @validator('query')
    def validate_query(cls, v):
        """Validate query content."""
        if not v.strip():
            raise ValueError('Query cannot be empty')
        
        # Remove extra whitespace
        query = ' '.join(v.strip().split())
        
        if len(query) < 1:
            raise ValueError('Query must be at least 1 character long')
        
        if len(query) > 5000:
            raise ValueError('Query must be at most 5000 characters long')
        
        return query
    
    @validator('conversation_id')
    def validate_conversation_id(cls, v):
        """Validate conversation ID format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Conversation ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Conversation ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Conversation ID must contain only hexadecimal characters')
        
        return v


class AdvancedAgenticResponse(BaseModel):
    """Schema for advanced agentic RAG response."""
    
    response: str = Field(..., description="AI response", example="Based on your query about account settings and billing, I can help you with...")
    sources: List[Dict[str, Any]] = Field(..., description="Source information", example=[{"title": "Account Settings Guide", "relevance": 0.95}, {"title": "Billing Information", "relevance": 0.88}])
    confidence: float = Field(..., description="Response confidence", example=0.92)
    complexity: str = Field(..., description="Query complexity", example="medium")
    actions_taken: List[str] = Field(..., description="Actions taken by the AI", example=["query_decomposition", "multi_agent_coordination", "self_reflection"])
    reflection_notes: Optional[List[str]] = Field(None, description="AI reflection notes", example=["The query was complex and required multiple steps to answer."])
    errors: Optional[List[str]] = Field(None, description="Errors encountered", example=["Timeout while fetching source data"])
    session_id: str = Field(..., description="Session ID", example="60c72b2f9b1d8e001f8e4cde")
    conversation_id: str = Field(..., description="Conversation ID", example="60c72b2f9b1d8e001f8e4cde")
    created_at: Optional[datetime] = Field(None, description="Response creation timestamp")


class ChatStreamRequest(BaseModel):
    """Schema for chat streaming request."""
    
    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Message content (1-10000 characters)",
        example="Hello, I need help with my account."
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Conversation ID (ObjectId as string)",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    guest_session_id: Optional[str] = Field(
        None,
        description="Guest session ID for anonymous users",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    rag_type: RAGType = Field(
        RAGType.BASIC,
        description="RAG type",
        example=RAGType.BASIC
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata",
        example={"temperature": 0.7, "max_tokens": 2000}
    )
    
    @validator('content')
    def validate_content(cls, v):
        """Validate message content."""
        if not v.strip():
            raise ValueError('Message content cannot be empty')
        
        # Remove extra whitespace
        content = ' '.join(v.strip().split())
        
        if len(content) < 1:
            raise ValueError('Message content must be at least 1 character long')
        
        if len(content) > 10000:
            raise ValueError('Message content must be at most 10000 characters long')
        
        return content
    
    @validator('conversation_id')
    def validate_conversation_id(cls, v):
        """Validate conversation ID format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Conversation ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Conversation ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Conversation ID must contain only hexadecimal characters')
        
        return v
    
    @validator('guest_session_id')
    def validate_guest_session_id(cls, v):
        """Validate guest session ID format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Guest session ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Guest session ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Guest session ID must contain only hexadecimal characters')
        
        return v


class ChatStreamResponse(BaseModel):
    """Schema for chat streaming response."""
    
    event_type: str = Field(..., description="Event type", example="chunk")
    content: Optional[str] = Field(None, description="Response content", example="Hello! How can I help you today?")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata", example={"rag_type": "basic", "confidence": 0.95})
    message_id: Optional[str] = Field(None, description="Message ID", example="60c72b2f9b1d8e001f8e4cde")
    conversation_id: Optional[str] = Field(None, description="Conversation ID", example="60c72b2f9b1d8e001f8e4cde")
    created_at: Optional[datetime] = Field(None, description="Response creation timestamp")


class ConversationCreateRequest(BaseModel):
    """Schema for conversation creation request."""
    
    title: Optional[str] = Field(
        None,
        max_length=200,
        description="Conversation title",
        example="Account Help"
    )
    customer_id: Optional[str] = Field(
        None,
        description="Customer ID (ObjectId as string)",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    admin_id: Optional[str] = Field(
        None,
        description="Admin ID (ObjectId as string)",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    
    @validator('customer_id')
    def validate_customer_id(cls, v):
        """Validate customer ID format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Customer ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Customer ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Customer ID must contain only hexadecimal characters')
        
        return v
    
    @validator('admin_id')
    def validate_admin_id(cls, v):
        """Validate admin ID format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Admin ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Admin ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Admin ID must contain only hexadecimal characters')
        
        return v


class ConversationUpdateRequest(BaseModel):
    """Schema for conversation update request."""
    
    title: Optional[str] = Field(
        None,
        max_length=200,
        description="Conversation title",
        example="Account Help"
    )
    status: Optional[str] = Field(
        None,
        description="Conversation status",
        example="active"
    )
    admin_id: Optional[str] = Field(
        None,
        description="Admin ID (ObjectId as string)",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    
    @validator('admin_id')
    def validate_admin_id(cls, v):
        """Validate admin ID format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Admin ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Admin ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Admin ID must contain only hexadecimal characters')
        
        return v


class ConversationResponse(BaseModel):
    """Schema for conversation response."""
    
    id: str = Field(..., description="Conversation ID", example="60c72b2f9b1d8e001f8e4cde")
    title: Optional[str] = Field(None, description="Conversation title", example="Account Help")
    customer_id: Optional[str] = Field(None, description="Customer ID", example="60c72b2f9b1d8e001f8e4cde")
    admin_id: Optional[str] = Field(None, description="Admin ID", example="60c72b2f9b1d8e001f8e4cdf")
    status: str = Field(..., description="Conversation status", example="active")
    created_at: Optional[datetime] = Field(None, description="Conversation creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Conversation update timestamp")
    message_count: int = Field(..., description="Number of messages", example=15)
    last_message: Optional[ChatResponse] = Field(None, description="Last message in conversation")


class ConversationListResponse(BaseModel):
    """Schema for conversation list response."""
    
    conversations: List[ConversationResponse] = Field(..., description="List of conversations")
    total: int = Field(..., description="Total number of conversations")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")