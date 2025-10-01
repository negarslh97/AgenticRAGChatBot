"""
Integration tests for Weaviate and MongoDB synchronization
"""

import pytest
from app.infrastructure.database.weaviate_connector import WeaviateMongoDBConnector
from app.infrastructure.markdown_parser import markdown_parser
from app.infrastructure.knowledge_base_repository import knowledge_base_repository
from app.domain.entities import ArticleStatus, ArticleVisibility


@pytest.mark.integration
@pytest.mark.weaviate
@pytest.mark.mongodb
@pytest.mark.slow
class TestWeaviateMongoDBSync:
    """Test synchronization between Weaviate and MongoDB."""
    
    @pytest.mark.asyncio
    async def test_both_connections(self, weaviate_connector_async):
        """Test that both MongoDB and Weaviate connections work."""
        # Connections are established by fixture
        assert weaviate_connector_async.mongodb_client is not None
        assert weaviate_connector_async.weaviate_client is not None
        
        # Test MongoDB ping
        result = await weaviate_connector_async.mongodb_client.admin.command('ping')
        assert result['ok'] == 1.0
        
        # Test Weaviate ready
        is_ready = weaviate_connector_async.weaviate_client.is_ready()
        assert is_ready is True
    
    @pytest.mark.asyncio
    async def test_setup_and_verify(self, weaviate_connector_async):
        """Test complete setup and verification."""
        result = await weaviate_connector_async.setup_and_verify()
        
        assert result is True
        
        # Check verification details
        verification = weaviate_connector_async.verify_setup()
        assert verification["weaviate_connection"] is True
        assert verification["mongodb_connection"] is True
        assert verification["schema_exists"] is True


