"""
🧹 Clean & Re-index Script - پاکسازی کامل و Re-index
=====================================================

این اسکریپت:
1. Collection Weaviate را به طور کامل حذف می‌کند
2. Schema جدید با تنظیمات بهینه می‌سازد
3. تمام مقالات published را به صورت تمیز re-index می‌کند

⚠️ هشدار: این عملیات تمام داده‌های Weaviate را حذف می‌کند!

نحوه اجرا:
    cd sally-backend
    python -m scripts.clean_and_reindex
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.infrastructure.connection_manager import weaviate_client
from app.infrastructure.markdown_parser import markdown_parser
from openai import OpenAI
import logging

# تنظیم logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('clean_and_reindex.log')
    ]
)
logger = logging.getLogger(__name__)


async def step1_delete_collection():
    """مرحله 1: حذف کامل collection"""
    logger.info("\n" + "=" * 80)
    logger.info("STEP 1: DELETE WEAVIATE COLLECTION")
    logger.info("=" * 80)
    
    try:
        with weaviate_client() as client:
            try:
                # بررسی وجود collection
                collection = client.collections.get("MarkdownNode")
                logger.info("Collection 'MarkdownNode' found")
                
                # حذف collection
                logger.warning("Deleting collection...")
                client.collections.delete("MarkdownNode")
                logger.info("✅ Collection deleted successfully")
                
            except Exception as e:
                logger.info(f"Collection does not exist or already deleted: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error deleting collection: {e}")
        return False


async def step2_create_schema():
    """مرحله 2: ایجاد schema جدید با تنظیمات بهینه"""
    logger.info("\n" + "=" * 80)
    logger.info("STEP 2: CREATE NEW SCHEMA")
    logger.info("=" * 80)
    
    try:
        from weaviate.classes.config import Configure, Property, DataType
        
        with weaviate_client() as client:
            # ایجاد collection با schema بهینه
            logger.info("Creating 'MarkdownNode' collection...")
            
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
            
            logger.info("✅ Schema created successfully")
            logger.info("Properties:")
            logger.info("  - node_id (TEXT)")
            logger.info("  - article_id (TEXT)")
            logger.info("  - title (TEXT)")
            logger.info("  - content (TEXT)")
            logger.info("  - full_content (TEXT)")
            logger.info("  - level (INT)")
            logger.info("  - path (TEXT)")
            logger.info("  - order (INT)")
            logger.info("  - parent_id (TEXT)")
            logger.info("  - visibility (TEXT)")
            logger.info("  - category (TEXT)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating schema: {e}")
        return False


async def step3_fetch_articles():
    """مرحله 3: بازیابی مقالات از MongoDB"""
    logger.info("\n" + "=" * 80)
    logger.info("STEP 3: FETCH ARTICLES FROM MONGODB")
    logger.info("=" * 80)
    
    try:
        # اتصال به MongoDB
        logger.info(f"Connecting to: {settings.database_url}")
        mongodb_client = AsyncIOMotorClient(settings.database_url)
        db = mongodb_client.get_database()
        
        # بازیابی مقالات published
        logger.info("Fetching published articles...")
        articles_cursor = db.knowledge_base_articles.find({"status": "published"})
        articles = await articles_cursor.to_list(length=None)
        
        total = len(articles)
        logger.info(f"✅ Found {total} published articles")
        
        if total == 0:
            logger.warning("⚠️ No published articles found!")
            logger.warning("💡 Make sure articles have status='published'")
        
        mongodb_client.close()
        return articles
        
    except Exception as e:
        logger.error(f"❌ Error fetching articles: {e}")
        return []


async def step4_index_articles(articles: list):
    """مرحله 4: Index کردن مقالات در Weaviate"""
    logger.info("\n" + "=" * 80)
    logger.info("STEP 4: INDEX ARTICLES TO WEAVIATE")
    logger.info("=" * 80)
    
    if not articles:
        logger.error("❌ No articles to index!")
        return False
    
    try:
        # راه‌اندازی OpenAI client
        logger.info("Initializing OpenAI client...")
        openai_client = OpenAI(
            api_key=settings.embedder_api_key_loaded,
            base_url=settings.embedder_openai_base_url_loaded
        )
        logger.info(f"✅ Using model: {settings.embedder_model_loaded}")
        
        total_articles = len(articles)
        successful = 0
        failed = 0
        total_chunks = 0
        
        logger.info(f"\nProcessing {total_articles} articles...\n")
        
        for idx, article in enumerate(articles, 1):
            try:
                article_id = str(article["_id"])
                title = article.get("title", "No title")
                content = article.get("content_markdown", "")
                
                logger.info(f"[{idx}/{total_articles}] Processing: {title[:60]}...")
                
                # بررسی محتوا
                if not content or len(content.strip()) < 10:
                    logger.warning(f"  ⚠️ Empty or too short content, skipping")
                    failed += 1
                    continue
                
                # پارس کردن
                logger.info(f"  📝 Parsing markdown...")
                tree = markdown_parser.parse_to_tree(content, article_id, article_title=title)
                nodes = tree.get_all_nodes()
                logger.info(f"  ✅ Generated {len(nodes)} chunks")
                
                if len(nodes) == 0:
                    logger.warning(f"  ⚠️ No chunks generated, skipping")
                    failed += 1
                    continue
                
                # تولید embeddings
                logger.info(f"  🔢 Generating embeddings...")
                texts_to_vectorize = [f"{node.title}\n\n{node.content}" for node in nodes]
                
                response = openai_client.embeddings.create(
                    model=settings.embedder_model_loaded,
                    input=texts_to_vectorize
                )
                vectors = [item.embedding for item in response.data]
                logger.info(f"  ✅ Generated {len(vectors)} embeddings")
                
                # ذخیره در Weaviate
                logger.info(f"  💾 Saving to Weaviate...")
                with weaviate_client() as client:
                    collection = client.collections.get("MarkdownNode")
                    
                    visibility = article.get("visibility", "public")
                    category = article.get("category", {}).get("name", "General") if isinstance(article.get("category"), dict) else "General"
                    
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
                
                total_chunks += len(nodes)
                successful += 1
                logger.info(f"  ✅ Saved {len(nodes)} chunks\n")
                
            except Exception as e:
                logger.error(f"  ❌ Error processing article '{title}': {e}")
                failed += 1
                continue
        
        logger.info("\n" + "=" * 80)
        logger.info("INDEXING COMPLETED")
        logger.info("=" * 80)
        logger.info(f"✅ Successful: {successful}/{total_articles}")
        logger.info(f"❌ Failed: {failed}/{total_articles}")
        logger.info(f"📊 Total chunks indexed: {total_chunks}")
        
        return successful > 0
        
    except Exception as e:
        logger.error(f"❌ Error in indexing process: {e}")
        return False


async def step5_verify():
    """مرحله 5: تایید موفقیت‌آمیز بودن عملیات"""
    logger.info("\n" + "=" * 80)
    logger.info("STEP 5: VERIFY INDEXING")
    logger.info("=" * 80)
    
    try:
        with weaviate_client() as client:
            collection = client.collections.get("MarkdownNode")
            result = collection.aggregate.over_all(total_count=True)
            count = result.total_count if hasattr(result, 'total_count') else 0
            
            logger.info(f"📊 Total chunks in Weaviate: {count}")
            
            if count > 0:
                logger.info("✅ Verification successful!")
                return True
            else:
                logger.error("❌ No data found in Weaviate!")
                return False
                
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False


async def main():
    """اجرای تمام مراحل"""
    logger.info("\n")
    logger.info("🧹" * 40)
    logger.info("CLEAN & RE-INDEX KNOWLEDGE BASE")
    logger.info("🧹" * 40)
    logger.info("\n")
    
    logger.warning("⚠️ WARNING: This will DELETE all data in Weaviate!")
    logger.warning("⚠️ Press Ctrl+C to cancel within 5 seconds...")
    
    try:
        await asyncio.sleep(5)
    except KeyboardInterrupt:
        logger.info("\n❌ Operation cancelled by user")
        return
    
    # مرحله 1: حذف collection
    if not await step1_delete_collection():
        logger.error("❌ Failed at step 1")
        return
    
    # مرحله 2: ایجاد schema
    if not await step2_create_schema():
        logger.error("❌ Failed at step 2")
        return
    
    # مرحله 3: بازیابی مقالات
    articles = await step3_fetch_articles()
    if not articles:
        logger.error("❌ Failed at step 3")
        return
    
    # مرحله 4: Index کردن
    if not await step4_index_articles(articles):
        logger.error("❌ Failed at step 4")
        return
    
    # مرحله 5: تایید
    if not await step5_verify():
        logger.error("❌ Failed at step 5")
        return
    
    logger.info("\n" + "=" * 80)
    logger.info("🎉 SUCCESS! Clean & Re-index completed!")
    logger.info("=" * 80)
    logger.info("\n✅ Your knowledge base is now clean and fully re-indexed")
    logger.info("✅ You can now test RAG queries")


if __name__ == "__main__":
    asyncio.run(main())

