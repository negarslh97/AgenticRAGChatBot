#!/usr/bin/env python3
"""
Migration script to convert KnowledgeBaseArticle documents from old author format to new author_id format.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from app.domain.entities_refactored import KnowledgeBaseArticle, Admin
from app.core.config import settings


async def migrate_articles():
    """Migrate existing articles to use author_id instead of author Link."""

    # Connect to database
    client = AsyncIOMotorClient(settings.database_url)
    database = client.get_default_database()

    print("🔄 Starting migration of KnowledgeBaseArticle documents...")

    # Use raw MongoDB collection to avoid Beanie validation
    collection = database["knowledge_base_articles"]

    # Find all articles
    articles = await collection.find({}).to_list(length=None)

    migrated_count = 0

    for article_doc in articles:
        needs_migration = False

        # Check if article has author_id
        if 'author_id' not in article_doc or article_doc.get('author_id') is None:
            # Set a default admin ID for articles without author_id
            article_doc['author_id'] = "default_admin_id"
            needs_migration = True
            print(f"📝 Migrating article '{article_doc.get('title', 'Unknown')}': setting author_id to default_admin_id")

        # Check publisher_id
        if 'publisher_id' not in article_doc:
            article_doc['publisher_id'] = None
            needs_migration = True

        # Save the article if it was migrated
        if needs_migration:
            await collection.update_one(
                {"_id": article_doc["_id"]},
                {"$set": {
                    "author_id": article_doc["author_id"],
                    "publisher_id": article_doc["publisher_id"]
                }}
            )
            migrated_count += 1

    print(f"✅ Migration completed! {migrated_count} articles migrated.")

    # Close connection
    client.close()


if __name__ == "__main__":
    asyncio.run(migrate_articles())