@pytest.mark.integration
@pytest.mark.weaviate
@pytest.mark.mongodb
@pytest.mark.slow
class TestArticleSyncToWeaviate:
    """Test article synchronization to Weaviate."""
    
    @pytest.mark.asyncio
    async def test_create_article_syncs_to_weaviate(
        self, 
        weaviate_connector_async,
        test_admin,
        test_category
    ):
        """Test that creating a published article syncs to Weaviate."""
        # Setup Weaviate schema
        weaviate_connector_async.create_weaviate_schema()
        
        # Create published article
        article = await knowledge_base_repository.create_article(
            title="Sync Test Article",
            content_markdown="# Introduction\n\nThis article should sync to Weaviate.\n\n## Details\n\nMore details here.",
            content_html="<h1>Introduction</h1><p>This article should sync to Weaviate.</p>",
            author_id=str(test_admin.id),
            category_id=str(test_category.id),
            summary="Test sync article",
            status=ArticleStatus.PUBLISHED,
            visibility=ArticleVisibility.PUBLIC
        )
        
        # Check if nodes exist in Weaviate
        verification = weaviate_connector_async.verify_setup()
        nodes_count = verification["data_counts"]["markdown_nodes"]
        
        # Should have at least 2 nodes (Introduction and Details sections)
        assert nodes_count >= 2
        
        # Verify we can query the nodes
        collection = weaviate_connector_async.weaviate_client.collections.get("MarkdownNode")
        response = collection.query.fetch_objects(
            limit=10,
            return_properties=["article_id", "title", "content"]
        )
        
        # Find nodes for our article
        article_nodes = [
            obj for obj in response.objects 
            if obj.properties.get("article_id") == str(article.id)
        ]
        
        assert len(article_nodes) >= 2
    
    @pytest.mark.asyncio
    async def test_update_article_syncs_to_weaviate(
        self,
        weaviate_connector_async,
        test_admin,
        test_article
    ):
        """Test that updating a published article updates Weaviate."""
        # Setup Weaviate
        weaviate_connector_async.create_weaviate_schema()
        
        # Publish the article first
        published = await knowledge_base_repository.publish_article(
            article_id=str(test_article.id),
            visibility=ArticleVisibility.PUBLIC,
            publisher=test_admin
        )
        
        # Get initial node count
        verification1 = weaviate_connector_async.verify_setup()
        initial_count = verification1["data_counts"]["markdown_nodes"]
        
        # Update the article
        updates = {
            "content_markdown": "# Updated Header\n\nUpdated content.\n\n## New Section\n\nNew content here.",
            "content_html": "<h1>Updated Header</h1><p>Updated content.</p>"
        }
        
        await knowledge_base_repository.update_article(
            article_id=str(published.id),
            updates=updates,
            updated_by=str(test_admin.id),
            new_version=True
        )
        
        # Verify nodes were updated (count may change)
        verification2 = weaviate_connector_async.verify_setup()
        updated_count = verification2["data_counts"]["markdown_nodes"]
        
        # Should still have nodes
        assert updated_count > 0
    
    @pytest.mark.asyncio
    async def test_delete_article_removes_from_weaviate(
        self,
        weaviate_connector_async,
        test_admin,
        test_article
    ):
        """Test that deleting an article removes nodes from Weaviate."""
        # Setup Weaviate
        weaviate_connector_async.create_weaviate_schema()
        
        # Publish the article
        published = await knowledge_base_repository.publish_article(
            article_id=str(test_article.id),
            visibility=ArticleVisibility.PUBLIC,
            publisher=test_admin
        )
        
        article_id = str(published.id)
        
        # Verify nodes exist
        verification1 = weaviate_connector_async.verify_setup()
        assert verification1["data_counts"]["markdown_nodes"] > 0
        
        # Delete the article
        await knowledge_base_repository.delete_article(article_id)
        
        # Verify nodes are removed
        collection = weaviate_connector_async.weaviate_client.collections.get("MarkdownNode")
        response = collection.query.fetch_objects(
            limit=100,
            return_properties=["article_id"]
        )
        
        # Should not find any nodes for this article
        article_nodes = [
            obj for obj in response.objects 
            if obj.properties.get("article_id") == article_id
        ]
        
        assert len(article_nodes) == 0
    
    @pytest.mark.asyncio
    async def test_draft_article_not_synced_to_weaviate(
        self,
        weaviate_connector_async,
        test_admin
    ):
        """Test that draft articles are NOT synced to Weaviate."""
        # Setup Weaviate
        weaviate_connector_async.create_weaviate_schema()
        
        # Get initial count
        verification1 = weaviate_connector_async.verify_setup()
        initial_count = verification1["data_counts"]["markdown_nodes"]
        
        # Create draft article
        draft_article = await knowledge_base_repository.create_article(
            title="Draft Article",
            content_markdown="# Draft\n\nThis is a draft.",
            content_html="<h1>Draft</h1><p>This is a draft.</p>",
            author_id=str(test_admin.id),
            status=ArticleStatus.DRAFT  # Draft status
        )
        
        # Verify no new nodes added
        verification2 = weaviate_connector_async.verify_setup()
        after_count = verification2["data_counts"]["markdown_nodes"]
        
        assert after_count == initial_count  # No change


