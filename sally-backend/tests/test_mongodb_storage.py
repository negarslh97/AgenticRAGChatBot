"""
Unit tests for MongoDB storage and operations
"""

import pytest
from bson import ObjectId
from app.domain.entities import (
    KnowledgeBaseArticle, ArticleStatus, ArticleVisibility,
    ArticleCategory, ArticleTag, Category, Tag, Admin, Role
)
from app.infrastructure.knowledge_base_repository import knowledge_base_repository


@pytest.mark.unit
@pytest.mark.mongodb
class TestMongoDBConnection:
    """Test MongoDB database connection."""
    
    @pytest.mark.asyncio
    async def test_mongodb_connection_success(self, mongodb_client):
        """Test successful connection to MongoDB."""
        # Connection is already established by fixture
        assert mongodb_client is not None
        
        # Test ping
        result = await mongodb_client.admin.command('ping')
        assert result['ok'] == 1.0
    
    @pytest.mark.asyncio
    async def test_mongodb_list_collections(self, mongodb_client):
        """Test listing MongoDB collections."""
        db = mongodb_client.get_default_database()
        collections = await db.list_collection_names()
        
        # Collections list should be accessible (may be empty)
        assert isinstance(collections, list)
    
    @pytest.mark.asyncio
    async def test_mongodb_database_operations(self, mongodb_client):
        """Test basic database operations."""
        db = mongodb_client.get_default_database()
        
        # Insert test document
        test_collection = db.test_collection
        result = await test_collection.insert_one({"test_key": "test_value"})
        
        assert result.inserted_id is not None
        
        # Find document
        doc = await test_collection.find_one({"_id": result.inserted_id})
        assert doc is not None
        assert doc["test_key"] == "test_value"
        
        # Delete document
        delete_result = await test_collection.delete_one({"_id": result.inserted_id})
        assert delete_result.deleted_count == 1


@pytest.mark.integration
@pytest.mark.mongodb
class TestArticleCRUDOperations:
    """Test CRUD operations for Knowledge Base Articles."""
    
    @pytest.mark.asyncio
    async def test_create_article_success(self, test_admin, test_category):
        """Test creating a knowledge base article."""
        article = await knowledge_base_repository.create_article(
            title="Test Article",
            content_markdown="# Test\n\nThis is a test article.",
            content_html="<h1>Test</h1><p>This is a test article.</p>",
            author_id=str(test_admin.id),
            category_id=str(test_category.id),
            tag_names=["test", "article"],
            summary="Test summary",
            status=ArticleStatus.DRAFT
        )
        
        assert article is not None
        assert article.title == "Test Article"
        assert article.status == ArticleStatus.DRAFT
        assert article.author_id == str(test_admin.id)
        assert article.category is not None
        assert article.category.name == test_category.name
        assert len(article.tags) == 2
    
    @pytest.mark.asyncio
    async def test_get_article_by_id(self, test_article):
        """Test retrieving article by ID."""
        retrieved = await knowledge_base_repository.get_article_by_id(str(test_article.id))
        
        assert retrieved is not None
        assert retrieved.id == test_article.id
        assert retrieved.title == test_article.title
    
    @pytest.mark.asyncio
    async def test_get_article_nonexistent(self):
        """Test retrieving non-existent article."""
        fake_id = str(ObjectId())
        retrieved = await knowledge_base_repository.get_article_by_id(fake_id)
        
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_update_article_content(self, test_article, test_admin):
        """Test updating article content."""
        updates = {
            "title": "Updated Title",
            "content_markdown": "# Updated\n\nUpdated content.",
            "content_html": "<h1>Updated</h1><p>Updated content.</p>"
        }
        
        updated = await knowledge_base_repository.update_article(
            article_id=str(test_article.id),
            updates=updates,
            updated_by=str(test_admin.id),
            new_version=True
        )
        
        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.version == 2  # Version incremented
    
    @pytest.mark.asyncio
    async def test_publish_article(self, test_article, test_admin):
        """Test publishing an article."""
        published = await knowledge_base_repository.publish_article(
            article_id=str(test_article.id),
            visibility=ArticleVisibility.PUBLIC,
            publisher=test_admin
        )
        
        assert published is not None
        assert published.status == ArticleStatus.PUBLISHED
        assert published.visibility == ArticleVisibility.PUBLIC
        assert published.published_at is not None
        assert published.publisher_id == str(test_admin.id)
    
    @pytest.mark.asyncio
    async def test_delete_article(self, test_article):
        """Test deleting an article."""
        article_id = str(test_article.id)
        
        # Delete
        result = await knowledge_base_repository.delete_article(article_id)
        assert result is True
        
        # Verify deleted
        retrieved = await knowledge_base_repository.get_article_by_id(article_id)
        assert retrieved is None


