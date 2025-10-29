from __future__ import annotations

from beanie import Document, Indexed, Link
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from bson import ObjectId


# Removed AdminRole enum - using Role document instead


class ArticleVisibility(str, Enum):
    PUBLIC = "public"
    CUSTOMER = "customer"
    INTERNAL = "internal"

    @classmethod
    def _missing_(cls, value):
        # Handle case-insensitive matching for existing data
        if isinstance(value, str):
            value_lower = value.lower()
            for member in cls:
                if member.value == value_lower:
                    return member
        return super()._missing_(value)


class ArticleStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

    @classmethod
    def _missing_(cls, value):
        # Handle case-insensitive matching for existing data
        if isinstance(value, str):
            value_lower = value.lower()
            for member in cls:
                if member.value == value_lower:
                    return member
        return super()._missing_(value)


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
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        name = "admins"
    
    async def before_save(self) -> None:
        """Hook to update timestamps before saving."""
        self.updated_at = datetime.utcnow()
    
    async def get_role(self) -> Optional[Role]:
        """Get the admin's role document."""
        from bson import ObjectId
        return await Role.get(ObjectId(self.role_id))


class Customer(Document):
    """Customer user model."""
    email: Indexed(str, unique=True)
    username: Optional[str] = None  # Not indexed to avoid null duplicate issues
    hashed_password: str
    full_name: str
    is_active: bool = True
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    class Settings:
        name = "customers"
    
    async def before_save(self) -> None:
        """Hook to update timestamps before saving."""
        self.updated_at = datetime.utcnow()


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
    """Conversation can belong to either a customer, admin, or a guest session."""
    customer_id: Optional[str] = Indexed()  # Indexed for faster user queries
    admin_id: Optional[str] = Indexed()  # For admin conversations
    guest_session_id: Optional[str] = Indexed()  # Indexed for guest sessions
    title: Optional[str] = None  # AI-generated title for the conversation
    tags: List[str] = []  # AI-generated tags for categorizing the conversation

    # 🆕 Conversation metadata (settings used for this conversation)
    rag_type: Optional[str] = "simple"  # "simple" or "agentic"
    model_name: Optional[str] = None  # LLM model used
    temperature: Optional[float] = 0.7  # Temperature setting

    # 🆕 Conversation status and tracking
    status: str = "active"  # "active", "closed", "archived"
    resolved_at: Optional[datetime] = None
    closed_by: Optional[str] = None  # ID of admin who closed the conversation
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    class Settings:
        name = "conversations"
    
    async def before_save(self) -> None:
        """Hook to update timestamps before saving."""
        self.updated_at = datetime.utcnow()
        
        # Set resolved_at when status changes to "closed"
        if self.status == "closed" and self.resolved_at is None:
            self.resolved_at = datetime.utcnow()


class SenderType(str, Enum):
    """استاندارد نوع فرستنده پیام - با CamelCase"""
    SUPER_ADMIN = "SuperAdmin"
    ADMIN = "Admin"
    CUSTOMER = "Customer"
    GUEST = "Guest"
    AI = "AI"


class MessageRating(BaseModel):
    """User rating for AI responses."""
    rating: int  # 1-5 scale
    comment: Optional[str] = None
    rated_by: Optional[str] = None  # User ID who rated
    rated_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Message(Document):
    """
    Message belongs to a conversation.

    ✅ استاندارد ذخیره‌سازی:
    - sender_type: از Enum استفاده می‌کند (SuperAdmin, Admin, Customer, Guest, AI)
    - metadata: شامل تمام اطلاعات مدل، token usage، sources و غیره
    - rating: امتیاز کاربر برای پاسخ‌های AI
    - response_time: زمان پاسخگویی مدل (برای پیام‌های AI)
    - feedback_id: پیوند به بازخورد کاربر (برای پاسخ‌های AI)
    """
    conversation_id: str = Indexed()  # Indexed for faster queries
    content: str
    sender_type: str = SenderType.GUEST.value  # نوع فرستنده (از SenderType enum)
    sender_id: Optional[str] = None  # شناسه فرستنده (برای کاربران واقعی)
    is_failed: bool = False  # آیا پاسخ AI با خطا مواجه شد؟
    failure_reason: Optional[str] = None  # دلیل خطا (در صورت وجود)
    metadata: Optional[Dict[str, Any]] = None  # اطلاعات کامل (model, tokens, sources, confidence, ...)
    rating: Optional[MessageRating] = None  # امتیاز کاربر (برای پاسخ‌های AI)
    response_time: Optional[float] = None  # زمان پاسخگویی مدل (ثانیه) - برای پیام‌های AI
    feedback_id: Optional[str] = None  # پیوند به بازخورد کاربر (برای پاسخ‌های AI)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    class Settings:
        name = "messages"


