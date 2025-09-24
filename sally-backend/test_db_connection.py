#!/usr/bin/env python3
"""
Test database connection and check articles
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.infrastructure.database_refactored import init_db
from app.domain.entities_refactored import KnowledgeBaseArticle, Category, Admin

async def test_db():
    """Test database connection and check data."""
    try:
        print("🔌 Testing database connection...")
        await init_db()
        print("✅ Database connection successful")

        # Check collections
        print("\n📊 Checking collections...")

        article_count = await KnowledgeBaseArticle.find_all().count()
        category_count = await Category.find_all().count()
        admin_count = await Admin.find_all().count()

        print(f"📝 Articles in DB: {article_count}")
        print(f"📂 Categories in DB: {category_count}")
        print(f"👤 Admins in DB: {admin_count}")

        # List recent articles
        if article_count > 0:
            print("\n📝 Recent articles:")
            articles = await KnowledgeBaseArticle.find_all().limit(5).to_list()
            for i, article in enumerate(articles, 1):
                print(f"  {i}. {article.title}")
                print(f"     ID: {str(article.id)[:8]}...")
                print(f"     Status: {article.status}")
                print(f"     Author: {article.author_id}")
                print(f"     Created: {article.created_at}")
                print()

        # List categories
        if category_count > 0:
            print("\n📂 Categories:")
            categories = await Category.find_all().to_list()
            for category in categories:
                print(f"  - {category.name} (ID: {str(category.id)[:8]}...)")

        # List admins
        if admin_count > 0:
            print("\n👤 Admins:")
            admins = await Admin.find_all().to_list()
            for admin in admins:
                print(f"  - {admin.full_name} ({admin.email}) - Active: {admin.is_active}")

        print("\n✅ Database test completed successfully")

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_db())
