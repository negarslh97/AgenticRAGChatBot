"""
بررسی مقالات موجود در MongoDB و status آن‌ها
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


async def check_articles():
    """بررسی تمام مقالات در MongoDB"""
    
    print("\n" + "=" * 80)
    print("[INFO] Checking MongoDB Articles")
    print("=" * 80)
    
    # اتصال
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client.get_database()
    
    # شمارش کل مقالات (بدون فیلتر)
    total = await db.knowledge_base_articles.count_documents({})
    print(f"\n[STATS] Total articles: {total}")
    
    if total == 0:
        print("\n[ERROR] No articles found in 'knowledge_base' collection!")
        print("\n[SOLUTION]:")
        print("   1. Add articles from frontend")
        print("   2. Or insert directly into MongoDB")
        client.close()
        return
    
    # گروه‌بندی بر اساس status
    print("\n[BREAKDOWN] Articles by status:")
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    async for result in db.knowledge_base_articles.aggregate(pipeline):
        status = result["_id"] or "no-status"
        count = result["count"]
        print(f"   - {status}: {count} articles")
    
    # نمایش چند مقاله نمونه
    print("\n[SAMPLE] Sample articles:")
    async for article in db.knowledge_base_articles.find().limit(5):
        article_id = str(article["_id"])
        title = article.get("title", "No title")
        status = article.get("status", "no-status")
        content_len = len(article.get("content_markdown", ""))
        visibility = article.get("visibility", "unknown")
        
        print(f"\n   ID: {article_id}")
        print(f"   Title: {title}")
        print(f"   Status: {status}")
        print(f"   Visibility: {visibility}")
        print(f"   Content: {content_len} chars")
        
        if status != "published":
            print(f"   [WARNING] This article does NOT have status='published'!")
    
    # بررسی مقالات بدون محتوا
    print("\n" + "=" * 80)
    print("[QUALITY] Content Quality Check")
    print("=" * 80)
    
    empty_content = await db.knowledge_base_articles.count_documents({
        "content_markdown": {"$in": ["", None]}
    })
    short_content = await db.knowledge_base_articles.count_documents({
        "$expr": {"$lt": [{"$strLenCP": {"$ifNull": ["$content_markdown", ""]}}, 50]}
    })
    
    print(f"\n[ERROR] Articles with no content: {empty_content}")
    print(f"[WARNING] Articles with short content (<50 chars): {short_content}")
    
    # راه‌حل‌ها
    published_count = await db.knowledge_base_articles.count_documents({"status": "published"})
    
    print("\n" + "=" * 80)
    print("[SUMMARY] Summary & Solutions")
    print("=" * 80)
    
    if published_count == 0:
        print("\n[ERROR] NO articles with status='published' found!")
        print("\n[SOLUTION]:")
        print("   Option 1: Update ALL articles to 'published'")
        print("   Option 2: Update specific articles to 'published'")
        print("\nDo you want to set ALL articles to 'published'? (y/n)")
        
        response = input().strip().lower()
        if response == 'y':
            result = await db.knowledge_base_articles.update_many(
                {},
                {"$set": {"status": "published"}}
            )
            print(f"\n[SUCCESS] {result.modified_count} articles updated to 'published'")
            print("\n[NEXT] You can now run re-indexing:")
            print("   python test_reindex_debug.py")
        else:
            print("\n[MANUAL] MongoDB commands to update manually:")
            print("\n// Update all articles:")
            print('db.knowledge_base_articles.updateMany({}, {$set: {status: "published"}})')
            print("\n// Update specific article:")
            print('db.knowledge_base_articles.updateOne({_id: ObjectId("...")}, {$set: {status: "published"}})')
    else:
        print(f"\n[SUCCESS] {published_count} articles with status='published' found")
        print("\n[NEXT] You can now run re-indexing:")
        print("   python test_reindex_debug.py")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(check_articles())

