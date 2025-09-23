#!/usr/bin/env python3
"""
Create default categories for the knowledge base.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.infrastructure.database_refactored import init_db
from app.domain.entities_refactored import Category


async def create_default_categories():
    """Create default categories if they don't exist."""

    await init_db()

    # Default categories
    default_categories = [
        {"name": "عمومی", "slug": "general", "description": "مقاله‌های عمومی", "is_public": True},
        {"name": "فنی", "slug": "technical", "description": "مقاله‌های فنی", "is_public": True},
        {"name": "آموزشی", "slug": "educational", "description": "مقاله‌های آموزشی", "is_public": True},
        {"name": "راهنما", "slug": "guide", "description": "راهنماها و دستورالعمل‌ها", "is_public": True},
        {"name": "داخلی", "slug": "internal", "description": "مقاله‌های داخلی", "is_public": False},
    ]

    created_count = 0

    for cat_data in default_categories:
        # Check if category already exists
        existing = await Category.find_one(Category.slug == cat_data["slug"])
        if existing:
            print(f"Category '{cat_data['name']}' already exists")
            continue

        # Create new category
        category = Category(**cat_data)
        await category.insert()

        print(f"Created category: {category.name} (ID: {category.id})")
        created_count += 1

    print(f"\n✅ Created {created_count} new categories")


if __name__ == "__main__":
    asyncio.run(create_default_categories())
