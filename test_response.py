#!/usr/bin/env python3
"""
Test ArticleResponse serialization.
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sally-backend'))

from app.core.config import settings
from app.infrastructure.database_refactored import init_db
from app.domain.entities_refactored import KnowledgeBaseArticle
from app.api.routes.admin_knowledge_base import ArticleResponse

async def test_response():
    """Test ArticleResponse creation."""
    print("🔍 Testing ArticleResponse serialization...")

    # Initialize database
    await init_db()

    try:
        # Get articles
        articles = await KnowledgeBaseArticle.find({}).sort(-KnowledgeBaseArticle.updated_at).to_list()
        print(f"✅ Found {len(articles)} articles")

        # Try to create response for first article
        article = articles[0]
        print(f"Testing response for: {article.title}")

        # Create response manually like the API does
        author_id = ""
        if article.author:
            # Debug: check what attributes Link has
            print(f"Author object: {article.author}")
            print(f"Author type: {type(article.author)}")
            print(f"Author dir: {[attr for attr in dir(article.author) if not attr.startswith('_')]}")
            # Try different ways to get the ID
            if hasattr(article.author, 'ref'):
                author_id = str(article.author.ref)
            elif hasattr(article.author, 'id'):
                author_id = str(article.author.id)
            elif hasattr(article.author, 'ref_id'):
                author_id = str(article.author.ref_id)
            else:
                author_id = str(article.author)

        response = ArticleResponse(
            id=str(article.id),
            title=article.title,
            content_markdown=article.content_markdown,
            content_html=article.content_html,
            summary=article.summary,
            status=article.status,
            visibility=article.visibility,
            author_id=author_id,
            category=article.category,
            tags=article.tags,
            version=article.version,
            created_at=article.created_at,
            updated_at=article.updated_at,
            published_at=article.published_at
        )

        print("✅ ArticleResponse created successfully")
        print(f"Response data: {response.model_dump()}")

        # Try to serialize to JSON
        try:
            import json
            json_str = response.model_dump_json()
            print("✅ JSON serialization successful")
            print(f"JSON: {json_str[:200]}...")
        except Exception as e:
            print(f"❌ JSON serialization failed: {e}")

    except Exception as e:
        print(f"❌ Error creating ArticleResponse: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_response())
