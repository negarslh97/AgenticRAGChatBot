from beanie import Document, Indexed
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    GUEST = "guest"
    CUSTOMER = "customer"
    admin = "admin"
    SuperAdmin = "SuperAdmin"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ArticleVisibility(str, Enum):
    PUBLIC = "public"
    CUSTOMER = "customer"
    INTERNAL = "internal"

class ArticleStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class User(Document):
    email: Indexed(str, unique=True)
    hashed_password: str
    full_name: str
    role: UserRole = UserRole.CUSTOMER
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "users"


class GuestSession(Document):
    session_id: Indexed(str, unique=True)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "guest_sessions"


class Conversation(Document):
    user_id: Optional[str] = None  # None for guest conversations
    guest_session_id: Optional[str] = None
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "conversations"


class Message(Document):
    conversation_id: str
    content: str
    is_from_user: bool = True
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "messages"


class Ticket(Document):
    customer_id: str
    title: str
    description: str
    status: TicketStatus = TicketStatus.OPEN
    priority: str = "medium"  # low, medium, high, urgent
    assigned_to: Optional[str] = None  # admin user ID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "tickets"


class TicketReply(Document):
    ticket_id: str
    user_id: str
    content: str
    is_internal: bool = False  # Internal notes vs customer-visible replies
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "ticket_replies"


class Category(Document):
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    is_public: bool = True  # Public categories visible to guests
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "categories"


class Tag(Document):
    name: Indexed(str, unique=True)
    color: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "tags"

class KnowledgeBaseArticle(Document):
    title: str
    content: str
    summary: Optional[str] = None
    category_id: Optional[str] = None
    tags: List[str] = []
    status: ArticleStatus = ArticleStatus.DRAFT
    visibility: Optional[ArticleVisibility] = None  # Only set for published articles
    author_id: str
    published_by: Optional[str] = None  # Super admin who published
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    
    class Settings:
        name = "knowledge_base_articles"



class UnansweredQuestion(Document):
    question: str
    user_id: Optional[str] = None
    guest_session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_resolved: bool = False
    
    class Settings:
        name = "unanswered_questions"


class Feedback(Document):
    conversation_id: Optional[str] = None
    ticket_id: Optional[str] = None
    user_id: Optional[str] = None
    guest_session_id: Optional[str] = None
    rating: int  # 1-5 scale
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "feedback"


class ActivityLog(Document):
    user_id: str
    action: str
    resource_type: str  # "article", "user", "ticket", etc.
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "activity_logs"
