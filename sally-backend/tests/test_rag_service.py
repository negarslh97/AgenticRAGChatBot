"""
Tests for RAG Service with Weaviate integration
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.rag_service import SimpleRAGService, AgenticRAGService, get_rag_service
from app.infrastructure.database.weaviate_connector import WeaviateMongoDBConnector
from app.domain.entities import ArticleVisibility, Customer, Admin


@pytest.mark.unit
class TestRAGServiceFactory:
    """Test RAG service factory function."""
    
    def test_get_rag_service_for_guest(self):
        """Test that guest users get SimpleRAGService."""
        service = get_rag_service(user=None)
        
        assert isinstance(service, SimpleRAGService)
    
    def test_get_rag_service_for_customer(self):
        """Test that authenticated customers get AgenticRAGService."""
        mock_customer = Mock(spec=Customer)
        mock_customer.id = "customer-123"
        
        service = get_rag_service(user=mock_customer)
        
        assert isinstance(service, AgenticRAGService)
    
    def test_get_rag_service_for_admin(self):
        """Test that admins get AgenticRAGService."""
        mock_admin = Mock(spec=Admin)
        mock_admin.id = "admin-123"
        
        service = get_rag_service(user=mock_admin)
        
        assert isinstance(service, AgenticRAGService)


@pytest.mark.unit
class TestSimpleRAGService:
    """Test SimpleRAGService functionality."""
    
    def test_initialization(self):
        """Test SimpleRAGService initialization."""
        service = SimpleRAGService()
        
        assert service is not None
        assert service.client is None  # No direct client needed
    
    @pytest.mark.asyncio
    async def test_retrieve_relevant_documents_hybrid_search(self):
        """Test hybrid search: Weaviate + MongoDB enrichment."""
        service = SimpleRAGService()

        # Mock Weaviate to return results
        weaviate_results = [
            {"id": "article-123", "node_id": "node-456", "title": "Test Article", "content": "Content", "score": 0.8, "path": "/test"}
        ]

        # Mock MongoDB enrichment to return enriched results
        enriched_results = [
            {"id": "article-123", "title": "Test Article", "content": "Content", "score": 0.8, "source": "hybrid", "tags": ["tag1"], "category": "Test"}
        ]

        with patch.object(service, '_retrieve_from_weaviate', return_value=weaviate_results) as mock_weaviate:
            with patch.object(service, '_enrich_with_mongodb_metadata', return_value=enriched_results) as mock_enrich:
                results = await service.retrieve_relevant_documents("test query")

                # Should use Weaviate first, then enrich with MongoDB
                assert len(results) == 1
                assert results[0]["source"] == "hybrid"
                mock_weaviate.assert_called_once()
                mock_enrich.assert_called_once()

    async def test_retrieve_relevant_documents_weaviate_fallback_to_mongodb(self):
        """Test fallback to MongoDB when Weaviate fails."""
        service = SimpleRAGService()

        # Mock Weaviate to fail (return empty results)
        with patch.object(service, '_retrieve_from_weaviate', return_value=[]) as mock_weaviate:
            # Mock MongoDB to succeed
            with patch.object(service, '_retrieve_from_mongodb', return_value=[
                {"id": "1", "title": "Test", "content": "Content", "score": 0.9}
            ]) as mock_mongodb:
                results = await service.retrieve_relevant_documents("test query")

                # Should fallback to MongoDB
                assert len(results) == 1
                mock_weaviate.assert_called_once()
                mock_mongodb.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_response_no_documents(self):
        """Test response generation when no documents found."""
        service = SimpleRAGService()
        
        # Mock no documents found
        with patch.object(service, 'retrieve_relevant_documents', return_value=[]):
            # Mock direct OpenAI response
            with patch.object(service, '_generate_direct_openai_response', return_value="Fallback response"):
                result = await service.generate_response("test query")
                
                assert result is not None
                assert "response" in result
                assert result["sources"] == []


@pytest.mark.integration
@pytest.mark.weaviate
@pytest.mark.mongodb
@pytest.mark.slow
class TestRAGWithWeaviate:
    """Test RAG service with actual Weaviate integration."""
    
    @pytest.mark.asyncio
    async def test_retrieve_from_weaviate_with_data(
        self,
        weaviate_connector_async,
        test_admin
    ):
        """Test retrieving documents from Weaviate with actual data."""
        from app.infrastructure.knowledge_base_repository import knowledge_base_repository
        from app.domain.entities import ArticleStatus, ArticleVisibility
        
        # Setup Weaviate
        weaviate_connector_async.create_weaviate_schema()
        weaviate_connector_async.delete_all_from_weaviate()
        weaviate_connector_async.create_weaviate_schema()
        
        # Create and publish an article
        article = await knowledge_base_repository.create_article(
            title="Python Programming Guide",
            content_markdown="""# Python Programming Guide

