# scripts/sync_data_to_weaviate.py
import weaviate
from pymongo import MongoClient
import os
from datetime import datetime
import asyncio

async def sync_mongodb_to_weaviate():
    print("🔄 Starting data synchronization...")
    
    # اضافه کردن API Key به header
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        return
    
    # اتصال به Weaviate با API Key
    try:
        weaviate_client = weaviate.connect_to_local(
            host="localhost",
            port=8080,
            skip_init_checks=True,
            additional_headers={
                "X-OpenAI-Api-Key": api_key  # اضافه کردن API Key
            }
        )
        print("✅ Connected to Weaviate with API Key")
    except Exception as e:
        print(f"❌ Weaviate connection error: {e}")
        return
    
    # بازیابی مقالات از MongoDB
    try:
        published_articles = articles_collection.find({"status": "PUBLISHED"})
        articles_count = articles_collection.count_documents({"status": "PUBLISHED"})
        print(f"📊 Found {articles_count} published articles in MongoDB")
    except Exception as e:
        print(f"❌ Error fetching articles from MongoDB: {e}")
        return
    
    success_count = 0
    error_count = 0
    
    # همگام‌سازی هر مقاله
    for article in published_articles:
        try:
            # آماده‌سازی داده برای Weaviate
            article_data = {
                "title": article.get("title", ""),
                "content": article.get("content", ""),
                "summary": article.get("summary", ""),
                "status": article.get("status", ""),
                "visibility": article.get("visibility", ""),
                "category": article.get("category", ""),
                "tags": article.get("tags", []),
                "mongoId": str(article.get("_id", "")),
            }
            
            # افزودن به Weaviate
            weaviate_client.collections.get("KnowledgeBaseArticle").data.insert(
                properties=article_data
            )
            
            success_count += 1
            if success_count % 10 == 0:
                print(f"✅ Synced {success_count} articles...")
                
        except Exception as e:
            error_count += 1
            print(f"⚠️ Error syncing article {article.get('_id')}: {e}")
    
    # نتیجه نهایی
    print(f"\n🎉 Synchronization completed!")
    print(f"✅ Successful: {success_count}")
    print(f"⚠️ Errors: {error_count}")
    print(f"📊 Total: {articles_count}")
    
    # بستن اتصالات
    mongo_client.close()
    weaviate_client.close()

if __name__ == "__main__":
    asyncio.run(sync_mongodb_to_weaviate())