#!/usr/bin/env python3
"""
Fix articles with validation issues.
"""

import asyncio
import sys
import os
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sally-backend'))

from app.core.config import settings

async def fix_articles():
    """Fix validation issues in articles."""
    print("🔧 Fixing article validation issues...")

    # Connect to MongoDB directly
    database_url_parts = settings.database_url.rstrip('/').split('/')
    database_name = database_url_parts[-1] if len(database_url_parts) > 1 else "SallyChatBot"

    client = AsyncIOMotorClient(settings.database_url)
    db = client[database_name]
    collection = db["knowledge_base_articles"]

    # Get all articles
    articles = await collection.find({}).to_list(length=None)
    print(f"📚 Found {len(articles)} articles")

    fixed_count = 0

    for article in articles:
        article_id = article["_id"]
        title = article.get("title", "No title")
        update_fields = {}

        # Fix publisher if it's DBRef
        if "publisher" in article and isinstance(article["publisher"], dict):
            if "$id" in article["publisher"]:
                update_fields["publisher"] = article["publisher"]["$id"]
                print(f"🔄 Fixing publisher for '{title}'")

        # Fix visibility issues
        status = article.get("status", "draft")
        visibility = article.get("visibility")

        if status == "published" and visibility is None:
            update_fields["visibility"] = "public"
            print(f"🔄 Setting visibility for published article '{title}'")

        # Fix tags if they have wrong format
        if "tags" in article and article["tags"]:
            fixed_tags = []
            for tag in article["tags"]:
                if isinstance(tag, dict) and "id" in tag and "name" in tag:
                    fixed_tags.append(tag)
                elif isinstance(tag, str):
                    fixed_tags.append({
                        "id": str(ObjectId()),
                        "name": tag,
                        "color": None
                    })
            if fixed_tags != article["tags"]:
                update_fields["tags"] = fixed_tags
                print(f"🔄 Fixing tags for '{title}'")

        # Apply updates
        if update_fields:
            await collection.update_one({"_id": article_id}, {"$set": update_fields})
            fixed_count += 1
            print(f"✅ Fixed '{title}'")

    client.close()
    print(f"📊 Fixed {fixed_count} articles")

if __name__ == "__main__":
    asyncio.run(fix_articles())
