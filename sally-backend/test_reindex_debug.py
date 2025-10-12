"""
🔍 Debug Script for Re-indexing Issues
========================================

این اسکریپت تمام مراحل re-indexing را به صورت دقیق تست می‌کند
و مشکلات احتمالی را شناسایی می‌کند.

نحوه اجرا:
    cd sally-backend
    python test_reindex_debug.py
"""

import asyncio
import sys
from pathlib import Path

# اضافه کردن root directory به path
sys.path.insert(0, str(Path(__file__).parent))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.infrastructure.connection_manager import weaviate_client
from app.infrastructure.markdown_parser import markdown_parser
from openai import OpenAI
import logging

# تنظیم logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_mongodb_connection():
    """تست 1: اتصال به MongoDB"""
    logger.info("=" * 80)
    logger.info("TEST 1: MongoDB Connection")
    logger.info("=" * 80)
    
    try:
        logger.info(f"🔗 Connecting to: {settings.database_url}")
        client = AsyncIOMotorClient(settings.database_url)
        db = client.get_database()
        
        # شمارش مقالات
        total = await db.knowledge_base_articles.count_documents({})
        published = await db.knowledge_base_articles.count_documents({"status": "published"})
        
        logger.info(f"✅ Connected to MongoDB")
        logger.info(f"📊 Total articles: {total}")
        logger.info(f"📊 Published articles: {published}")
        
        if published == 0:
            logger.error("❌ هیچ مقاله published وجود ندارد!")
            logger.error("💡 راه‌حل: در MongoDB، مقالاتی با status='published' اضافه کنید")
            return False, client
        
        # نمایش نمونه مقالات
        logger.info("\n📝 Sample articles:")
        async for article in db.knowledge_base_articles.find({"status": "published"}).limit(3):
            title = article.get("title", "NO TITLE")
            content_len = len(article.get("content_markdown", ""))
            logger.info(f"  • {title} (content: {content_len} chars)")
            
            if content_len == 0:
                logger.warning(f"    ⚠️ این مقاله محتوا ندارد!")
        
        return True, client
        
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        return False, None


async def test_weaviate_connection():
    """تست 2: اتصال به Weaviate"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Weaviate Connection")
    logger.info("=" * 80)
    
    try:
        weaviate_url = settings.weaviate_url_loaded
        logger.info(f"🔗 Connecting to: {weaviate_url}")
        
        if not weaviate_url:
            logger.error("❌ WEAVIATE_URL is not set!")
            logger.error("💡 راه‌حل: در .env فایل، WEAVIATE_URL را تنظیم کنید")
            logger.error("   مثال: WEAVIATE_URL=http://localhost:8080")
            return False
        
        with weaviate_client() as client:
            # بررسی health
            if client.is_ready():
                logger.info("✅ Weaviate is ready")
            else:
                logger.error("❌ Weaviate is not ready")
                return False
            
            # بررسی collection
            try:
                collection = client.collections.get("MarkdownNode")
                result = collection.aggregate.over_all(total_count=True)
                count = result.total_count if hasattr(result, 'total_count') else 0
                logger.info(f"📊 MarkdownNode collection: {count} objects")
                
                if count == 0:
                    logger.warning("⚠️ Collection خالی است")
                
            except Exception as e:
                logger.warning(f"⚠️ Collection 'MarkdownNode' not found: {e}")
                logger.info("💡 این طبیعی است اگر اولین بار است که re-index می‌کنید")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Weaviate connection failed: {e}")
        logger.error("💡 راه‌حل: مطمئن شوید Weaviate در حال اجرا است")
        logger.error("   docker-compose up -d weaviate")
        return False


def test_openai_embedder():
    """تست 3: OpenAI Embedder"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: OpenAI Embedder Configuration")
    logger.info("=" * 80)
    
    try:
        api_key = settings.embedder_api_key_loaded
        base_url = settings.embedder_openai_base_url_loaded
        model = settings.embedder_model_loaded
        
        logger.info(f"🔑 API Key: {'✅ SET' if api_key else '❌ NOT SET'}")
        logger.info(f"🔗 Base URL: {base_url or 'default (https://api.openai.com/v1)'}")
        logger.info(f"🤖 Model: {model}")
        
        if not api_key:
            logger.error("❌ Embedder_API_KEY is not set!")
            logger.error("💡 راه‌حل: در .env فایل، Embedder_API_KEY را تنظیم کنید")
            logger.error("   مثال: Embedder_API_KEY=sk-...")
            return False
        
        # تست embedding
        logger.info("\n🧪 Testing embedding generation...")
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        response = client.embeddings.create(
            model=model,
            input=["این یک تست است"]
        )
        
        embedding = response.data[0].embedding
        logger.info(f"✅ Embedding generated successfully")
        logger.info(f"📊 Embedding dimension: {len(embedding)}")
        
        return True, client
        
    except Exception as e:
        logger.error(f"❌ OpenAI Embedder failed: {e}")
        logger.error("💡 راه‌حل: بررسی کنید API Key معتبر است")
        return False, None


