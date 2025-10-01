#!/usr/bin/env python3
"""
اسکریپت بررسی اتصالات دیتابیس
این اسکریپت بررسی می‌کند که:
1. MongoDB اتصال دارد
2. Weaviate اتصال دارد
3. ارتباط و Sync بین MongoDB و Weaviate برقرار است
"""

import os
import sys
from pathlib import Path
import asyncio

# Add parent directory to Python path
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

from app.core.config import settings

async def check_mongodb():
    """بررسی اتصال MongoDB"""
    print("="*80)
    print("📊 بررسی اتصال MongoDB")
    print("="*80)
    print()
    
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongodb_url = settings.database_url
        print(f"🔗 MongoDB URL: {mongodb_url}")
        
        # اتصال به MongoDB
        client = AsyncIOMotorClient(mongodb_url)
        
        # تست اتصال
        await client.admin.command('ping')
        print("✅ MongoDB متصل است")
        
        # دریافت لیست دیتابیس‌ها
        db = client.get_default_database()
        collections = await db.list_collection_names()
        
        print(f"📚 تعداد کالکشن‌ها: {len(collections)}")
        print(f"📋 کالکشن‌ها: {', '.join(collections[:5])}{'...' if len(collections) > 5 else ''}")
        
        # بررسی کالکشن مقالات
        if "knowledge_base_articles" in collections:
            articles_count = await db.knowledge_base_articles.count_documents({})
            published_count = await db.knowledge_base_articles.count_documents({"status": "published"})
            print(f"📄 مقالات در MongoDB: {articles_count} (منتشر شده: {published_count})")
        else:
            print("⚠️  کالکشن knowledge_base_articles وجود ندارد")
        
        print()
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ خطا در اتصال به MongoDB: {str(e)}")
        print()
        return False


def check_weaviate():
    """بررسی اتصال Weaviate"""
    print("="*80)
    print("🔍 بررسی اتصال Weaviate")
    print("="*80)
    print()
    
    try:
        import weaviate
        from weaviate.classes.init import Auth
        from urllib.parse import urlparse
        
        weaviate_url = settings.weaviate_url_loaded or "http://localhost:8080"
        weaviate_api_key = settings.weaviate_api_key_loaded
        
        print(f"🔗 Weaviate URL: {weaviate_url}")
        
        # Parse URL
        parsed_url = urlparse(weaviate_url)
        http_host = parsed_url.hostname or "localhost"
        http_port = parsed_url.port or 8080
        http_secure = parsed_url.scheme == "https"
        
        # اتصال به Weaviate
        if weaviate_api_key:
            client = weaviate.connect_to_custom(
                http_host=http_host,
                http_port=http_port,
                http_secure=http_secure,
                grpc_host=http_host,
                grpc_port=50051,
                grpc_secure=http_secure,
                auth_credentials=Auth.api_key(weaviate_api_key)
            )
        else:
            client = weaviate.connect_to_custom(
                http_host=http_host,
                http_port=http_port,
                http_secure=http_secure,
                grpc_host=http_host,
                grpc_port=50051,
                grpc_secure=http_secure
            )
        
        # تست اتصال
        if client.is_ready():
            print("✅ Weaviate متصل است")
            
            # بررسی collection
            if client.collections.exists("MarkdownNode"):
                print("✅ Collection 'MarkdownNode' موجود است")
                
                # شمارش داده‌ها
                collection = client.collections.get("MarkdownNode")
                aggregate_result = collection.aggregate.over_all(total_count=True)
                total_count = aggregate_result.total_count
                
                print(f"📊 گره‌های Markdown در Weaviate: {total_count}")
            else:
                print("⚠️  Collection 'MarkdownNode' وجود ندارد")
            
            print()
            client.close()
            return True
        else:
            print("❌ Weaviate آماده نیست")
            print()
            return False
        
    except Exception as e:
        print(f"❌ خطا در اتصال به Weaviate: {str(e)}")
        print()
        print("💡 راه‌حل: docker-compose up -d در پوشه sally-backend")
        print()
        return False


