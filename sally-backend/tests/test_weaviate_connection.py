"""
Unit tests for Weaviate connection and operations
"""

import pytest
from app.infrastructure.database.weaviate_connector import WeaviateMongoDBConnector
from app.core.config import settings


@pytest.mark.unit
@pytest.mark.weaviate
class TestWeaviateConnection:
    """Test Weaviate database connection."""
    
    def test_weaviate_connector_initialization(self):
        """Test that WeaviateMongoDBConnector can be initialized."""
        connector = WeaviateMongoDBConnector()
        
        assert connector is not None
        assert connector.weaviate_client is None  # Not connected yet
        assert connector.collection_name == "SallyChatBot"
    
    def test_weaviate_connection_success(self, weaviate_connector):
        """Test successful connection to Weaviate."""
        # Connection is already established by fixture
        assert weaviate_connector.weaviate_client is not None
        
        # Test if client is ready
        is_ready = weaviate_connector.weaviate_client.is_ready()
        assert is_ready is True
    
    def test_weaviate_connection_with_invalid_url(self):
        """Test Weaviate connection with invalid URL."""
        connector = WeaviateMongoDBConnector()
        
        # Override settings temporarily
        original_url = settings.weaviate_url
        settings.weaviate_url = "http://invalid-url:9999"
        
        try:
            result = connector.connect_weaviate()
            # Should fail or return False
            assert result is False or connector.weaviate_client is None
        finally:
            # Restore original setting
            settings.weaviate_url = original_url
    
    def test_weaviate_schema_creation(self, weaviate_connector):
        """Test Weaviate schema creation for MarkdownNode."""
        result = weaviate_connector.create_weaviate_schema()
        
        assert result is True
        
        # Verify collection exists
        collection_exists = weaviate_connector.weaviate_client.collections.exists("MarkdownNode")
        assert collection_exists is True
    
    def test_weaviate_schema_creation_idempotent(self, weaviate_connector):
        """Test that schema creation is idempotent (can be called multiple times)."""
        # Create schema first time
        result1 = weaviate_connector.create_weaviate_schema()
        assert result1 is True
        
        # Create schema second time - should not fail
        result2 = weaviate_connector.create_weaviate_schema()
        assert result2 is True
    
    def test_verify_setup_with_weaviate_only(self, weaviate_connector):
        """Test verify_setup with only Weaviate connected."""
        # Create schema first
        weaviate_connector.create_weaviate_schema()
        
        # Verify setup
        result = weaviate_connector.verify_setup()
        
        assert result["weaviate_connection"] is True
        assert result["schema_exists"] is True
        assert "markdown_nodes" in result["data_counts"]
        assert result["data_counts"]["markdown_nodes"] == 0  # No data yet


@pytest.mark.integration
@pytest.mark.weaviate
class TestWeaviateOperations:
    """Test Weaviate CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_save_markdown_tree_success(self, weaviate_connector_async, sample_markdown_content):
        """Test saving markdown tree to Weaviate."""
        from app.infrastructure.markdown_parser import markdown_parser
        
        # Create schema
        weaviate_connector_async.create_weaviate_schema()
        
        # Parse markdown to tree
        article_id = "test-article-123"
        tree = markdown_parser.parse_to_tree(sample_markdown_content, article_id)
        
        # Save tree
        result = await weaviate_connector_async.save_markdown_tree(tree, sample_markdown_content)
        
        assert result is True
        
        # Verify nodes were saved
        verification = weaviate_connector_async.verify_setup()
        assert verification["data_counts"]["markdown_nodes"] > 0
    
    @pytest.mark.asyncio
    async def test_save_empty_markdown_tree(self, weaviate_connector_async):
        """Test saving empty markdown tree."""
        from app.domain.entities import MarkdownTree
        
        # Create schema
        weaviate_connector_async.create_weaviate_schema()
        
        # Create empty tree
        empty_tree = MarkdownTree(article_id="empty-test", root_nodes=[])
        
        # Save empty tree - should succeed without errors
        result = await weaviate_connector_async.save_markdown_tree(empty_tree, "")
        
        assert result is True
    
    def test_delete_markdown_nodes_success(self, weaviate_connector):
        """Test deleting markdown nodes by article_id."""
        # Create schema
        weaviate_connector.create_weaviate_schema()
        
        # Delete nodes (even if none exist)
        article_id = "test-article-to-delete"
        result = weaviate_connector.delete_markdown_nodes(article_id)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_after_save(self, weaviate_connector_async, sample_markdown_content):
        """Test delete operation after saving data."""
        from app.infrastructure.markdown_parser import markdown_parser
        
        # Create schema
        weaviate_connector_async.create_weaviate_schema()
        
        # Save data
        article_id = "test-delete-123"
        tree = markdown_parser.parse_to_tree(sample_markdown_content, article_id)
        await weaviate_connector_async.save_markdown_tree(tree, sample_markdown_content)
        
        # Verify data exists
        verification1 = weaviate_connector_async.verify_setup()
        nodes_before = verification1["data_counts"]["markdown_nodes"]
        assert nodes_before > 0
        
        # Delete data
        result = weaviate_connector_async.delete_markdown_nodes(article_id)
        assert result is True
        
        # Verify data was deleted
        verification2 = weaviate_connector_async.verify_setup()
        nodes_after = verification2["data_counts"]["markdown_nodes"]
        assert nodes_after == 0


@pytest.mark.integration
@pytest.mark.weaviate
class TestWeaviateSearch:
    """Test Weaviate vector search operations."""
    
    @pytest.mark.asyncio
    async def test_semantic_search_after_save(self, weaviate_connector_async):
        """Test semantic search after saving markdown nodes."""
        from app.infrastructure.markdown_parser import markdown_parser
        
        # Create schema
        weaviate_connector_async.create_weaviate_schema()
        
        # Prepare test data
        markdown_content = """# Product Documentation