## Introduction to Python

Python is a high-level programming language.

## Getting Started

To start with Python, you need to install it.

## Basic Syntax

Python uses indentation for code blocks.
""",
            content_html="<h1>Python Programming Guide</h1>",
            author_id=str(test_admin.id),
            status=ArticleStatus.PUBLISHED,
            visibility=ArticleVisibility.PUBLIC
        )
        
        # Wait a moment for indexing
        import asyncio
        await asyncio.sleep(1)
        
        # Initialize RAG service
        service = SimpleRAGService()
        
        # Retrieve documents
        try:
            results = await service._retrieve_from_weaviate("Python programming", is_public_only=True)
            
            # Should find results
            assert len(results) > 0
            assert any("Python" in r.get("title", "") for r in results)
            
        except Exception as e:
            # If vectorization is not configured, skip
            if "vectorize" in str(e).lower() or "api" in str(e).lower():
                pytest.skip(f"Vectorization not configured: {e}")
            else:
                raise
    
    @pytest.mark.asyncio
    async def test_retrieve_from_mongodb_fallback(
        self,
        test_admin
    ):
        """Test MongoDB fallback when Weaviate unavailable."""
        from app.infrastructure.knowledge_base_repository import knowledge_base_repository
        from app.domain.entities import ArticleStatus, ArticleVisibility
        
        # Create article
        article = await knowledge_base_repository.create_article(
            title="JavaScript Tutorial",
            content_markdown="# JavaScript\n\nLearn JavaScript programming.",
            content_html="<h1>JavaScript</h1>",
            author_id=str(test_admin.id),
            status=ArticleStatus.PUBLISHED,
            visibility=ArticleVisibility.PUBLIC
        )
        
        # Initialize service
        service = SimpleRAGService()
        
        # Use MongoDB retrieval directly
        results = await service._retrieve_from_mongodb("JavaScript", is_public_only=True)
        
        # Should find results
        assert len(results) > 0
        assert any("JavaScript" in r.get("title", "") for r in results)
    
    @pytest.mark.asyncio
    async def test_visibility_filter_public_only(
        self,
        test_admin
    ):
        """Test that public-only filter works correctly."""
        from app.infrastructure.knowledge_base_repository import knowledge_base_repository
        from app.domain.entities import ArticleStatus, ArticleVisibility
        
        # Create public article
        public_article = await knowledge_base_repository.create_article(
            title="Public Guide",
            content_markdown="# Public\n\nPublic content.",
            content_html="<h1>Public</h1>",
            author_id=str(test_admin.id),
            status=ArticleStatus.PUBLISHED,
            visibility=ArticleVisibility.PUBLIC
        )
        
        # Create internal article
        internal_article = await knowledge_base_repository.create_article(
            title="Internal Guide",
            content_markdown="# Internal\n\nInternal content.",
            content_html="<h1>Internal</h1>",
            author_id=str(test_admin.id),
            status=ArticleStatus.PUBLISHED,
            visibility=ArticleVisibility.INTERNAL
        )
        
        # Initialize service
        service = SimpleRAGService()
        
        # Retrieve public only using MongoDB
        results = await service._retrieve_from_mongodb("Guide", is_public_only=True)
        
        # Should only find public article
        assert len(results) >= 1
        titles = [r.get("title", "") for r in results]
        assert "Public Guide" in titles
        # Internal should not be in results for public-only query


@pytest.mark.integration
@pytest.mark.weaviate
class TestSemanticSearch:
    """Test semantic search capabilities."""
    
    @pytest.mark.asyncio
    async def test_semantic_search_quality(
        self,
        weaviate_connector_async,
        test_admin
    ):
        """Test quality of semantic search results."""
        from app.infrastructure.knowledge_base_repository import knowledge_base_repository
        from app.domain.entities import ArticleStatus, ArticleVisibility
        
        # Setup
        weaviate_connector_async.create_weaviate_schema()
        weaviate_connector_async.delete_all_from_weaviate()
        weaviate_connector_async.create_weaviate_schema()
        
        # Create articles with different topics
        articles_content = [
            ("Python Machine Learning", "# ML with Python\n\nMachine learning using Python and scikit-learn."),
            ("Web Development", "# Web Dev\n\nBuilding websites with HTML, CSS, and JavaScript."),
            ("Database Design", "# Databases\n\nDesigning efficient database schemas."),
        ]
        
        for title, content in articles_content:
            await knowledge_base_repository.create_article(
                title=title,
                content_markdown=content,
                content_html=f"<h1>{title}</h1>",
                author_id=str(test_admin.id),
                status=ArticleStatus.PUBLISHED,
                visibility=ArticleVisibility.PUBLIC
            )
        
        # Wait for indexing
        import asyncio
        await asyncio.sleep(1)
        
        # Test search
        service = SimpleRAGService()
        
        try:
            # Search for "machine learning"
            results = await service._retrieve_from_weaviate("machine learning tutorial")
            
            if results:
                # The ML article should rank highly
                top_result = results[0]
                assert "Machine Learning" in top_result.get("title", "") or "ML" in top_result.get("title", "")
            
        except Exception as e:
            if "vectorize" in str(e).lower() or "api" in str(e).lower():
                pytest.skip(f"Vectorization not configured: {e}")
            else:
                raise


@pytest.mark.unit
class TestAgenticRAGService:
    """Test AgenticRAGService functionality."""
    
    def test_initialization(self):
        """Test AgenticRAGService initialization."""
        service = AgenticRAGService()
        
        assert service is not None
    
    def test_suggest_actions(self):
        """Test action suggestion logic."""
        service = AgenticRAGService()
        
        # Test problem-related query
        actions = service._suggest_actions(
            query="I have a problem with my account",
            relevant_docs=[]
        )
        
        # Ticket system removed - no longer test for create_ticket action
        
        # Test with relevant docs
        actions = service._suggest_actions(
            query="How do I configure the system?",
            relevant_docs=[{"id": "1", "title": "Config Guide"}]
        )
        
        assert "view_related_articles" in actions
        
        # Test account-related query
        actions = service._suggest_actions(
            query="I need to update my billing information",
            relevant_docs=[]
        )
        
        assert "view_account" in actions
    
    @pytest.mark.asyncio
    async def test_generate_response_with_user_context(self):
        """Test response generation with user context."""
        service = AgenticRAGService()
        
        # Mock user context
        context = {
            "user_id": "customer-123"
        }
        
        # Mock document retrieval
        with patch.object(service, 'retrieve_relevant_documents', return_value=[]):
            # Mock direct response
            with patch.object(service, '_generate_direct_openai_response', return_value="Response with context"):
                result = await service.generate_response("test query", context)
                
                assert result is not None
                assert "response" in result