class CategoryAncestor(BaseModel):
    """Represents an ancestor in the category hierarchy."""
    id: str  # ObjectId as string
    name: str


class Category(Document):
    """Knowledge base category with hierarchical support."""
    name: str = Indexed()  # Indexed for search
    slug: Indexed(str, unique=True)  # URL-friendly identifier
    description: Optional[str] = None
    color: Optional[str] = None  # Color in hex format (e.g., #4CAF50)
    parent: Optional[Link["Category"]] = None  # Reference to parent category
    ancestors: List[CategoryAncestor] = []  # List of all ancestors for easy querying
    is_public: bool = True  # Public categories visible to guests
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "categories"

    async def update_ancestors(self) -> None:
        """Update the ancestors list based on parent hierarchy."""
        if not self.parent:
            self.ancestors = []
            return

        # Fetch parent and its ancestors
        parent = await Category.get(str(self.parent.id))
        if parent:
            # Start with parent's ancestors and add the parent itself
            self.ancestors = parent.ancestors.copy()
            self.ancestors.append(CategoryAncestor(id=str(parent.id), name=parent.name))

    async def before_save(self) -> None:
        """Hook to update ancestors before saving."""
        await self.update_ancestors()
        self.updated_at = datetime.utcnow()


class Tag(Document):
    """Knowledge base tag with enhanced features."""
    name: Indexed(str, unique=True)
    color: Optional[str] = None
    description: Optional[str] = None
    usage_count: int = 0  # تعداد استفاده از این تگ
    is_system: bool = False  # تگ سیستمی (غیر قابل حذف توسط کاربر)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "tags"

    async def before_save(self) -> None:
        """Ensure name is lowercase for consistency."""
        if self.name:
            self.name = self.name.lower()
        self.updated_at = datetime.utcnow()

    async def increment_usage(self) -> None:
        """Increment usage count."""
        self.usage_count += 1
        await self.save()

    async def decrement_usage(self) -> None:
        """Decrement usage count."""
        if self.usage_count > 0:
            self.usage_count -= 1
            await self.save()


class ArticleCategory(BaseModel):
    """Embedded category information for articles."""
    id: str  # ObjectId as string
    name: str
    slug: str
    color: Optional[str] = None  # Denormalized color for better performance


class ArticleTag(BaseModel):
    """Embedded tag information for articles with enhanced features."""
    id: str  # ObjectId as string
    name: str
    color: Optional[str] = None
    description: Optional[str] = None
    is_system: bool = False


class KnowledgeBaseArticle(Document):
    """Knowledge base article with improved relationships."""
    title: str = Indexed()  # Indexed for search
    content_markdown: str  # Raw markdown content
    content_html: str  # Rendered HTML content
    summary: Optional[str] = None
    category: Optional[ArticleCategory] = None  # Embedded category info
    tags: List[ArticleTag] = []  # Embedded tags
    status: ArticleStatus = ArticleStatus.DRAFT
    visibility: Optional[ArticleVisibility] = None  # Only set for published articles
    author_id: str = Indexed()  # Author ID as string, indexed for filtering
    publisher_id: Optional[str] = None  # Publisher ID as string
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None  # تاریخ آخرین همگام‌سازی با Weaviate

    model_config = ConfigDict(arbitrary_types_allowed=True)

    class Settings:
        name = "knowledge_base_articles"

    async def before_save(self) -> None:
        """Hook to update timestamps before saving."""
        self.updated_at = datetime.utcnow()
        
        # Set published_at when status changes to PUBLISHED
        if self.status == ArticleStatus.PUBLISHED and self.published_at is None:
            self.published_at = datetime.utcnow()
        
        # Update last_synced_at when article is modified
        if self.last_synced_at is not None:
            self.last_synced_at = None  # Mark as unsynced


