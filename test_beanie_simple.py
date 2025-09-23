#!/usr/bin/env python3
"""
Test Beanie model validation with simpler approach.
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sally-backend'))

from app.core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient

async def test_direct_query():
    """Test direct MongoDB query."""
    print("🔍 Testing direct MongoDB query...")

    client = AsyncIOMotorClient(settings.database_url)
    db = client.get_default_database()

    try:
        # Direct query
        articles = await db.knowledge_base_articles.find({}).to_list(None)
        print(f"✅ Found {len(articles)} articles in database")

        # Try to import and validate one article
        from app.domain.entities_refactored import KnowledgeBaseArticle, Admin
        from beanie import init_beanie

        # Initialize Beanie
        await init_beanie(database=db, document_models=[KnowledgeBaseArticle, Admin])

        # Test validation on first article
        if articles:
            article_data = articles[0]
            print(f"Testing validation for: {article_data.get('title')}")

            try:
                # Try to create model instance
                article = KnowledgeBaseArticle(**article_data)
                print("✅ Article validation successful")
            except Exception as e:
                print(f"❌ Article validation failed: {e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    client.close()

if __name__ == "__main__":
    asyncio.run(test_direct_query())
