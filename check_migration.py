#!/usr/bin/env python3
"""
Check the migration status of articles in the database.
"""

import asyncio
import sys
import os
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sally-backend'))

from app.core.config import settings

async def check_articles():
    """Check the current state of articles in the database."""
    print("🔍 Checking article migration status...")

    # Connect to MongoDB directly
    database_url_parts = settings.database_url.rstrip('/').split('/')
    database_name = database_url_parts[-1] if len(database_url_parts) > 1 else "SallyChatBot"

    client = AsyncIOMotorClient(settings.database_url)
    db = client[database_name]
    collection = db["knowledge_base_articles"]

    # Get all articles
    articles = await collection.find({}).to_list(length=None)
    print(f"📚 Found {len(articles)} articles")

    for article in articles:
        print(f"\n--- Article: {article.get('title', 'No title')} ---")
        print(f"ID: {article['_id']}")

        # Check required fields
        required_fields = ['title', 'content_markdown', 'content_html', 'author', 'tags', 'status']
        for field in required_fields:
            if field in article:
                if field == 'tags':
                    print(f"✅ {field}: {len(article[field])} tags")
                elif field == 'author':
                    print(f"✅ {field}: {article[field]}")
                elif field == 'status':
                    print(f"✅ {field}: {article[field]}")
                else:
                    print(f"✅ {field}: present ({len(article[field])} chars)" if isinstance(article[field], str) else f"✅ {field}: {article[field]}")
            else:
                print(f"❌ {field}: MISSING")

        # Check optional but important fields
        optional_fields = ['category', 'visibility', 'publisher', 'published_at']
        for field in optional_fields:
            if field in article:
                print(f"ℹ️  {field}: {article[field]}")
            else:
                print(f"⚠️  {field}: not set")

        # Check old fields that should be removed
        old_fields = ['category_id', 'author_id', 'published_by', 'content']
        for field in old_fields:
            if field in article:
                print(f"⚠️  Old field still present: {field} = {article[field]}")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_articles())
