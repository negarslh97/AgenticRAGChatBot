"""
Test configuration and fixtures for SallyBot tests
"""

import pytest
import pytest_asyncio
import asyncio
import os
import sys
from typing import AsyncGenerator, Generator
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.domain.entities import (
    Admin, Customer, Role, KnowledgeBaseArticle, 
    Category, Tag, ArticleStatus, ArticleVisibility
)
from app.infrastructure.database.weaviate_connector import WeaviateMongoDBConnector


# ==================== Pytest Configuration ====================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (requires external services)"
    )
    config.addinivalue_line(
        "markers", "weaviate: marks tests that require Weaviate"
    )
    config.addinivalue_line(
        "markers", "mongodb: marks tests that require MongoDB"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== Database Fixtures ====================

@pytest_asyncio.fixture(scope="function")
async def mongodb_client() -> AsyncGenerator[AsyncIOMotorClient, None]:
    """
    Provide MongoDB client for testing.
    Uses test database to avoid affecting production data.
    """
    # Use test database
    test_db_url = os.getenv("TEST_DATABASE_URL", "mongodb://localhost:27017/SallyChatBot_Test")
    client = AsyncIOMotorClient(test_db_url)
    
    # Wait for connection
    try:
        await client.admin.command('ping')
        print(f"✅ Connected to test MongoDB: {test_db_url}")
    except Exception as e:
        pytest.skip(f"MongoDB not available: {e}")
    
    yield client
    
    # Cleanup: Drop test database after tests
    db_name = client.get_default_database().name
    await client.drop_database(db_name)
    client.close()
    print(f"🧹 Cleaned up test database: {db_name}")


@pytest.fixture(scope="function")
def weaviate_connector() -> Generator[WeaviateMongoDBConnector, None, None]:
    """
    Provide Weaviate connector for testing.
    Requires Weaviate to be running.
    """
    connector = WeaviateMongoDBConnector()
    
    # Test connection
    try:
        connected = connector.connect_weaviate()
        if not connected:
            pytest.skip("Weaviate connection failed")
        print("✅ Connected to Weaviate for testing")
    except Exception as e:
        pytest.skip(f"Weaviate not available: {e}")
    
    yield connector
    
    # Cleanup
    try:
        connector.cleanup()
        print("🧹 Cleaned up Weaviate connector")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")


@pytest_asyncio.fixture(scope="function")
async def weaviate_connector_async() -> AsyncGenerator[WeaviateMongoDBConnector, None]:
    """
    Provide async Weaviate connector for testing with MongoDB connection.
    """
    connector = WeaviateMongoDBConnector()
    
    # Test connections
    try:
        mongodb_ok = await connector.connect_mongodb()
        weaviate_ok = connector.connect_weaviate()

        if not mongodb_ok:
            pytest.skip("Failed to connect to MongoDB")

        if not weaviate_ok:
            pytest.skip("Failed to connect to Weaviate")

        print("✅ Connected to both MongoDB and Weaviate for testing")
    except Exception as e:
        pytest.skip(f"Services not available: {e}")
    
    yield connector
    
    # Cleanup
    try:
        connector.cleanup()
        print("🧹 Cleaned up async connector")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")


# ==================== Entity Fixtures ====================

@pytest_asyncio.fixture
async def test_role(mongodb_client) -> Role:
    """Create a test role."""
    from beanie import init_beanie
    
    db = mongodb_client.get_default_database()
    await init_beanie(database=db, document_models=[Role, Admin, Customer, KnowledgeBaseArticle, Category, Tag])
    
    role = Role(
        name="TestAdmin",
        description="Test admin role",
        permissions=[],
        is_active=True
    )
    await role.insert()
    return role


@pytest_asyncio.fixture
async def test_admin(test_role: Role) -> Admin:
    """Create or get a test admin user."""
    # First check if admin already exists
    existing_admin = await Admin.find_one({"email": "test_admin@test.com"})

    if existing_admin:
        return existing_admin

    # Create new admin if doesn't exist
    admin = Admin(
        email="test_admin@test.com",
        hashed_password="$2b$12$test_hash",
        full_name="Test Admin",
        role_id=str(test_role.id),
        role_name=test_role.name,
        is_active=True
    )
    await admin.insert()
    return admin


@pytest_asyncio.fixture
async def test_category(mongodb_client) -> Category:
    """Create a test category."""
    from beanie import init_beanie
    
    db = mongodb_client.get_default_database()
    await init_beanie(database=db, document_models=[Category])
    
    category = Category(
        name="Test Category",
        slug="test-category",
        description="Test category for testing",
        is_public=True
    )
    await category.insert()
    return category


@pytest_asyncio.fixture
async def test_article(test_admin: Admin, test_category: Category) -> KnowledgeBaseArticle:
    """Create a test knowledge base article."""
    from app.domain.entities import ArticleCategory
    
    article = KnowledgeBaseArticle(
        title="Test Article",
        content_markdown="# Test Header\n\nThis is test content.\n\n## Subheader\n\nMore test content.",
        content_html="<h1>Test Header</h1><p>This is test content.</p><h2>Subheader</h2><p>More test content.</p>",
        summary="Test article summary",
        category=ArticleCategory(
            id=str(test_category.id),
            name=test_category.name,
            slug=test_category.slug
        ),
        status=ArticleStatus.DRAFT,
        visibility=None,
        author_id=str(test_admin.id),
        version=1
    )
    await article.insert()
    return article


@pytest.fixture
def sample_markdown_content() -> str:
    """Provide sample markdown content for testing."""
    return """# Main Title

This is the introduction to the document.

## Section 1

Content for section 1.

### Subsection 1.1

Details for subsection 1.1.

### Subsection 1.2

Details for subsection 1.2.

## Section 2

Content for section 2.

# Another Main Title

More content here.
"""


# ==================== Environment Fixtures ====================

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    test_env = {
        "DATABASE_URL": "mongodb://localhost:27017/SallyChatBot_Test",
        "WEAVIATE_URL": "http://localhost:8080",
        "OPENAI_API_KEY": "test-key-12345",
        "Embedder_API_KEY": "test-embedder-key-12345",
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    
    return test_env


# ==================== Helper Fixtures ====================

@pytest.fixture
def cleanup_weaviate_data(weaviate_connector: WeaviateMongoDBConnector):
    """Clean up Weaviate data after test."""
    yield
    
    # Cleanup after test
    try:
        weaviate_connector.delete_all_from_weaviate()
        print("🧹 Cleaned up Weaviate test data")
    except Exception as e:
        print(f"⚠️ Failed to cleanup Weaviate: {e}")


@pytest_asyncio.fixture
async def cleanup_mongodb_data(mongodb_client: AsyncIOMotorClient):
    """Clean up MongoDB test data after test."""
    yield
    
    # Cleanup after test
    try:
        db = mongodb_client.get_default_database()
        collections = await db.list_collection_names()
        
        for collection_name in collections:
            await db[collection_name].delete_many({})
        
        print(f"🧹 Cleaned up {len(collections)} MongoDB collections")
    except Exception as e:
        print(f"⚠️ Failed to cleanup MongoDB: {e}")