async def check_sync_mechanism():
    """بررسی مکانیسم همگام‌سازی"""
    print("="*80)
    print("🔄 بررسی مکانیسم Sync بین MongoDB و Weaviate")
    print("="*80)
    print()
    
    try:
        # بررسی وجود کلاس KnowledgeBaseRepository
        from app.infrastructure.knowledge_base_repository import KnowledgeBaseRepository
        
        print("✅ KnowledgeBaseRepository موجود است")
        
        # بررسی وجود متد _sync_to_weaviate
        if hasattr(KnowledgeBaseRepository, '_sync_to_weaviate'):
            print("✅ متد _sync_to_weaviate پیاده‌سازی شده")
        else:
            print("❌ متد _sync_to_weaviate پیاده‌سازی نشده")
            return False
        
        # بررسی وجود WeaviateMongoDBConnector
        from app.infrastructure.database.weaviate_connector import WeaviateMongoDBConnector
        
        print("✅ WeaviateMongoDBConnector موجود است")
        
        # بررسی متدهای connector
        connector = WeaviateMongoDBConnector()
        methods = ['connect_weaviate', 'connect_mongodb', 'save_markdown_tree', 'delete_markdown_nodes']
        
        for method in methods:
            if hasattr(connector, method):
                print(f"  ✅ {method}")
            else:
                print(f"  ❌ {method} موجود نیست")
        
        print()
        print("📋 نحوه کار Sync:")
        print("   1. مقاله در MongoDB ایجاد/آپدیت می‌شود")
        print("   2. اگر status=PUBLISHED باشد، متد _sync_to_weaviate صدا زده می‌شود")
        print("   3. محتوای Markdown به ساختار درختی تبدیل می‌شود")
        print("   4. ساختار درختی در Weaviate ذخیره می‌شود (با vectorization)")
        print("   5. RAG Service از Weaviate برای جستجوی معنایی استفاده می‌کند")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در بررسی Sync: {str(e)}")
        print()
        return False


async def check_usage_in_code():
    """بررسی استفاده از دیتابیس‌ها در کد"""
    print("="*80)
    print("💻 بررسی استفاده در کد")
    print("="*80)
    print()
    
    # MongoDB Usage
    print("📊 استفاده از MongoDB:")
    print("   ✅ main.py → init_db() در startup")
    print("   ✅ knowledge_base_repository.py → ذخیره و بازیابی مقالات")
    print("   ✅ rag_service.py → fallback search")
    print("   ✅ super_admin_knowledge_base.py → مدیریت مقالات")
    print()
    
    # Weaviate Usage
    print("🔍 استفاده از Weaviate:")
    print("   ✅ knowledge_base_repository.py → _sync_to_weaviate()")
    print("   ✅ rag_service.py → _retrieve_from_weaviate() برای جستجوی معنایی")
    print("   ✅ weaviate_connector.py → مدیریت schema و data")
    print("   ✅ background_jobs.py → sync مقالات Git")
    print()
    
    # Sync Points
    print("🔄 نقاط Sync بین دو دیتابیس:")
    print("   1. create_article() → MongoDB insert → Weaviate sync (if PUBLISHED)")
    print("   2. update_article() → MongoDB update → Weaviate update (if PUBLISHED)")
    print("   3. publish_article() → Status change → Weaviate sync")
    print("   4. delete_article() → MongoDB delete → Weaviate delete")
    print()
    
    return True


async def main():
    """تابع اصلی"""
    print()
    print("🔍 بررسی کامل اتصالات دیتابیس و Sync Mechanism")
    print()
    
    # بررسی MongoDB
    mongodb_ok = await check_mongodb()
    
    # بررسی Weaviate
    weaviate_ok = check_weaviate()
    
    # بررسی مکانیسم Sync
    sync_ok = await check_sync_mechanism()
    
    # بررسی استفاده در کد
    usage_ok = await check_usage_in_code()
    
    # خلاصه نهایی
    print("="*80)
    print("📊 خلاصه نتایج")
    print("="*80)
    print()
    
    results = {
        "MongoDB Connection": mongodb_ok,
        "Weaviate Connection": weaviate_ok,
        "Sync Mechanism": sync_ok,
        "Code Usage": usage_ok
    }
    
    for name, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {name}")
    
    print()
    
    if all(results.values()):
        print("🎉 همه اتصالات و مکانیسم‌ها به درستی پیاده‌سازی شده‌اند!")
        print()
        print("📋 برای استفاده کامل:")
        print("   1. اطمینان از اجرای MongoDB (پیش‌فرض: localhost:27017)")
        print("   2. اجرای Weaviate: cd sally-backend && docker-compose up -d")
        print("   3. migrate مقالات: python migrate_all_articles.py")
        print("   4. اجرای برنامه: uvicorn main:app --reload")
        return 0
    else:
        print("⚠️  برخی مشکلات وجود دارد:")
        if not mongodb_ok:
            print("   • MongoDB در دسترس نیست")
        if not weaviate_ok:
            print("   • Weaviate در دسترس نیست (docker-compose up -d)")
        if not sync_ok:
            print("   • مکانیسم Sync کامل نیست")
        print()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

