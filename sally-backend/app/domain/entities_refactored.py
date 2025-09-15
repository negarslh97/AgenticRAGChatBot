from beanie import Document, Indexed
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from bson import ObjectId


class AdminRole(str, Enum):
    SuperAdmin = "SuperAdmin"
    Admin = "Admin"


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


class PermissionDetail(BaseModel):
    """Represents the structure of a single permission object in the database."""
    permission_key: str
    description: Optional[str] = None
    resource: str
    action: str


class Role(Document):
    """RBAC role definition with permissions."""
    name: str = Indexed(unique=True)
    description: Optional[str] = None
    # 2. نوع فیلد permissions را به لیستی از مدل جدید PermissionDetail تغییر می‌دهیم
    permissions: List[PermissionDetail] = []
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "roles"
        
        
class Admin(Document):
    """Admin user model with RBAC support."""
    email: Indexed(str, unique=True)
    hashed_password: str
    full_name: str
    role_id: str  # Store ObjectId as string for compatibility
    role_name: str # Denormalized role name for readability
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        name = "admins"
    
    async def get_role(self) -> Optional[Role]:
        """Get the admin's role document."""
        from bson import ObjectId
        return await Role.get(ObjectId(self.role_id))


class Customer(Document):
    """Customer user model."""
    email: Indexed(str, unique=True)
    username: Optional[str] = None
    hashed_password: str
    full_name: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        name = "customers"


class GuestSession(Document):
    """Guest session for anonymous users."""
    session_id: Indexed(str, unique=True)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "guest_sessions"


class Conversation(Document):
    """Conversation can belong to either a customer or a guest session."""
    customer_id: Optional[str] = None
    guest_session_id: Optional[str] = None
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        name = "conversations"


class Message(Document):
    """Message belongs to a conversation."""
    conversation_id: str
    content: str
    is_from_user: bool = True
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        name = "messages"


class Ticket(Document):
    """Support ticket created by a customer."""
    customer_id: str
    title: str
    description: str
    status: TicketStatus = TicketStatus.OPEN
    priority: str = "medium"
    assigned_to: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        name = "tickets"


class TicketReply(Document):
    """Reply to a ticket can come from either a customer or an admin."""
    ticket_id: str
    customer_id: Optional[str] = None
    admin_id: Optional[str] = None
    content: str
    is_internal: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        name = "ticket_replies"


class Category(Document):
    """Knowledge base category."""
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    is_public: bool = True  # Public categories visible to guests
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "categories"


class Tag(Document):
    """Knowledge base tag."""
    name: Indexed(str, unique=True)
    color: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "tags"


class KnowledgeBaseArticle(Document):
    """Knowledge base article."""
    title: str
    content: str
    summary: Optional[str] = None
    category_id: Optional[str] = None
    tags: List[str] = []
    status: ArticleStatus = ArticleStatus.DRAFT
    visibility: Optional[ArticleVisibility] = None  # Only set for published articles
    author_id: str  # Store ObjectId as string
    published_by: Optional[str] = None  # Store ObjectId as string
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        name = "knowledge_base_articles"
    
    async def get_author(self) -> Optional[Admin]:
        """Get the author of this article."""
        from bson import ObjectId
        return await Admin.get(ObjectId(self.author_id))
    
    async def get_publisher(self) -> Optional[Admin]:
        """Get the admin who published this article."""
        if self.published_by:
            from bson import ObjectId
            return await Admin.get(ObjectId(self.published_by))
        return None


class UnansweredQuestion(Document):
    """Questions that couldn't be answered by the AI."""
    question: str
    customer_id: Optional[str] = None  # Store ObjectId as string
    guest_session_id: Optional[str] = None  # Reference to GuestSession
    context: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_resolved: bool = False
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        name = "unanswered_questions"


class Feedback(Document):
    """User feedback for conversations or tickets."""
    conversation_id: Optional[str] = None  # Store ObjectId as string
    ticket_id: Optional[str] = None  # Store ObjectId as string
    customer_id: Optional[str] = None  # Store ObjectId as string
    guest_session_id: Optional[str] = None  # Reference to GuestSession
    rating: int  # 1-5 scale
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        name = "feedback"


class ActivityLog(Document):
    """System activity logs for auditing."""
    admin_id: Optional[str] = None  # Store ObjectId as string
    customer_id: Optional[str] = None  # Store ObjectId as string
    action: str
    resource_type: str  # "article", "customer", "ticket", etc.
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        name = "activity_logs"