#!/usr/bin/env python3
"""
Migration script to update existing KnowledgeBaseArticle documents to the new model structure.
This script converts old article format to the new embedded models and Link relationships.
"""

import asyncio
import sys
import os
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import settings


async def migrate_articles():
    """Migrate existing articles to the new model structure."""
    print("🔧 Starting article migration...")

    # Connect to MongoDB directly
    # Parse database name from URL (format: mongodb://host:port/database)
    database_url_parts = settings.database_url.rstrip('/').split('/')
    database_name = database_url_parts[-1] if len(database_url_parts) > 1 else "SallyChatBot"

    client = AsyncIOMotorClient(settings.database_url)
    db = client[database_name]
    collection = db["knowledge_base_articles"]

    # Get all existing articles
    articles = await collection.find({}).to_list(length=None)
    print(f"📚 Found {len(articles)} articles to migrate")

    migrated_count = 0
    error_count = 0

    for article_doc in articles:
        try:
            article_id = article_doc["_id"]
            title = article_doc.get("title", "Unknown")
            print(f"🔄 Migrating article: {title}")

            # Prepare update operations
            update_fields = {}

            # Convert old category_id to embedded ArticleCategory
            if "category_id" in article_doc and article_doc["category_id"]:
                try:
                    category_doc = await db.categories.find_one({"_id": ObjectId(article_doc["category_id"])})
                    if category_doc:
                        update_fields["category"] = {
                            "id": str(category_doc["_id"]),
                            "name": category_doc["name"],
                            "slug": category_doc.get("slug", category_doc["name"].lower().replace(" ", "-"))
                        }
                    else:
                        # If category_id is invalid but exists, try to find category by name
                        if isinstance(article_doc["category_id"], str):
                            category_doc = await db.categories.find_one({"name": article_doc["category_id"]})
                            if category_doc:
                                update_fields["category"] = {
                                    "id": str(category_doc["_id"]),
                                    "name": category_doc["name"],
                                    "slug": category_doc.get("slug", category_doc["name"].lower().replace(" ", "-"))
                                }
                                print(f"⚠️  Found category by name '{article_doc['category_id']}' for article '{title}'")
                except Exception as e:
                    print(f"⚠️  Invalid category_id '{article_doc['category_id']}' for article '{title}', skipping category conversion")
                    # Try to find a default category
                    default_category = await db.categories.find_one({})
                    if default_category:
                        update_fields["category"] = {
                            "id": str(default_category["_id"]),
                            "name": default_category["name"],
                            "slug": default_category.get("slug", default_category["name"].lower().replace(" ", "-"))
                        }
                        print(f"⚠️  Using default category for article '{title}'")

            # Convert old tags (list of strings) to embedded ArticleTag
            if "tags" in article_doc and article_doc["tags"]:
                embedded_tags = []
                for tag in article_doc["tags"]:
                    if isinstance(tag, str):
                        # Old format: just a string
                        embedded_tags.append({
                            "id": str(ObjectId()),
                            "name": tag,
                            "color": None
                        })
                    elif isinstance(tag, dict):
                        # Check if it's already in new format or corrupted
                        if "name" in tag and isinstance(tag["name"], str):
                            # Already in correct format
                            embedded_tags.append(tag)
                        elif "name" in tag and isinstance(tag["name"], dict):
                            # Corrupted format - extract the actual name
                            if isinstance(tag["name"], dict) and "name" in tag["name"]:
                                embedded_tags.append({
                                    "id": tag.get("id", str(ObjectId())),
                                    "name": tag["name"]["name"],
                                    "color": tag.get("color")
                                })
                            else:
                                # Skip invalid tags
                                print(f"⚠️  Skipping invalid tag format in article '{title}'")
                        else:
                            # Skip invalid tags
                            print(f"⚠️  Skipping invalid tag format in article '{title}'")
                update_fields["tags"] = embedded_tags
            else:
                update_fields["tags"] = []

            # Convert old author_id to Link[Admin] reference
            if "author_id" in article_doc and article_doc["author_id"]:
                try:
                    author_id = ObjectId(article_doc["author_id"])
                    author_doc = await db.admins.find_one({"_id": author_id})
                    if author_doc:
                        # For Beanie Link, we just store the ObjectId
                        update_fields["author"] = author_id
                except Exception as e:
                    print(f"⚠️  Invalid author_id '{article_doc['author_id']}' for article '{title}', skipping author conversion")

            # Convert old published_by to Link[Admin] reference
            if "published_by" in article_doc and article_doc["published_by"]:
                try:
                    publisher_id = ObjectId(article_doc["published_by"])
                    publisher_doc = await db.admins.find_one({"_id": publisher_id})
                    if publisher_doc:
                        # For Beanie Link, we just store the ObjectId
                        update_fields["publisher"] = publisher_id
                except Exception as e:
                    print(f"⚠️  Invalid published_by '{article_doc['published_by']}' for article '{title}', skipping publisher conversion")

            # Ensure author exists (required field)
            if "author" not in update_fields:
                # Find first available admin as default author
                default_admin = await db.admins.find_one({})
                if default_admin:
                    update_fields["author"] = default_admin["_id"]
                    print(f"⚠️  No valid author found for article '{title}', using default admin")
                else:
                    print(f"❌ No admin users found in database! Cannot set author for article '{title}'")
                    error_count += 1
                    continue

            # Split content into markdown and HTML
            if "content" in article_doc and article_doc["content"]:
                update_fields["content_markdown"] = article_doc["content"]
                update_fields["content_html"] = article_doc["content"]  # Simple conversion for now
            else:
                # Set default empty content if no content exists
                update_fields["content_markdown"] = ""
                update_fields["content_html"] = ""

            # Convert existing publisher from DBRef to ObjectId if needed
            if "publisher" in article_doc and isinstance(article_doc["publisher"], dict) and "$id" in article_doc["publisher"]:
                update_fields["publisher"] = article_doc["publisher"]["$id"]

            # Remove old fields
            unset_fields = {}
            for old_field in ["category_id", "author_id", "published_by", "content"]:
                if old_field in article_doc:
                    unset_fields[old_field] = ""

            # Perform the update
            update_operation = {"$set": update_fields}
            if unset_fields:
                update_operation["$unset"] = unset_fields

            await collection.update_one({"_id": article_id}, update_operation)

            migrated_count += 1
            print(f"✅ Migrated: {title}")

        except Exception as e:
            error_count += 1
            print(f"❌ Error migrating article {article_doc.get('title', 'Unknown')}: {str(e)}")
            continue

    # Close the client
    client.close()

    print(f"\n📊 Migration completed:")
    print(f"   ✅ Successfully migrated: {migrated_count}")
    print(f"   ❌ Errors: {error_count}")
    print(f"   📝 Total processed: {len(articles)}")


async def main():
    """Main migration function."""
    try:
        await migrate_articles()
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())