async def test_markdown_parser():
    """تست 4: Markdown Parser"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Markdown Parser")
    logger.info("=" * 80)
    
    try:
        test_content = """# عنوان اصلی

این یک متن تست است.

## بخش اول

محتوای بخش اول.

### زیربخش

محتوای زیربخش.

## بخش دوم

محتوای بخش دوم.
"""
        
        logger.info("🧪 Testing markdown parsing...")
        tree = markdown_parser.parse_to_tree(test_content, "test-article-id", article_title="Test Article")
        nodes = tree.get_all_nodes()
        
        logger.info(f"✅ Parser working correctly")
        logger.info(f"📊 Generated {len(nodes)} chunks")
        
        for i, node in enumerate(nodes[:3], 1):
            logger.info(f"\n  Chunk {i}:")
            logger.info(f"    Title: {node.title}")
            logger.info(f"    Content length: {len(node.content)} chars")
            logger.info(f"    Level: {node.level}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Markdown parser failed: {e}")
        return False


async def test_full_reindex_single_article(mongodb_client, openai_client):
    """تست 5: Re-index یک مقاله نمونه"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: Full Re-index Test (Single Article)")
    logger.info("=" * 80)
    
    try:
        db = mongodb_client.get_database()
        
        # یافتن اولین مقاله
        article = await db.knowledge_base_articles.find_one({"status": "published"})
        
        if not article:
            logger.error("❌ No published articles found")
            return False
        
        article_id = str(article["_id"])
        title = article.get("title", "بدون عنوان")
        content = article.get("content_markdown", "")
        
        logger.info(f"📝 Testing with article: {title}")
        logger.info(f"📊 Content length: {len(content)} chars")
        
        if len(content) < 10:
            logger.error("❌ Content is too short or empty!")
            logger.error("💡 راه‌حل: مطمئن شوید مقالات content_markdown دارند")
            return False
        
        # پارس کردن
        logger.info("\n🔄 Step 1: Parsing markdown...")
        tree = markdown_parser.parse_to_tree(content, article_id, article_title=title)
        nodes = tree.get_all_nodes()
        logger.info(f"✅ Generated {len(nodes)} chunks")
        
        if len(nodes) == 0:
            logger.error("❌ No chunks generated!")
            return False
        
        # تولید embeddings
        logger.info("\n🔄 Step 2: Generating embeddings...")
        texts_to_vectorize = [f"{node.title}\n\n{node.content}" for node in nodes]
        
        response = openai_client.embeddings.create(
            model=settings.embedder_model_loaded,
            input=texts_to_vectorize
        )
        vectors = [item.embedding for item in response.data]
        logger.info(f"✅ Generated {len(vectors)} embeddings")
        
        # ذخیره در Weaviate
        logger.info("\n🔄 Step 3: Saving to Weaviate...")
        with weaviate_client() as client:
            # اطمینان از وجود collection
            try:
                collection = client.collections.get("MarkdownNode")
            except:
                logger.info("📝 Creating MarkdownNode collection...")
                from weaviate.classes.config import Configure, Property, DataType
                
                vectorizer_config = Configure.Vectorizer.none()
                client.collections.create(
                    name="MarkdownNode",
                    vectorizer_config=vectorizer_config,
                    properties=[
                        Property(name="node_id", data_type=DataType.TEXT),
                        Property(name="article_id", data_type=DataType.TEXT),
                        Property(name="title", data_type=DataType.TEXT),
                        Property(name="content", data_type=DataType.TEXT),
                        Property(name="full_content", data_type=DataType.TEXT),
                        Property(name="level", data_type=DataType.INT),
                        Property(name="path", data_type=DataType.TEXT),
                        Property(name="order", data_type=DataType.INT),
                        Property(name="parent_id", data_type=DataType.TEXT),
                        Property(name="visibility", data_type=DataType.TEXT),
                        Property(name="category", data_type=DataType.TEXT),
                    ]
                )
                collection = client.collections.get("MarkdownNode")
                logger.info("✅ Collection created")
            
            # حذف chunks قبلی این مقاله
            try:
                deleted = collection.data.delete_many(
                    where={
                        "path": ["article_id"],
                        "operator": "Equal",
                        "valueText": article_id
                    }
                )
                logger.info(f"🗑️  Deleted old chunks (if any)")
            except Exception as e:
                logger.warning(f"⚠️ Could not delete old chunks: {e}")
            
            # اضافه کردن chunks جدید
            visibility = article.get("visibility", "public")
            category = article.get("category", {}).get("name", "عمومی") if isinstance(article.get("category"), dict) else "عمومی"
            
            with collection.batch.dynamic() as batch:
                for node, vector in zip(nodes, vectors):
                    properties = {
                        "node_id": node.id,
                        "article_id": article_id,
                        "title": node.title,
                        "content": node.content,
                        "full_content": content[:2000],
                        "level": node.level,
                        "path": node.path,
                        "order": node.order,
                        "parent_id": node.parent_id or "",
                        "visibility": visibility,
                        "category": category
                    }
                    batch.add_object(properties=properties, vector=vector)
            
            logger.info(f"✅ Saved {len(nodes)} chunks to Weaviate")
            
            # تایید ذخیره
            result = collection.aggregate.over_all(total_count=True)
            total_count = result.total_count if hasattr(result, 'total_count') else 0
            logger.info(f"📊 Total objects in Weaviate now: {total_count}")
            
            if total_count == 0:
                logger.error("❌ Objects were NOT saved to Weaviate!")
                logger.error("💡 ممکن است مشکلی در Weaviate batch insert وجود داشته باشد")
                return False
        
        logger.info("\n" + "=" * 80)
        logger.info("🎉 SUCCESS! Re-indexing completed successfully!")
        logger.info("=" * 80)
        return True
        
    except Exception as e:
        logger.error(f"❌ Full re-index test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """اجرای تمام تست‌ها"""
    logger.info("\n")
    logger.info("🔍" * 40)
    logger.info("Starting Re-indexing Debug Tests")
    logger.info("🔍" * 40)
    logger.info("\n")
    
    # Test 1: MongoDB
    mongo_ok, mongo_client = await test_mongodb_connection()
    if not mongo_ok:
        logger.error("\n❌ توقف: MongoDB در دسترس نیست")
        return
    
    # Test 2: Weaviate
    weaviate_ok = await test_weaviate_connection()
    if not weaviate_ok:
        logger.error("\n❌ توقف: Weaviate در دسترس نیست")
        mongo_client.close()
        return
    
    # Test 3: OpenAI Embedder
    embedder_ok, openai_client = test_openai_embedder()
    if not embedder_ok:
        logger.error("\n❌ توقف: OpenAI Embedder کار نمی‌کند")
        mongo_client.close()
        return
    
    # Test 4: Markdown Parser
    parser_ok = await test_markdown_parser()
    if not parser_ok:
        logger.error("\n❌ توقف: Markdown Parser کار نمی‌کند")
        mongo_client.close()
        return
    
    # Test 5: Full Re-index
    reindex_ok = await test_full_reindex_single_article(mongo_client, openai_client)
    
    # Cleanup
    mongo_client.close()
    
    # نتیجه نهایی
    logger.info("\n")
    logger.info("=" * 80)
    logger.info("FINAL RESULTS")
    logger.info("=" * 80)
    logger.info(f"MongoDB Connection:    {'✅ PASS' if mongo_ok else '❌ FAIL'}")
    logger.info(f"Weaviate Connection:   {'✅ PASS' if weaviate_ok else '❌ FAIL'}")
    logger.info(f"OpenAI Embedder:       {'✅ PASS' if embedder_ok else '❌ FAIL'}")
    logger.info(f"Markdown Parser:       {'✅ PASS' if parser_ok else '❌ FAIL'}")
    logger.info(f"Full Re-index:         {'✅ PASS' if reindex_ok else '❌ FAIL'}")
    logger.info("=" * 80)
    
    if reindex_ok:
        logger.info("\n🎉 همه چیز کار می‌کند! حالا می‌توانید از API یا Script استفاده کنید")
    else:
        logger.info("\n❌ مشکلاتی وجود دارد. لطفاً خطاهای بالا را بررسی کنید")


if __name__ == "__main__":
    asyncio.run(main())

