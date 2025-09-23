#!/usr/bin/env python3
"""
Test Beanie model validation directly.
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sally-backend'))

from app.core.config import settings
from app.domain.entities_refactored import KnowledgeBaseArticle
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

async def test_beanie():
    """Test loading articles with Beanie."""
    print("🔍 Testing Beanie model validation...")

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.database_url)
    database_name = settings.database_url.rstrip('/').split('/')[-1] if '/' in settings.database_url else "SallyChatBot"
    db = client[database_name]

    # Initialize Beanie
    await init_beanie(database=db, document_models=[KnowledgeBaseArticle])

    try:
        # Try to get all articles
        articles = await KnowledgeBaseArticle.find_all().to_list()
        print(f"✅ Successfully loaded {len(articles)} articles with Beanie")

        for article in articles[:1]:  # Just check first article
            print(f"Title: {article.title}")
            print(f"Author: {article.author}")
            print(f"Status: {article.status}")
            print(f"Tags: {len(article.tags)} tags")

    except Exception as e:
        print(f"❌ Error loading articles with Beanie: {e}")
        import traceback
        traceback.print_exc()

    client.close()

if __name__ == "__main__":
    asyncio.run(test_beanie())