@pytest.mark.integration
@pytest.mark.weaviate
@pytest.mark.mongodb
@pytest.mark.slow
class TestMigration:
    """Test migration of articles from MongoDB to Weaviate."""
    
    @pytest.mark.asyncio
    async def test_migrate_single_article(
        self,
        weaviate_connector_async,
        test_admin
    ):
        """Test migrating a single article."""
        # Create a published article in MongoDB
        article = await knowledge_base_repository.create_article(
            title="Migration Test",
            content_markdown="# Migration\n\nTest migration.\n\n## Section 2\n\nMore content.",
            content_html="<h1>Migration</h1><p>Test migration.</p>",
            author_id=str(test_admin.id),
            status=ArticleStatus.PUBLISHED,
            visibility=ArticleVisibility.PUBLIC
        )
        
        # Setup Weaviate
        weaviate_connector_async.create_weaviate_schema()
        
        # Clear any existing nodes
        weaviate_connector_async.delete_all_from_weaviate()
        weaviate_connector_async.create_weaviate_schema()
        
        # Debug: Check if article exists before migration
        debug_db = weaviate_connector_async.mongodb_client.get_default_database()
        debug_article = await debug_db.knowledge_base_articles.find_one({"_id": article.id})
        if debug_article:
            print(f"✅ Debug: Article found before migration - ID: {article.id}, Title: {debug_article['title']}")
        else:
            print(f"❌ Debug: Article NOT found before migration - ID: {article.id}")

        # Migrate the article
        result = await weaviate_connector_async.migrate_article_with_vectorization(str(article.id))

        assert result is True

        # Verify nodes exist
        verification = weaviate_connector_async.verify_setup()
        assert verification["data_counts"]["markdown_nodes"] >= 2
    
    @pytest.mark.asyncio
    async def test_migrate_all_published_articles(
        self,
        weaviate_connector_async,
        test_admin
    ):
        """Test migrating all published articles."""
        # Create multiple published articles
        for i in range(3):
            await knowledge_base_repository.create_article(
                title=f"Article {i}",
                content_markdown=f"# Article {i}\n\nContent for article {i}.",
                content_html=f"<h1>Article {i}</h1><p>Content for article {i}.</p>",
                author_id=str(test_admin.id),
                status=ArticleStatus.PUBLISHED,
                visibility=ArticleVisibility.PUBLIC
            )
        
        # Setup Weaviate
        weaviate_connector_async.create_weaviate_schema()
        weaviate_connector_async.delete_all_from_weaviate()
        weaviate_connector_async.create_weaviate_schema()
        
        # Migrate all
        result = await weaviate_connector_async.migrate_all_data()
        
        assert result is True
        
        # Verify all articles migrated
        verification = weaviate_connector_async.verify_setup()
        assert verification["data_counts"]["markdown_nodes"] >= 3


@pytest.mark.integration
@pytest.mark.weaviate
@pytest.mark.mongodb
class TestMarkdownParsing:
    """Test markdown parsing and tree structure."""
    
    @pytest.mark.asyncio
    async def test_parse_markdown_to_tree(self, sample_markdown_content):
        """Test parsing markdown content to tree structure."""
        tree = markdown_parser.parse_to_tree(sample_markdown_content, "test-article")
        
        assert tree is not None
        assert tree.article_id == "test-article"
        assert len(tree.root_nodes) > 0
        
        # Get all nodes
        all_nodes = tree.get_all_nodes()
        assert len(all_nodes) > 0
        
        # Check node properties
        for node in all_nodes:
            assert node.id is not None
            assert node.title is not None
            assert node.level >= 1 and node.level <= 6
            assert node.path is not None
    
    @pytest.mark.asyncio
    async def test_markdown_tree_hierarchy(self, sample_markdown_content):
        """Test that markdown tree maintains proper hierarchy."""
        tree = markdown_parser.parse_to_tree(sample_markdown_content, "test-article")
        
        # Check root nodes are level 1
        for root in tree.root_nodes:
            assert root.level == 1
            assert root.parent_id == "-1"
        
        # Check children have correct parent relationships
        all_nodes = tree.get_all_nodes()
        for node in all_nodes:
            if node.children:
                for child in node.children:
                    assert child.parent_id == node.id
                    assert child.level > node.level
    
    @pytest.mark.asyncio
    async def test_save_parsed_tree_to_weaviate(
        self,
        weaviate_connector_async,
        sample_markdown_content
    ):
        """Test saving parsed markdown tree to Weaviate."""
        # Setup
        weaviate_connector_async.create_weaviate_schema()
        
        # Parse
        tree = markdown_parser.parse_to_tree(sample_markdown_content, "parse-test")
        
        # Save
        result = await weaviate_connector_async.save_markdown_tree(tree, sample_markdown_content)
        
        assert result is True
        
        # Verify
        verification = weaviate_connector_async.verify_setup()
        assert verification["data_counts"]["markdown_nodes"] > 0
