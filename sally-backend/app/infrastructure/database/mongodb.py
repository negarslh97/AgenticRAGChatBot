from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings
from app.domain.entities import (
    Admin, Customer, Role, GuestSession, Conversation, Message,
    Category, Tag, KnowledgeBaseArticle, UnansweredQuestion, Feedback, ActivityLog
)
from app.core.security import get_password_hash
from app.core.permissions import create_default_roles, DEFAULT_ROLES

# Global MongoDB client
_client = None

def get_mongo_client():
    """Get or create global MongoDB client."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGODB_URL)
    return _client

async def close_mongo_client():
    """Close the global MongoDB client."""
    global _client
    if _client:
        _client.close()
        _client = None

async def init_db():
    """Initialize database connection and models for the refactored system."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGODB_URL)

    await init_beanie(
        database=_client.get_default_database(),
        document_models=[
            Admin, Customer, Role, GuestSession, Conversation, Message,
            Category, Tag, KnowledgeBaseArticle, UnansweredQuestion, Feedback, ActivityLog
        ]
    )


async def create_default_SuperAdmin():
    """Create default Super Admin user if no admins exist."""
    from app.domain.entities import Admin, Role
    from app.core.permissions import SUPER_ADMIN_ROLE_NAME
    
    admin_count = await Admin.find_all().count()
    if admin_count == 0:
        print("No admins found. Creating default super admin...")
        
        # Ensure SuperAdmin role exists
        SuperAdmin_role = await Role.find_one(Role.name == SUPER_ADMIN_ROLE_NAME)
        if not SuperAdmin_role:
            # Create default roles if they don't exist
            await create_default_roles()
            SuperAdmin_role = await Role.find_one(Role.name == SUPER_ADMIN_ROLE_NAME)
        
        if SuperAdmin_role:
            default_admin = Admin(
                email=settings.default_SuperAdmin_email,
                hashed_password=get_password_hash(settings.default_SuperAdmin_password),
                full_name="Default Super Admin",
                role_id=SuperAdmin_role.id,
                role_name=SUPER_ADMIN_ROLE_NAME
            )
            await default_admin.insert()
            print(f"Created default super admin: {settings.default_SuperAdmin_email}")
        else:
            raise RuntimeError(f"CRITICAL ERROR: {SUPER_ADMIN_ROLE_NAME} role not found! Cannot create default admin. This indicates a fundamental system setup failure.")


async def verify_database_setup():
    """Verify that the database is properly set up."""
    try:
        # Check if we can connect to the database
        client = get_mongo_client()
        await client.admin.command('ping')
        print("✓ Database connection successful")

        # Check if collections exist
        db = client.get_default_database()
        collections = await db.list_collection_names()
        
        required_collections = [
            "admins", "customers", "roles", "guest_sessions", "conversations",
            "messages", "categories", "tags", "knowledge_base_articles",
            "unanswered_questions", "feedback", "activity_logs"
        ]
        
        missing_collections = []
        for collection in required_collections:
            if collection not in collections:
                missing_collections.append(collection)
        
        if missing_collections:
            print(f"⚠ Missing collections: {missing_collections}")
            return False
        else:
            print("✓ All required collections exist")
        
        # Check if default roles exist
        from app.domain.entities import Role
        SuperAdmin_role = await Role.find_one(Role.name == "SuperAdmin")
        admin_role = await Role.find_one(Role.name == "Admin")
        
        if SuperAdmin_role and admin_role:
            print("✓ Default roles exist")
        else:
            print("⚠ Default roles missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Database verification failed: {str(e)}")
        return False


async def get_database_stats():
    """Get statistics about the database."""
    from app.domain.entities import (
        Admin, Customer, Role, GuestSession, Conversation, Message,
        Category, Tag, KnowledgeBaseArticle, UnansweredQuestion, Feedback, ActivityLog
    )

    stats = {
        "admins": await Admin.find_all().count(),
        "customers": await Customer.find_all().count(),
        "roles": await Role.find_all().count(),
        "guest_sessions": await GuestSession.find_all().count(),
        "conversations": await Conversation.find_all().count(),
        "messages": await Message.find_all().count(),
        "categories": await Category.find_all().count(),
        "tags": await Tag.find_all().count(),
        "knowledge_base_articles": await KnowledgeBaseArticle.find_all().count(),
        "unanswered_questions": await UnansweredQuestion.find_all().count(),
        "feedback": await Feedback.find_all().count(),
        "activity_logs": await ActivityLog.find_all().count()
    }

    return stats