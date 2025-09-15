from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings
from app.domain.entities import (
    User, GuestSession, Conversation, Message, Ticket, TicketReply,
    Category, Tag, KnowledgeBaseArticle, UnansweredQuestion, Feedback, ActivityLog
)
from app.core.security import get_password_hash
from app.domain.entities import UserRole


async def init_database():
    """Initialize database connection and models."""
    client = AsyncIOMotorClient(settings.database_url)
    
    await init_beanie(
        database=client.get_default_database(),
        document_models=[
            User, GuestSession, Conversation, Message, Ticket, TicketReply,
            Category, Tag, KnowledgeBaseArticle, UnansweredQuestion, Feedback, ActivityLog
        ]
    )


async def create_default_admin():
    """Create default Super admin user if it doesn't exist."""
    existing_admin = await User.find_one(User.email == "admin@sally.com")
    
    if not existing_admin:
        admin_user = User(
            email="admin@sally.com",
            hashed_password=get_password_hash("admin123"),
            full_name="System administrator",
            role=UserRole.SuperAdmin,
            is_active=True
        )
        await admin_user.insert()
        print("Default Super admin created: admin@sally.com / admin123")
