"""
🔄 Re-indexing Knowledge Base Script
=====================================

این اسکریپت برای پاکسازی کامل و re-indexing پایگاه دانش استفاده می‌شود.

مراحل:
1. پاک کردن Weaviate collection
2. ایجاد مجدد schema با تنظیمات بهینه
3. بازیابی تمام مقالات از MongoDB
4. پردازش مجدد با chunking strategy جدید
5. ایندکس کردن مجدد در Weaviate

نحوه اجرا:
    cd sally-backend
    python -m scripts.reindex_knowledge_base
"""

import asyncio
import sys
import os
from pathlib import Path

# اضافه کردن root directory به path
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
        logging.FileHandler('reindex_knowledge_base.log')
    ]
)
logger = logging.getLogger(__name__)


class KnowledgeBaseReindexer:
    """مدیریت فرآیند re-indexing پایگاه دانش"""
    
    def __init__(self):
        self.mongodb_client = None
        self.db = None
        self.openai_client = None
        
    async def initialize(self):
        """راه‌اندازی اتصالات"""
        logger.info("🔌 اتصال به MongoDB...")
        self.mongodb_client = AsyncIOMotorClient(settings.database_url)
        self.db = self.mongodb_client.get_database()
        
        logger.info("🔌 راه‌اندازی OpenAI client برای embeddings...")
        self.openai_client = OpenAI(
            api_key=settings.embedder_api_key_loaded,
            base_url=settings.embedder_openai_base_url_loaded
        )
        
        logger.info("✅ اتصالات برقرار شد")
    
    async def step1_clear_weaviate(self):
        """مرحله 1: پاکسازی کامل Weaviate"""
        logger.info("=" * 80)
        logger.info("🗑️  مرحله 1: پاکسازی Weaviate Collection")
        logger.info("=" * 80)
        
        try:
            with weaviate_client() as client:
                # بررسی وجود collection
                try:
                    collection = client.collections.get("MarkdownNode")
                    logger.info("📋 Collection 'MarkdownNode' پیدا شد")
                    
                    # حذف collection
                    logger.warning("⚠️  در حال حذف collection...")
                    client.collections.delete("MarkdownNode")
                    logger.info("✅ Collection با موفقیت حذف شد")
                    
                except Exception as e:
                    logger.info(f"ℹ️  Collection وجود نداشت یا قبلاً حذف شده: {e}")
                
                # ایجاد مجدد collection با schema بهینه
                logger.info("🏗️  ایجاد مجدد collection با schema بهینه...")
                from weaviate.classes.config import Configure, Property, DataType
                
                # استفاده از "none" vectorizer - ما خودمان vectorها را تولید می‌کنیم
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
                
                logger.info("✅ Collection جدید ایجاد شد")
                logger.info("🎯 Schema بهینه برای Hybrid Search (Vector + BM25)")
                
        except Exception as e:
            logger.error(f"❌ خطا در پاکسازی Weaviate: {e}")
            raise
    
    async def step2_reindex_all_articles(self):
        """مرحله 2: پردازش و ایندکس مجدد تمام مقالات"""
        logger.info("=" * 80)
        logger.info("📚 مرحله 2: پردازش و ایندکس مجدد مقالات")
        logger.info("=" * 80)
        
        try:
            # بازیابی تمام مقالات از MongoDB
            logger.info("🔍 بازیابی مقالات از MongoDB...")
            articles_cursor = self.db.knowledge_base_articles.find({
                "status": "published"
            })
            articles = await articles_cursor.to_list(length=None)
            
            total_articles = len(articles)
            logger.info(f"📊 تعداد مقالات یافت شده: {total_articles}")
            
            if total_articles == 0:
                logger.warning("⚠️  هیچ مقاله‌ای برای ایندکس کردن وجود ندارد!")
                return
            
            # پردازش هر مقاله
            total_chunks = 0
            successful_articles = 0
            
            for idx, article in enumerate(articles, 1):
                try:
                    article_id = str(article["_id"])
                    title = article.get("title", "بدون عنوان")
                    content = article.get("content_markdown", "")
                    
                    logger.info(f"\n{'='*60}")
                    logger.info(f"📄 [{idx}/{total_articles}] پردازش: {title}")
                    logger.info(f"   ID: {article_id}")
                    logger.info(f"   طول محتوا: {len(content)} کاراکتر")
                    
                    if not content or len(content.strip()) < 10:
                        logger.warning(f"   ⚠️  محتوای خالی یا کوتاه - رد شد")
                        continue
                    
                    # 🎯 پارس کردن با chunking strategy جدید (Small-to-Big)
                    logger.info(f"   🔪 تقسیم به chunks (max_size=512, overlap=50)...")
                    tree = markdown_parser.parse_to_tree(
                        content,
                        article_id,
                        article_title=title
                    )
                    
                    nodes = tree.get_all_nodes()
                    logger.info(f"   ✅ {len(nodes)} chunk ایجاد شد")
                    
                    # نمایش آمار chunks
                    chunk_sizes = [len(node.content) for node in nodes]
                    avg_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
                    max_size = max(chunk_sizes) if chunk_sizes else 0
                    min_size = min(chunk_sizes) if chunk_sizes else 0
                    
                    logger.info(f"   📊 آمار chunks:")
                    logger.info(f"      • میانگین: {avg_size:.0f} کاراکتر")
                    logger.info(f"      • حداکثر: {max_size} کاراکتر")
                    logger.info(f"      • حداقل: {min_size} کاراکتر")
                    
                    # ایندکس کردن chunks در Weaviate
                    chunks_indexed = await self._index_chunks_to_weaviate(
                        nodes,
                        article_id,
                        article
                    )
                    
                    total_chunks += chunks_indexed
                    successful_articles += 1
                    
                    logger.info(f"   ✅ {chunks_indexed} chunk با موفقیت ایندکس شد")
                    
                except Exception as e:
                    logger.error(f"   ❌ خطا در پردازش مقاله '{title}': {e}")
                    continue
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ Re-indexing کامل شد!")
            logger.info(f"📊 خلاصه:")
            logger.info(f"   • مقالات موفق: {successful_articles}/{total_articles}")
            logger.info(f"   • کل chunks ایجاد شده: {total_chunks}")
            logger.info(f"   • میانگین chunks به ازای هر مقاله: {total_chunks/successful_articles:.1f}" if successful_articles > 0 else "")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"❌ خطا در re-indexing: {e}")
            raise
    
    async def _index_chunks_to_weaviate(self, nodes, article_id, article_metadata):
        """ایندکس کردن chunks در Weaviate با batch processing"""
        try:
            with weaviate_client() as client:
                collection = client.collections.get("MarkdownNode")
                
                # تولید embeddings برای همه nodes به صورت batch
                logger.info(f"      🔢 تولید embeddings برای {len(nodes)} chunk...")
                
                texts_to_vectorize = [
                    f"{node.title}\n\n{node.content}" 
                    for node in nodes
                ]
                
                # Batch embedding generation
                embedder_model = settings.embedder_model_loaded
                response = self.openai_client.embeddings.create(
                    model=embedder_model,
                    input=texts_to_vectorize
                )
                
                vectors = [item.embedding for item in response.data]
                logger.info(f"      ✅ {len(vectors)} embedding تولید شد")
                
                # Batch insert به Weaviate
                logger.info(f"      💾 ذخیره در Weaviate...")
                
                # آماده‌سازی metadata (safe handling of None)
                if article_metadata is None:
                    article_metadata = {}
                
                visibility = article_metadata.get("visibility", "public")
                
                # Safe category extraction
                category_obj = article_metadata.get("category")
                if category_obj and isinstance(category_obj, dict):
                    category = category_obj.get("name", "عمومی")
                else:
                    category = "عمومی"
                
                # استخراج محتوای کامل مقاله برای context
                full_article_content = article_metadata.get("content_markdown", "")
                
                # Insert با batch
                with collection.batch.dynamic() as batch:
                    for node, vector in zip(nodes, vectors):
                        properties = {
                            "node_id": node.id,
                            "article_id": article_id,
                            "title": node.title,
                            "content": node.content,
                            "full_content": full_article_content[:2000],  # محدود کردن برای عملکرد بهتر
                            "level": node.level,
                            "path": node.path,
                            "order": node.order,
                            "parent_id": node.parent_id or "",
                            "visibility": visibility,
                            "category": category
                        }
                        
                        batch.add_object(
                            properties=properties,
                            vector=vector
                        )
                
                logger.info(f"      ✅ همه chunks ذخیره شدند")
                return len(nodes)
                
        except Exception as e:
            logger.error(f"      ❌ خطا در ایندکس کردن: {e}")
            raise
    
    async def reindex_single_article(self, article_id: str = None, article_title: str = None, remove_old: bool = True):
        """
        ایندکس کردن یک مقاله خاص
        
        Args:
            article_id: شناسه مقاله (اختیاری)
            article_title: عنوان مقاله (اختیاری)
            remove_old: آیا chunks قبلی این مقاله را حذف کنیم؟
        """
        logger.info("=" * 80)
        logger.info("📄 ایندکس کردن مقاله خاص")
        logger.info("=" * 80)
        
        if not article_id and not article_title:
            logger.error("❌ باید حداقل article_id یا article_title را مشخص کنید")
            return
        
        try:
            await self.initialize()
            
            # جستجوی مقاله
            query = {}
            if article_id:
                from bson import ObjectId
                try:
                    query["_id"] = ObjectId(article_id)
                except:
                    query["_id"] = article_id
            elif article_title:
                query["title"] = {"$regex": article_title, "$options": "i"}
            
            logger.info(f"🔍 جستجوی مقاله با معیار: {query}")
            article = await self.db.knowledge_base_articles.find_one(query)
            
            if not article:
                logger.error("❌ مقاله پیدا نشد!")
                return
            
            article_id = str(article["_id"])
            title = article.get("title", "بدون عنوان")
            content = article.get("content_markdown", "")
            
            logger.info(f"✅ مقاله پیدا شد:")
            logger.info(f"   • ID: {article_id}")
            logger.info(f"   • عنوان: {title}")
            logger.info(f"   • طول محتوا: {len(content)} کاراکتر")
            
            if not content or len(content.strip()) < 10:
                logger.warning("⚠️  محتوای خالی یا کوتاه!")
                return
            
            # حذف chunks قبلی (اختیاری)
            if remove_old:
                logger.info("🗑️  حذف chunks قبلی این مقاله از Weaviate...")
                try:
                    with weaviate_client() as client:
                        from weaviate.classes.query import Filter
                        collection = client.collections.get("MarkdownNode")
                        
                        # حذف تمام nodes این مقاله با syntax صحیح Weaviate v4
                        result = collection.data.delete_many(
                            where=Filter.by_property("article_id").equal(article_id)
                        )
                        logger.info(f"   ✅ Chunks قبلی حذف شدند")
                except Exception as e:
                    logger.warning(f"   ⚠️  خطا در حذف chunks قبلی: {e}")
            
            # پارس و تقسیم به chunks
            logger.info(f"🔪 تقسیم به chunks با استراتژی جدید...")
            tree = markdown_parser.parse_to_tree(
                content,
                article_id,
                article_title=title
            )
            
            nodes = tree.get_all_nodes()
            logger.info(f"✅ {len(nodes)} chunk ایجاد شد")
            
            # نمایش آمار
            chunk_sizes = [len(node.content) for node in nodes]
            if chunk_sizes:
                logger.info(f"📊 آمار chunks:")
                logger.info(f"   • تعداد: {len(chunk_sizes)}")
                logger.info(f"   • میانگین اندازه: {sum(chunk_sizes)/len(chunk_sizes):.0f} کاراکتر")
                logger.info(f"   • حداکثر: {max(chunk_sizes)} کاراکتر")
                logger.info(f"   • حداقل: {min(chunk_sizes)} کاراکتر")
            
            # ایندکس در Weaviate
            chunks_indexed = await self._index_chunks_to_weaviate(
                nodes,
                article_id,
                article
            )
            
            logger.info("=" * 80)
            logger.info(f"✅ مقاله '{title}' با موفقیت ایندکس شد!")
            logger.info(f"   • {chunks_indexed} chunk ذخیره شد")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"❌ خطا در ایندکس کردن مقاله: {e}", exc_info=True)
        finally:
            if self.mongodb_client:
                self.mongodb_client.close()
    
    async def reindex_multiple_articles(self, article_ids: list = None, article_titles: list = None):
        """
        ایندکس کردن چند مقاله خاص
        
        Args:
            article_ids: لیست شناسه مقالات
            article_titles: لیست عنوان مقالات
        """
        logger.info("=" * 80)
        logger.info("📚 ایندکس کردن چند مقاله خاص")
        logger.info("=" * 80)
        
        try:
            await self.initialize()
            
            # ساخت query
            query = {"$or": []}
            
            if article_ids:
                from bson import ObjectId
                for aid in article_ids:
                    try:
                        query["$or"].append({"_id": ObjectId(aid)})
                    except:
                        query["$or"].append({"_id": aid})
            
            if article_titles:
                for title in article_titles:
                    query["$or"].append({"title": {"$regex": title, "$options": "i"}})
            
            if not query["$or"]:
                logger.error("❌ باید حداقل یک article_id یا article_title مشخص کنید")
                return
            
            # بازیابی مقالات
            logger.info(f"🔍 جستجوی مقالات...")
            articles_cursor = self.db.knowledge_base_articles.find(query)
            articles = await articles_cursor.to_list(length=None)
            
            total = len(articles)
            logger.info(f"✅ {total} مقاله پیدا شد")
            
            if total == 0:
                logger.warning("⚠️  هیچ مقاله‌ای پیدا نشد!")
                return
            
            # پردازش هر مقاله
            successful = 0
            total_chunks = 0
            
            for idx, article in enumerate(articles, 1):
                try:
                    article_id = str(article["_id"])
                    title = article.get("title", "بدون عنوان")
                    
                    logger.info(f"\n[{idx}/{total}] پردازش: {title}")
                    
                    # حذف chunks قبلی (skip delete - اگر وجود نداشت خطا نمی‌دهد)
                    try:
                        with weaviate_client() as client:
                            from weaviate.classes.query import Filter
                            collection = client.collections.get("MarkdownNode")
                            # استفاده از syntax صحیح Weaviate v4
                            collection.data.delete_many(
                                where=Filter.by_property("article_id").equal(article_id)
                            )
                            logger.info(f"   🗑️  Chunks قبلی حذف شد")
                    except Exception as delete_error:
                        # اگر chunks قبلی وجود نداشت، مشکلی نیست
                        logger.debug(f"   ℹ️  No previous chunks to delete or delete failed: {delete_error}")
                    
                    # پارس و ایندکس
                    content = article.get("content_markdown", "")
                    tree = markdown_parser.parse_to_tree(content, article_id, article_title=title)
                    nodes = tree.get_all_nodes()
                    
                    chunks_indexed = await self._index_chunks_to_weaviate(nodes, article_id, article)
                    
                    total_chunks += chunks_indexed
                    successful += 1
                    logger.info(f"   ✅ {chunks_indexed} chunk ذخیره شد")
                    
                except Exception as e:
                    logger.error(f"   ❌ خطا: {e}")
                    continue
            
            logger.info("\n" + "=" * 80)
            logger.info(f"✅ عملیات تکمیل شد!")
            logger.info(f"   • مقالات موفق: {successful}/{total}")
            logger.info(f"   • کل chunks: {total_chunks}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"❌ خطا: {e}", exc_info=True)
        finally:
            if self.mongodb_client:
                self.mongodb_client.close()
    
    async def run(self):
        """اجرای کامل فرآیند re-indexing"""
        try:
            logger.info("\n" + "=" * 80)
            logger.info("🚀 شروع Re-indexing Knowledge Base")
            logger.info("=" * 80)
            logger.info("")
            logger.info("⚠️  هشدار: این عملیات تمام داده‌های Weaviate را پاک می‌کند!")
            logger.info("⚠️  مطمئن شوید که از MongoDB backup دارید.")
            logger.info("")
            
            # درخواست تأیید
            confirmation = input("آیا می‌خواهید ادامه دهید؟ (yes/no): ")
            if confirmation.lower() not in ['yes', 'y', 'بله']:
                logger.info("❌ عملیات لغو شد")
                return
            
            await self.initialize()
            
            # مرحله 1: پاکسازی
            await self.step1_clear_weaviate()
            
            # مرحله 2: Re-indexing
            await self.step2_reindex_all_articles()
            
            logger.info("\n🎉 تمام مراحل با موفقیت انجام شد!")
            logger.info("💡 اکنون می‌توانید سیستم RAG را تست کنید")
            
        except KeyboardInterrupt:
            logger.warning("\n⚠️  عملیات توسط کاربر متوقف شد")
        except Exception as e:
            logger.error(f"\n❌ خطای غیرمنتظره: {e}", exc_info=True)
        finally:
            if self.mongodb_client:
                self.mongodb_client.close()
                logger.info("🔌 اتصال MongoDB بسته شد")


async def main():
    """نقطه ورود اصلی با منوی تعاملی"""
    print("\n" + "=" * 80)
    print("🔄 Knowledge Base Re-indexing Tool")
    print("=" * 80)
    print("\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:\n")
    print("1️⃣  Re-index همه مقالات (پاکسازی کامل + ایندکس مجدد)")
    print("2️⃣  ایندکس یک مقاله خاص با ID")
    print("3️⃣  ایندکس یک مقاله خاص با عنوان")
    print("4️⃣  ایندکس چند مقاله با ID های متعدد")
    print("5️⃣  ایندکس چند مقاله با عناوین متعدد")
    print("0️⃣  خروج")
    print("=" * 80)
    
    choice = input("\n➡️  انتخاب شما (0-5): ").strip()
    
    reindexer = KnowledgeBaseReindexer()
    
    if choice == "1":
        # Re-index همه
        await reindexer.run()
        
    elif choice == "2":
        # ایندکس با ID
        article_id = input("\n📝 Article ID را وارد کنید: ").strip()
        if article_id:
            remove_old = input("🗑️  chunks قبلی حذف شوند؟ (yes/no, پیش‌فرض: yes): ").strip().lower()
            remove_old = remove_old in ['', 'yes', 'y', 'بله']
            await reindexer.reindex_single_article(article_id=article_id, remove_old=remove_old)
        else:
            logger.error("❌ Article ID نمی‌تواند خالی باشد")
            
    elif choice == "3":
        # ایندکس با عنوان
        article_title = input("\n📝 عنوان مقاله را وارد کنید (یا بخشی از آن): ").strip()
        if article_title:
            remove_old = input("🗑️  chunks قبلی حذف شوند؟ (yes/no, پیش‌فرض: yes): ").strip().lower()
            remove_old = remove_old in ['', 'yes', 'y', 'بله']
            await reindexer.reindex_single_article(article_title=article_title, remove_old=remove_old)
        else:
            logger.error("❌ عنوان مقاله نمی‌تواند خالی باشد")
            
    elif choice == "4":
        # ایندکس چند مقاله با ID
        print("\n📝 Article ID ها را وارد کنید (با کاما جدا شوند):")
        ids_input = input("➡️  ").strip()
        if ids_input:
            article_ids = [aid.strip() for aid in ids_input.split(',') if aid.strip()]
            await reindexer.reindex_multiple_articles(article_ids=article_ids)
        else:
            logger.error("❌ حداقل یک Article ID لازم است")
            
    elif choice == "5":
        # ایندکس چند مقاله با عنوان
        print("\n📝 عناوین مقالات را وارد کنید (با کاما جدا شوند):")
        titles_input = input("➡️  ").strip()
        if titles_input:
            article_titles = [title.strip() for title in titles_input.split(',') if title.strip()]
            await reindexer.reindex_multiple_articles(article_titles=article_titles)
        else:
            logger.error("❌ حداقل یک عنوان لازم است")
            
    elif choice == "0":
        logger.info("👋 خروج از برنامه")
        
    else:
        logger.error("❌ انتخاب نامعتبر! لطفاً عددی بین 0 تا 5 وارد کنید")


if __name__ == "__main__":
    # اجرای async
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  برنامه توسط کاربر متوقف شد")
    except Exception as e:
        print(f"\n❌ خطای غیرمنتظره: {e}")