class UnansweredQuestion(Document):
    """Questions that couldn't be answered by the AI."""
    question: str = Indexed()  # Indexed for search
    customer_id: Optional[str] = Indexed()  # Store ObjectId as string, indexed for filtering
    guest_session_id: Optional[str] = Indexed()  # Reference to GuestSession, indexed
    context: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_resolved: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

    class Settings:
        name = "unanswered_questions"


class Feedback(Document):
    """User feedback for conversations."""
    conversation_id: Optional[str] = Indexed()  # Store ObjectId as string, indexed for filtering
    customer_id: Optional[str] = Indexed()  # Store ObjectId as string, indexed
    guest_session_id: Optional[str] = Indexed()  # Reference to GuestSession, indexed
    rating: int  # 1-5 scale
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None  # Admin ID who resolved the feedback

    model_config = ConfigDict(arbitrary_types_allowed=True)

    class Settings:
        name = "feedback"
    
    async def before_save(self) -> None:
        """Hook to update timestamps before saving."""
        self.updated_at = datetime.utcnow()


class ActivityLog(Document):
    """System activity logs for auditing."""
    admin_id: Optional[str] = Indexed()  # Store ObjectId as string, indexed for filtering
    customer_id: Optional[str] = Indexed()  # Store ObjectId as string, indexed
    action: str = Indexed()  # Indexed for filtering by action type
    resource_type: str = Indexed()  # "article", "customer", etc., indexed
    resource_id: Optional[str] = Indexed()  # Indexed for specific resource queries
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    class Settings:
        name = "activity_logs"
    
    async def before_save(self) -> None:
        """Hook to update timestamps before saving."""
        self.updated_at = datetime.utcnow()


# ===========================================
# MARKDOWN TREE STRUCTURES
# ===========================================

class MarkdownNode(BaseModel):
    """Node in the markdown tree structure."""
    id: str = Field(description="Unique ID for the node")
    title: str = Field(description="Heading text without # symbols")
    level: int = Field(description="Heading level (1-6 for # to ######)")
    content: str = Field(description="Content under this heading")
    parent_id: Optional[str] = Field(default=None, description="Parent node ID (-1 for root)")
    path: str = Field(description="Full path like '1.2.3' for hierarchy")
    order: int = Field(description="Order within siblings")
    children: List['MarkdownNode'] = Field(default_factory=list, description="Child nodes")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "title": self.title,
            "level": self.level,
            "content": self.content,
            "parent_id": self.parent_id,
            "path": self.path,
            "order": self.order,
            "children": [child.to_dict() for child in self.children]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MarkdownNode':
        """Create from dictionary."""
        children = [cls.from_dict(child) for child in data.get("children", [])]
        return cls(
            id=data["id"],
            title=data["title"],
            level=data["level"],
            content=data["content"],
            parent_id=data["parent_id"],
            path=data["path"],
            order=data["order"],
            children=children
        )


class MarkdownTree(BaseModel):
    """Complete markdown tree structure."""
    article_id: str = Field(description="Reference to the article")
    root_nodes: List[MarkdownNode] = Field(default_factory=list, description="Root level nodes")

    def get_all_nodes(self) -> List[MarkdownNode]:
        """Get all nodes in the tree (flattened)."""
        nodes = []

        def traverse(node: MarkdownNode):
            nodes.append(node)
            for child in node.children:
                traverse(child)

        for root in self.root_nodes:
            traverse(root)

        return nodes

    def find_node_by_path(self, path: str) -> Optional[MarkdownNode]:
        """Find a node by its path."""
        for node in self.get_all_nodes():
            if node.path == path:
                return node
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "article_id": self.article_id,
            "root_nodes": [node.to_dict() for node in self.root_nodes]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MarkdownTree':
        """Create from dictionary."""
        root_nodes = [MarkdownNode.from_dict(node) for node in data.get("root_nodes", [])]
        return cls(
            article_id=data["article_id"],
            root_nodes=root_nodes
        )