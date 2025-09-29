"""
Test configuration and fixtures for SallyBot API tests.
"""
import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
import os
from faker import Faker

from app.infrastructure.database.mongodb import init_db
from app.core.permissions import create_default_roles
from app.core.config import settings
from app.domain.entities import (
    Admin, Customer, Role, Ticket, TicketReply, KnowledgeBaseArticle,
    Category, Tag, GuestSession, Conversation, Message, ActivityLog, Feedback
)
from main import app


# Test database settings
TEST_DATABASE_URL = "mongodb://localhost:27017/test_sally_db"
TEST_DATABASE_NAME = "test_sally_db"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Create test database connection and setup."""
    # Override settings for testing
    original_db_url = getattr(settings, 'database_url', None)

    # Set the test database URL (which includes the database name)
    settings.database_url = TEST_DATABASE_URL

    # Initialize test database
    await init_db()

    # Create default roles
    await create_default_roles()

    yield

    # Cleanup: Drop test database
    client = AsyncIOMotorClient(TEST_DATABASE_URL)
    await client.drop_database(TEST_DATABASE_NAME)
    client.close()

    # Restore original settings
    if original_db_url:
        settings.database_url = original_db_url


@pytest_asyncio.fixture
async def client(test_db):
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
def faker():
    """Faker instance for generating test data."""
    return Faker('fa_IR')  # Persian locale for more realistic test data


@pytest_asyncio.fixture
async def super_admin_user(test_db, faker):
    """Create a test super admin user."""
    from app.core.security import get_password_hash

    # Get SuperAdmin role
    super_admin_role = await Role.find_one({"name": "SuperAdmin"})
    assert super_admin_role, "SuperAdmin role not found"

    admin = Admin(
        email=faker.email(),
        hashed_password=get_password_hash("testpassword123"),
        full_name=faker.name(),
        role_id=str(super_admin_role.id),
        role_name=super_admin_role.name
    )
    await admin.insert()
    return admin


@pytest_asyncio.fixture
async def admin_user(test_db, faker):
    """Create a test admin user."""
    from app.core.security import get_password_hash

    # Get Admin role
    admin_role = await Role.find_one({"name": "Admin"})
    assert admin_role, "Admin role not found"

    admin = Admin(
        email=faker.email(),
        hashed_password=get_password_hash("testpassword123"),
        full_name=faker.name(),
        role_id=str(admin_role.id),
        role_name=admin_role.name
    )
    await admin.insert()
    return admin


@pytest_asyncio.fixture
async def customer_user(test_db, faker):
    """Create a test customer user."""
    from app.core.security import get_password_hash

    customer = Customer(
        email=faker.email(),
        hashed_password=get_password_hash("testpassword123"),
        full_name=faker.name()
    )
    await customer.insert()
    return customer


@pytest.fixture
def auth_headers():
    """Helper fixture to create authorization headers."""
    def _create_headers(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    return _create_headers


@pytest_asyncio.fixture
async def super_admin_token(super_admin_user):
    """Create JWT token for super admin."""
    from app.core.security import create_access_token
    from datetime import timedelta

    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    token = create_access_token(
        data={"sub": str(super_admin_user.id), "type": "SuperAdmin"},
        expires_delta=access_token_expires
    )
    return token


@pytest_asyncio.fixture
async def admin_token(admin_user):
    """Create JWT token for admin."""
    from app.core.security import create_access_token
    from datetime import timedelta

    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    token = create_access_token(
        data={"sub": str(admin_user.id), "type": "Admin"},
        expires_delta=access_token_expires
    )
    return token


@pytest_asyncio.fixture
async def customer_token(customer_user):
    """Create JWT token for customer."""
    from app.core.security import create_access_token
    from datetime import timedelta

    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    token = create_access_token(
        data={"sub": str(customer_user.id), "type": "Customer"},
        expires_delta=access_token_expires
    )
    return token


@pytest_asyncio.fixture
async def test_ticket(customer_user, faker):
    """Create a test ticket."""
    ticket = Ticket(
        customer_id=str(customer_user.id),
        title=faker.sentence(),
        description=faker.paragraph(),
        priority="medium"
    )
    await ticket.insert()
    return ticket


@pytest_asyncio.fixture
async def test_category(faker):
    """Create a test knowledge base category."""
    category = Category(
        name=faker.word(),
        slug=faker.slug(),
        description=faker.sentence(),
        is_public=True
    )
    await category.insert()
    return category


@pytest_asyncio.fixture
async def test_article(test_category, admin_user, faker):
    """Create a test knowledge base article."""
    from app.domain.entities import ArticleStatus, ArticleVisibility, ArticleCategory

    article = KnowledgeBaseArticle(
        title=faker.sentence(),
        content_markdown=faker.paragraph(),
        content_html=f"<p>{faker.paragraph()}</p>",
        summary=faker.sentence(),
        category=ArticleCategory(id=str(test_category.id), name=test_category.name, slug=test_category.slug),
        tags=[],
        status=ArticleStatus.DRAFT,
        visibility=ArticleVisibility.INTERNAL,
        author_id=str(admin_user.id)
    )
    await article.insert()
    return article
