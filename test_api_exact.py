#!/usr/bin/env python3
"""
Test the exact same query used in the API.
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sally-backend'))

from app.core.config import settings
from app.infrastructure.database_refactored import init_db
from app.domain.entities_refactored import KnowledgeBaseArticle

async def test_api_query():
    """Test the exact query used in the API."""
    print("🔍 Testing exact API query...")

    # Initialize database (same as in main.py)
    await init_db()
    print("✅ Database initialized")

    try:
        # This is the exact query from the API
        query = {}
        articles = await KnowledgeBaseArticle.find(query).sort(-KnowledgeBaseArticle.updated_at).to_list()
        print(f"✅ Successfully retrieved {len(articles)} articles")

        for article in articles[:1]:  # Just check first article
            print(f"Title: {article.title}")
            print(f"Author: {article.author}")
            print(f"Status: {article.status}")

    except Exception as e:
        print(f"❌ Error in API query: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api_query())