@pytest.mark.integration
@pytest.mark.mongodb
class TestArticleQueries:
    """Test querying articles with filters."""
    
    @pytest.mark.asyncio
    async def test_get_articles_with_status_filter(self, test_admin, test_category):
        """Test getting articles filtered by status."""
        # Create published article
        await knowledge_base_repository.create_article(
            title="Published Article",
            content_markdown="# Published",
            content_html="<h1>Published</h1>",
            author_id=str(test_admin.id),
            status=ArticleStatus.PUBLISHED,
            visibility=ArticleVisibility.PUBLIC
        )
        
        # Create draft article
        await knowledge_base_repository.create_article(
            title="Draft Article",
            content_markdown="# Draft",
            content_html="<h1>Draft</h1>",
            author_id=str(test_admin.id),
            status=ArticleStatus.DRAFT
        )
        
        # Query published only
        published = await knowledge_base_repository.get_articles(
            status=ArticleStatus.PUBLISHED
        )
        
        assert len(published) >= 1
        assert all(art.status == ArticleStatus.PUBLISHED for art in published)
    
    @pytest.mark.asyncio
    async def test_get_articles_with_category_filter(self, test_admin, test_category):
        """Test getting articles filtered by category."""
        # Create article with category
        await knowledge_base_repository.create_article(
            title="Categorized Article",
            content_markdown="# Categorized",
            content_html="<h1>Categorized</h1>",
            author_id=str(test_admin.id),
            category_id=str(test_category.id),
            status=ArticleStatus.PUBLISHED
        )
        
        # Query by category
        articles = await knowledge_base_repository.get_articles(
            category_id=str(test_category.id)
        )
        
        assert len(articles) >= 1
        assert all(art.category.id == str(test_category.id) for art in articles if art.category)
    
    @pytest.mark.asyncio
    async def test_get_articles_with_pagination(self, test_admin):
        """Test pagination in article queries."""
        # Create multiple articles
        for i in range(5):
            await knowledge_base_repository.create_article(
                title=f"Article {i}",
                content_markdown=f"# Article {i}",
                content_html=f"<h1>Article {i}</h1>",
                author_id=str(test_admin.id),
                status=ArticleStatus.PUBLISHED
            )
        
        # Get first page
        page1 = await knowledge_base_repository.get_articles(limit=2, skip=0)
        assert len(page1) == 2
        
        # Get second page
        page2 = await knowledge_base_repository.get_articles(limit=2, skip=2)
        assert len(page2) == 2
        
        # Verify different articles
        page1_ids = {str(art.id) for art in page1}
        page2_ids = {str(art.id) for art in page2}
        assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.integration
@pytest.mark.mongodb
class TestArticleSearch:
    """Test article search functionality."""
    
    @pytest.mark.asyncio
    async def test_search_articles_by_title(self, test_admin):
        """Test searching articles by title."""
        # Create searchable article
        await knowledge_base_repository.create_article(
            title="Python Programming Guide",
            content_markdown="# Python Guide\n\nLearn Python programming.",
            content_html="<h1>Python Guide</h1><p>Learn Python programming.</p>",
            author_id=str(test_admin.id),
            status=ArticleStatus.PUBLISHED,
            visibility=ArticleVisibility.PUBLIC
        )
        
        # Search for "Python"
        results = await knowledge_base_repository.search_articles(
            query="Python",
            visibility_filter=[ArticleVisibility.PUBLIC]
        )
        
        # Should find at least one result
        assert len(results) >= 1
        assert any("Python" in r["title"] for r in results)
    
    @pytest.mark.asyncio
    async def test_search_articles_with_visibility_filter(self, test_admin):
        """Test searching with visibility filter."""
        # Create public article
        await knowledge_base_repository.create_article(
            title="Public Article",
            content_markdown="# Public",
            content_html="<h1>Public</h1>",
            author_id=str(test_admin.id),
            status=ArticleStatus.PUBLISHED,
            visibility=ArticleVisibility.PUBLIC
        )
        
        # Create internal article
        await knowledge_base_repository.create_article(
            title="Internal Article",
            content_markdown="# Internal",
            content_html="<h1>Internal</h1>",
            author_id=str(test_admin.id),
            status=ArticleStatus.PUBLISHED,
            visibility=ArticleVisibility.INTERNAL
        )
        
        # Search public only
        results = await knowledge_base_repository.search_articles(
            query="Article",
            visibility_filter=[ArticleVisibility.PUBLIC]
        )
        
        # Should only find public articles
        assert len(results) >= 1


@pytest.mark.integration
@pytest.mark.mongodb
class TestCategoryOperations:
    """Test category operations."""
    
    @pytest.mark.asyncio
    async def test_get_categories(self, test_category):
        """Test getting list of categories."""
        categories = await knowledge_base_repository.get_categories()
        
        assert len(categories) >= 1
        assert any(cat.id == test_category.id for cat in categories)
    
    @pytest.mark.asyncio
    async def test_get_public_categories_only(self, mongodb_client):
        """Test getting only public categories."""
        from beanie import init_beanie
        
        db = mongodb_client.get_default_database()
        await init_beanie(database=db, document_models=[Category])
        
        # Create public category
        public_cat = Category(
            name="Public Category",
            slug="public-cat",
            is_public=True
        )
        await public_cat.insert()
        
        # Create private category
        private_cat = Category(
            name="Private Category",
            slug="private-cat",
            is_public=False
        )
        await private_cat.insert()
        
        # Get public only
        categories = await knowledge_base_repository.get_categories(include_private=False)
        
        # Should only include public
        assert all(cat.is_public for cat in categories)


@pytest.mark.integration
@pytest.mark.mongodb
class TestStatistics:
    """Test statistics gathering."""
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, test_admin, test_article):
        """Test getting repository statistics."""
        # Publish the test article
        await knowledge_base_repository.publish_article(
            article_id=str(test_article.id),
            visibility=ArticleVisibility.PUBLIC,
            publisher=test_admin
        )
        
        stats = await knowledge_base_repository.get_statistics()
        
        assert "total_articles" in stats
        assert "published_articles" in stats
        assert "draft_articles" in stats
        assert stats["total_articles"] >= 1
        assert stats["published_articles"] >= 1
