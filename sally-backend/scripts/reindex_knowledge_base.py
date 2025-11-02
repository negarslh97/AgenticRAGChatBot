# reindex_knowledge_base.py

"""
🔄 Re-indexing Knowledge Base Script
=====================================
این اسکریپت برای پاکسازی کامل و re-indexing پایگاه دانش استفاده می‌شود.
"""

import asyncio
import sys
from pathlib import Path

# اضافه کردن root directory به path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.infrastructure.connection_manager import weaviate_client
from app.infrastructure.markdown_parser import markdown_parser
# ✅ وارد کردن تابع جدید و صحیح
from app.core.weaviate_utils import create_unified_collection, get_weaviate_collection_name
import logging

# ... (بقیه تنظیمات logging بدون تغییر باقی می‌ماند) ...
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
        
    async def initialize(self):
        """راه‌اندازی اتصالات"""
        logger.info("اتصال به MongoDB...")
        self.mongodb_client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.mongodb_client.get_database()
        logger.info("اتصالات برقرار شد")
    
    async def step1_clear_weaviate(self):
        """مرحله 1: پاکسازی و ایجاد مجدد Weaviate Collection به روش صحیح"""
        logger.info("=" * 80)
        logger.info("مرحله 1: پاکسازی و ایجاد مجدد Weaviate Collection")
        logger.info("=" * 80)

        try:
            with weaviate_client() as client:
                collection_name = get_weaviate_collection_name()

                # حذف collection موجود (اگر وجود دارد)
                if client.collections.exists(collection_name):
                    logger.warning(f"در حال حذف collection '{collection_name}'...")
                    client.collections.delete(collection_name)
                    logger.info("Collection با موفقیت حذف شد")
                else:
                    logger.info(f"Collection '{collection_name}' وجود نداشت.")

                # =======================================================
                # ✅✅✅ تغییر کلیدی: فراخوانی تابع یکپارچه برای ایجاد مجدد
                # =======================================================
                logger.info("ایجاد مجدد collection با استفاده از weaviate_utils...")
                # چون این تابع سینک است، نیازی به await نیست
                success = create_unified_collection()
                if not success:
                    raise Exception("ایجاد مجدد Collection ناموفق بود. لاگ‌ها را بررسی کنید.")

                logger.info("Collection جدید با schema صحیح ایجاد شد.")

        except Exception as e:
            logger.error(f"خطا در پاکسازی و ایجاد مجدد Weaviate: {e}")
            raise

    # ... (متدهای دیگر مانند step2_reindex_all_articles و _index_chunks_to_weaviate بدون تغییر باقی می‌مانند) ...
    # ... فقط مطمئن شوید که properties ارسالی در _index_chunks_to_weaviate با schema جدید مطابقت دارد ...
    # ... که در نسخه بعدی weaviate_utils آن را تضمین می‌کنیم ...
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
                    logger.info(f"[{idx}/{total_articles}] پردازش: {title}")

                    if not content or len(content.strip()) < 10:
                        logger.warning(f"   محتوای خالی یا کوتاه - رد شد")
                        continue

                    tree = markdown_parser.parse_to_tree(
                        content,
                        article_id,
                        article_title=title
                    )

                    nodes = tree.get_all_nodes()
                    logger.info(f"   {len(nodes)} chunk ایجاد شد")

                    chunks_indexed = await self._index_chunks_to_weaviate(
                        nodes,
                        article_id,
                        article
                    )

                    total_chunks += chunks_indexed
                    successful_articles += 1

                    logger.info(f"   {chunks_indexed} chunk با موفقیت ایندکس شد")
                    
                except Exception as e:
                    logger.error(f"   ❌ خطا در پردازش مقاله '{title}': {e}")
                    continue
            
            logger.info("\n" + "=" * 80)
            logger.info("Re-indexing کامل شد!")
            logger.info(f"خلاصه:")
            logger.info(f"   • مقالات موفق: {successful_articles}/{total_articles}")
            logger.info(f"   • کل chunks ایجاد شده: {total_chunks}")
            
        except Exception as e:
            logger.error(f"❌ خطا در re-indexing: {e}")
            raise
    
    async def _index_chunks_to_weaviate(self, nodes, article_id, article_metadata):
        """ایندکس کردن chunks در Weaviate با Server-Side Vectorization"""
        try:
            with weaviate_client() as client:
                collection_name = get_weaviate_collection_name()
                collection = client.collections.get(collection_name)

                logger.info(f"      ذخیره در Weaviate (Server-Side)...")

                visibility = article_metadata.get("visibility", "public")
                category_obj = article_metadata.get("category")
                category = category_obj.get("name", "عمومی") if category_obj and isinstance(category_obj, dict) else "عمومی"
                full_article_content = article_metadata.get("content_markdown", "")

                with collection.batch.dynamic() as batch:
                    for node in nodes:
                        properties = {
                            "node_id": node.id,
                            "article_id": article_id,
                            "title": node.title,
                            "content": node.content,
                            "full_content": full_article_content,
                            "level": node.level,
                            "path": node.path,
                            "order": node.order,
                            "parent_id": node.parent_id or "",
                            "visibility": visibility,
                            "category": category,
                            "embedder_model": settings.embedder_model_loaded # اضافه کردن فیلد جدید
                        }
                        batch.add_object(properties=properties)

                return len(nodes)

        except Exception as e:
            logger.error(f"      خطا در ایندکس کردن: {e}")
            raise

    # ... بقیه کلاس و تابع main() بدون تغییر ...
    # ... (کد طولانی است و برای خلاصه شدن حذف شده، نیازی به تغییر ندارد) ...
    async def run(self):
        """اجرای کامل فرآیند re-indexing"""
        try:
            logger.info("\n" + "=" * 80)
            logger.info("شروع Re-indexing Knowledge Base")
            logger.info("=" * 80)

            confirmation = input("آیا می‌خواهید ادامه دهید؟ (yes/no): ")
            if confirmation.lower() not in ['yes', 'y', 'بله']:
                logger.info("عملیات لغو شد")
                return

            await self.initialize()
            await self.step1_clear_weaviate()
            await self.step2_reindex_all_articles()

            logger.info("\nتمام مراحل با موفقیت انجام شد!")

        except KeyboardInterrupt:
            logger.warning("\nعملیات توسط کاربر متوقف شد")
        except Exception as e:
            logger.error(f"\nخطای غیرمنتظره: {e}", exc_info=True)
        finally:
            if self.mongodb_client:
                self.mongodb_client.close()
                logger.info("اتصال MongoDB بسته شد")

async def main():
    # ... (این بخش نیازی به تغییر ندارد) ...
    print("\n" + "=" * 80)
    print("Knowledge Base Re-indexing Tool")
    print("=" * 80)
    print("\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:\n")
    print("1. Re-index همه مقالات (پاکسازی کامل + ایندکس مجدد)")
    print("0. خروج")
    print("=" * 80)
    
    choice = input("\nانتخاب شما (0-1): ").strip()

    reindexer = KnowledgeBaseReindexer()

    if choice == "1":
        await reindexer.run()
    else:
        logger.info("خروج از برنامه")

if __name__ == "__main__":
    asyncio.run(main())