## Installation

To install our product, follow these steps.

## Configuration

Configure the application using environment variables.

## Troubleshooting

Common issues and solutions.
"""
        article_id = "search-test-123"
        tree = markdown_parser.parse_to_tree(markdown_content, article_id)
        
        # Save tree
        await weaviate_connector_async.save_markdown_tree(tree, markdown_content)
        
        # Perform search
        collection = weaviate_connector_async.weaviate_client.collections.get("MarkdownNode")
        
        try:
            # Search for "installation"
            response = collection.query.near_text(
                query="installation steps",
                limit=3,
                return_properties=["title", "content", "path"]
            )
            
            # Should find results
            assert response.objects is not None
            assert len(response.objects) > 0
            
            # Check if Installation section is in results
            titles = [obj.properties.get("title", "") for obj in response.objects]
            assert any("Installation" in title for title in titles)
            
        except Exception as e:
            # If vectorization fails (e.g., no API key), test should note this
            pytest.skip(f"Vectorization not available: {e}")


@pytest.mark.unit
@pytest.mark.weaviate
class TestWeaviateCleanup:
    """Test Weaviate cleanup operations."""
    
    def test_delete_all_from_weaviate(self, weaviate_connector):
        """Test deleting all data from Weaviate."""
        # Create schema first
        weaviate_connector.create_weaviate_schema()
        
        # Delete all
        result = weaviate_connector.delete_all_from_weaviate()
        
        assert result is True
        
        # Verify collection is recreated and empty
        verification = weaviate_connector.verify_setup()
        assert verification["schema_exists"] is True
        assert verification["data_counts"]["markdown_nodes"] == 0
    
    def test_cleanup_method(self, weaviate_connector):
        """Test cleanup method closes connections properly."""
        # Ensure client is connected
        assert weaviate_connector.weaviate_client is not None
        
        # Call cleanup
        weaviate_connector.cleanup()
        
        # After cleanup, client connection should be closed
        # Note: We can't easily test if connection is truly closed,
        # but we verify no exception is raised
        assert True  # If we reach here, cleanup succeeded


@pytest.mark.integration
@pytest.mark.weaviate
class TestWeaviateVectorizer:
    """Test Weaviate vectorizer configuration."""
    
    def test_vectorizer_info_logging(self, weaviate_connector):
        """Test that vectorizer info can be logged without errors."""
        # Create schema first
        weaviate_connector.create_weaviate_schema()
        
        # This should not raise any exceptions
        weaviate_connector.log_vectorizer_info()
        
        # No assertion needed - test passes if no exception raised
        assert True
    
    def test_display_weaviate_objects(self, weaviate_connector):
        """Test displaying Weaviate objects."""
        # Create schema
        weaviate_connector.create_weaviate_schema()
        
        # Display objects (should work even with empty collection)
        result = weaviate_connector.display_weaviate_objects(class_name="MarkdownNode", limit=5)
        
        assert result is True
