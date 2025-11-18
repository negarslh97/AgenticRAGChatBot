"""
Script to drop the old username_1 index from the admins collection.

This index is a leftover from an earlier schema version and causes duplicate key errors
when creating admin users since the Admin model no longer has a username field.

Usage:
    cd sally-backend
    python scripts/drop_username_index.py
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


async def drop_username_index():
    """Drop the username_1 index from the admins collection."""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client.get_default_database()
    admins_collection = db["admins"]
    
    try:
        # Get all indexes
        indexes = await admins_collection.list_indexes().to_list(length=None)
        
        print("Current indexes on 'admins' collection:")
        for index in indexes:
            print(f"  - {index.get('name', 'unknown')}: {index.get('key', {})}")
        
        # Check if username_1 index exists and drop it
        username_index_exists = False
        for index in indexes:
            index_name = index.get("name", "")
            if index_name == "username_1":
                username_index_exists = True
                await admins_collection.drop_index("username_1")
                print(f"\n✅ Successfully dropped index: username_1")
                break
        
        if not username_index_exists:
            print("\nℹ️  Index 'username_1' not found. It may have already been removed.")
        
        # Show updated indexes
        print("\nUpdated indexes on 'admins' collection:")
        updated_indexes = await admins_collection.list_indexes().to_list(length=None)
        for index in updated_indexes:
            print(f"  - {index.get('name', 'unknown')}: {index.get('key', {})}")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    print("Dropping username_1 index from admins collection...\n")
    asyncio.run(drop_username_index())
    print("\n✅ Done!")

