"""
Knowledge Base Repository - عملیات ذخیره‌سازی پیشرفته پایگاه دانش

این فایل عملیات CRUD پیشرفته برای KnowledgeBaseArticle و وابستگی‌های آن را مدیریت می‌کند.
شامل عملیات ذخیره‌سازی در MongoDB و همگام‌سازی با Weaviate.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from bson import ObjectId
import logging

from app.domain.entities import (
    KnowledgeBaseArticle, ArticleStatus, ArticleVisibility,
    Category, Tag, ArticleCategory, ArticleTag, Admin
)
from app.core.config import settings
from app.core.exceptions import RepositoryError, WeaviateError, DatabaseError

logger = logging.getLogger(__name__)


class KnowledgeBaseRepository:
    """
    Repository برای مدیریت عملیات پایگاه دانش در MongoDB و Weaviate
    
    ✅ همه متدها از Connection Manager استفاده می‌کنند و اتصالات را به درستی مدیریت می‌کنند
    """

    def __init__(self):
        # ✅ دیگر نیازی به نگهداری client در repository نیست
        # همه متدها از Connection Manager استفاده می‌کنند
        pass

    # =============== ARTICLE CRUD OPERATIONS ===============

    async def create_article(
        self,
        title: str,
        content_markdown: str,
        content_html: str,
        author_id: str,
        category_id: Optional[str] = None,
        tag_names: Optional[List[str]] = None,
        summary: Optional[str] = None,
        status: ArticleStatus = ArticleStatus.DRAFT,
        visibility: Optional[ArticleVisibility] = None
    ) -> KnowledgeBaseArticle:
        """
        ایجاد مقاله جدید در MongoDB و همگام‌سازی با Weaviate اگر منتشر شده باشد

        Args:
            title: عنوان مقاله
            content_markdown: محتوای markdown
            content_html: محتوای HTML رندر شده
            author_id: شناسه نویسنده
            category_id: شناسه دسته‌بندی (اختیاری)
            tag_names: لیست نام تگ‌ها (اختیاری)
            summary: خلاصه مقاله (اختیاری)
            status: وضعیت مقاله
            visibility: سطح دسترسی

        Returns:
            مقاله ایجاد شده
        """
        try:
            # آماده‌سازی category
            category = None
            if category_id:
                category_obj = await Category.get(category_id)
                if category_obj:
                    category = ArticleCategory(
                        id=str(category_obj.id),
                        name=category_obj.name,
                        slug=category_obj.slug
                    )

            # آماده‌سازی tags
            tags = []
            if tag_names:
                tags = await self._prepare_tags(tag_names)

            # ایجاد مقاله جدید
            new_article = KnowledgeBaseArticle(
                title=title,
                content_markdown=content_markdown,
                content_html=content_html,
                summary=summary,
                category=category,
                tags=tags,
                status=status,
                visibility=visibility,
                author_id=author_id,
                version=1,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            # ذخیره در MongoDB
            await new_article.insert()
            logger.info(f"✅ مقاله '{title}' در MongoDB ذخیره شد - ID: {new_article.id}")

            # همگام‌سازی با Weaviate فقط برای مقالات منتشر شده
            if status == ArticleStatus.PUBLISHED:
                await self._sync_to_weaviate(new_article, "create")
                logger.info(f"🔄 مقاله '{title}' به Weaviate منتقل شد (PUBLISHED)")
            else:
                logger.info(f"ℹ️ مقاله '{title}' در وضعیت {status} است - به Weaviate منتقل نشد")

            return new_article

        except Exception as e:
            logger.error(f"❌ خطا در ایجاد مقاله: {str(e)}")
            raise

    async def get_article_by_id(self, article_id: str) -> Optional[KnowledgeBaseArticle]:
        """دریافت مقاله بر اساس ID"""
        try:
            return await KnowledgeBaseArticle.get(article_id)
        except Exception as e:
            logger.error(f"❌ خطا در دریافت مقاله {article_id}: {str(e)}")
            return None

    async def get_articles(
        self,
        status: Optional[ArticleStatus] = None,
        visibility: Optional[ArticleVisibility] = None,
        category_id: Optional[str] = None,
        author_id: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[KnowledgeBaseArticle]:
        """
        دریافت لیست مقالات با فیلترهای مختلف

        Args:
            status: فیلتر وضعیت مقاله
            visibility: فیلتر سطح دسترسی
            category_id: فیلتر دسته‌بندی
            author_id: فیلتر نویسنده
            limit: حداکثر تعداد نتایج
            skip: رد کردن تعداد نتایج

        Returns:
            لیست مقالات
        """
        try:
            query = {}

            if status:
                query["status"] = status
            if visibility:
                query["visibility"] = visibility
            if category_id:
                query["category.id"] = category_id
            if author_id:
                query["author_id"] = author_id

            articles = await KnowledgeBaseArticle.find(query).skip(skip).limit(limit).to_list()
            return articles

        except Exception as e:
            logger.error(f"❌ خطا در دریافت مقالات: {str(e)}")
            return []

    async def update_article(
        self,
        article_id: str,
        updates: Dict[str, Any],
        updated_by: str,
        new_version: bool = True
    ) -> Optional[KnowledgeBaseArticle]:
        """
        بروزرسانی مقاله

        Args:
            article_id: شناسه مقاله
            updates: فیلدهای قابل بروزرسانی
            updated_by: شناسه بروزرسان‌کننده
            new_version: آیا نسخه جدید ایجاد شود

        Returns:
            مقاله بروزرسانی شده یا None
        """
        try:
            article = await KnowledgeBaseArticle.get(article_id)
            if not article:
                return None

            # اعمال بروزرسانی‌ها
            for key, value in updates.items():
                if hasattr(article, key):
                    setattr(article, key, value)

            # بروزرسانی metadata
            article.updated_at = datetime.utcnow()
            if new_version:
                article.version += 1

            # ذخیره در MongoDB
            await article.save()
            logger.info(f"✅ مقاله '{article.title}' بروزرسانی شد - نسخه: {article.version}")

            # همگام‌سازی با Weaviate فقط برای مقالات منتشر شده
            if article.status == ArticleStatus.PUBLISHED:
                await self._sync_to_weaviate(article, "update")
                logger.info(f"🔄 مقاله '{article.title}' در Weaviate بروزرسانی شد")
            else:
                # اگر مقاله از PUBLISHED به غیر PUBLISHED تغییر کرد، از Weaviate حذف شود
                await self._sync_to_weaviate(article, "delete")
                logger.info(f"🗑️ مقاله '{article.title}' از Weaviate حذف شد (وضعیت: {article.status})")

            return article

        except Exception as e:
            logger.error(f"❌ خطا در بروزرسانی مقاله {article_id}: {str(e)}")
            return None

    async def publish_article(
        self,
        article_id: str,
        visibility: ArticleVisibility,
        publisher: Admin
    ) -> Optional[KnowledgeBaseArticle]:
        """
        انتشار مقاله

        Args:
            article_id: شناسه مقاله
            visibility: سطح دسترسی
            publisher: ناشر مقاله

        Returns:
            مقاله منتشر شده
        """
        try:
            article = await KnowledgeBaseArticle.get(article_id)
            if not article:
                return None

            # بروزرسانی وضعیت انتشار
            updates = {
                "status": ArticleStatus.PUBLISHED,
                "visibility": visibility,
                "published_at": datetime.utcnow(),
                "publisher_id": str(publisher.id)
            }

            return await self.update_article(article_id, updates, str(publisher.id), new_version=True)

        except Exception as e:
            logger.error(f"❌ خطا در انتشار مقاله {article_id}: {str(e)}")
            return None

    async def delete_article(self, article_id: str) -> bool:
        """
        حذف مقاله از MongoDB و Weaviate

        Args:
            article_id: شناسه مقاله

        Returns:
            True اگر حذف موفق بود
        """
        try:
            article = await KnowledgeBaseArticle.get(article_id)
            if not article:
                return False

            # ✅ حذف از Weaviate (قبلاً کد تکراری بود، حالا فقط یکبار فراخوانی می‌شود)
            await self._sync_to_weaviate(article, "delete")

            # حذف از MongoDB
            await article.delete()
            logger.info(f"✅ مقاله '{article.title}' حذف شد")

            return True

        except Exception as e:
            logger.error(f"❌ خطا در حذف مقاله {article_id}: {str(e)}")
            return False

    # =============== SEARCH OPERATIONS ===============

    async def search_articles(
        self,
        query: str,
        visibility_filter: Optional[List[ArticleVisibility]] = None,
        category_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        جستجوی پیشرفته در مقالات

        Args:
            query: عبارت جستجو
            visibility_filter: فیلتر سطح دسترسی
            category_id: فیلتر دسته‌بندی
            limit: حداکثر تعداد نتایج

        Returns:
            لیست نتایج جستجو با امتیاز
        """
        try:
            # ابتدا جستجو در Weaviate اگر فعال باشد
            weaviate_results = await self._search_weaviate(query, visibility_filter, category_id, limit)
            if weaviate_results:
                return weaviate_results

            # fallback به جستجوی ساده MongoDB
            return await self._search_mongodb(query, visibility_filter, category_id, limit)

        except Exception as e:
            logger.error(f"❌ خطا در جستجو: {str(e)}")
            return []

    async def _search_weaviate(
        self,
        query: str,
        visibility_filter: Optional[List[ArticleVisibility]] = None,
        category_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """جستجو در Weaviate با استفاده از Server-Side Vectorization (near_text)"""
        try:
            from app.infrastructure.connection_manager import weaviate_client
            from app.core.weaviate_utils import get_weaviate_collection_name

            # تعیین collection بر اساس مدل embedder
            collection_name = get_weaviate_collection_name()

            logger.info(f"🔍 جستجو در collection: {collection_name} با استفاده از near_text")

            with weaviate_client() as client:
                collection = client.collections.get(collection_name)

                # ✅ استفاده از near_text - Weaviate خودش query را به بردار تبدیل می‌کند
                search_response = collection.query.near_text(
                    query=query,  # فقط متن خام را ارسال کنید
                    limit=limit,
                    return_metadata=['distance', 'certainty']
                )

                processed_results = []
                seen_article_ids = set()

                for obj in search_response.objects:
                    article_id = obj.properties.get("article_id", "")

                    # جلوگیری از تکرار مقالات
                    if article_id in seen_article_ids:
                        continue
                    seen_article_ids.add(article_id)

                    certainty = obj.metadata.certainty if hasattr(obj.metadata, 'certainty') else 0.5

                    processed_results.append({
                        "id": article_id,
                        "title": obj.properties.get("title", ""),
                        "summary": obj.properties.get("content", "")[:200],
                        "score": certainty,
                        "source": "weaviate"
                    })

                return processed_results
            # ✅ client به صورت خودکار بسته می‌شود

        except Exception as e:
            logger.error(f"❌ خطا در جستجوی Weaviate با near_text: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise WeaviateError(f"خطا در جستجوی Weaviate: {e}", {"query": query}) from e

    async def _search_mongodb(
        self,
        query: str,
        visibility_filter: Optional[List[ArticleVisibility]] = None,
        category_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """جستجوی ساده در MongoDB"""
        try:
            # ساخت query
            mongo_query = {"status": ArticleStatus.PUBLISHED.value}

            if visibility_filter:
                mongo_query["visibility"] = {"$in": [v.value for v in visibility_filter]}

            if category_id:
                mongo_query["category.id"] = category_id

            # دریافت مقالات
            articles = await KnowledgeBaseArticle.find(mongo_query).to_list()

            # جستجوی متنی ساده
            query_lower = query.lower()
            results = []

            for article in articles:
                score = 0

                # امتیازدهی بر اساس تطابق در عنوان
                if any(word in article.title.lower() for word in query_lower.split()):
                    score += 10

                # امتیازدهی بر اساس تطابق در محتوا
                content_matches = sum(1 for word in query_lower.split()
                                    if word in article.content_html.lower())
                score += content_matches * 2

                # امتیازدهی بر اساس تطابق در خلاصه
                if article.summary and any(word in article.summary.lower()
                                         for word in query_lower.split()):
                    score += 7

                if score > 0:
                    results.append({
                        "id": str(article.id),
                        "title": article.title,
                        "summary": article.summary,
                        "score": score,
                        "source": "mongodb"
                    })

            # مرتب‌سازی بر اساس امتیاز
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]

        except Exception as e:
            logger.error(f"❌ خطا در جستجوی MongoDB: {str(e)}")
            return []

    # =============== CATEGORY OPERATIONS ===============

    async def get_categories(
        self,
        include_private: bool = False
    ) -> List[Category]:
        """دریافت لیست دسته‌بندی‌ها"""
        try:
            query = {} if include_private else {"is_public": True}
            return await Category.find(query).to_list()
        except Exception as e:
            logger.error(f"❌ خطا در دریافت دسته‌بندی‌ها: {str(e)}")
            return []

    # =============== HELPER METHODS ===============

    async def _prepare_tags(self, tag_names: List[str]) -> List[ArticleTag]:
        """آماده‌سازی تگ‌ها برای مقاله"""
        article_tags = []

        for tag_name in tag_names:
            # جستجوی تگ موجود
            tag = await Tag.find_one(Tag.name == tag_name.strip())

            if not tag:
                # ایجاد تگ جدید
                tag = Tag(name=tag_name.strip())
                await tag.insert()

            article_tags.append(ArticleTag(
                id=str(tag.id),
                name=tag.name,
                color=tag.color
            ))

        return article_tags

    async def check_article_in_weaviate(self, article_id: str) -> bool:
        """
        بررسی وجود مقاله در Weaviate در collection مناسب

        Args:
            article_id: شناسه مقاله

        Returns:
            True اگر مقاله در Weaviate وجود داشته باشد
        """
        try:
            # ✅ استفاده از Connection Manager به جای ایجاد اتصال جدید
            from app.infrastructure.connection_manager import weaviate_client
            from weaviate.classes.query import Filter
            from app.core.weaviate_utils import get_weaviate_collection_name

            # بررسی collection مناسب
            collection_name = get_weaviate_collection_name()

            logger.info(f"🔍 بررسی مقاله {article_id} در collection: {collection_name}")

            with weaviate_client() as client:
                # جستجوی گره‌های مربوط به این article_id
                collection = client.collections.get(collection_name)

                # Query for nodes with this article_id using proper Filter syntax
                response = collection.query.fetch_objects(
                    filters=Filter.by_property("article_id").equal(article_id),
                    limit=1
                )

                has_nodes = len(response.objects) > 0

                if has_nodes:
                    logger.info(f"✅ مقاله {article_id} در {collection_name} یافت شد ({len(response.objects)} گره)")
                else:
                    logger.info(f"❌ مقاله {article_id} در {collection_name} یافت نشد")

                return has_nodes
            # ✅ client به صورت خودکار بسته می‌شود

        except Exception as e:
            logger.error(f"❌ خطا در بررسی وجود مقاله در Weaviate: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise WeaviateError(f"خطا در بررسی وجود مقاله {article_id}: {e}") from e

    async def check_multiple_articles_in_weaviate(self, article_ids: List[str]) -> Dict[str, bool]:
        """
        🔥 بررسی وجود چندین مقاله در Weaviate با یک connection

        این متد به جای باز کردن connection جداگانه برای هر مقاله،
        یک connection واحد استفاده می‌کند و کارایی را بهبود می‌بخشد.

        Args:
            article_ids: لیست شناسه‌های مقالات

        Returns:
            دیکشنری که کلید article_id و مقدار True/False است
        """
        result = {aid: False for aid in article_ids}

        if not article_ids:
            return result

        try:
            from app.infrastructure.connection_manager import weaviate_client
            from weaviate.classes.query import Filter
            from app.core.weaviate_utils import get_weaviate_collection_name

            # تعیین collection بر اساس مدل embedder
            collection_name = get_weaviate_collection_name()

            logger.info(f"🔍 بررسی چندین مقاله در collection: {collection_name}")

            with weaviate_client() as client:
                collection = client.collections.get(collection_name)

                # 🔍 دیباگ: بررسی وضعیت collection قبل از query
                logger.info(f"🔍 DEBUG: Collection exists: {client.collections.exists(collection_name)}")
                logger.info(f"🔍 DEBUG: Client ready: {client.is_ready()}")

                # بررسی هر مقاله با یک connection
                for article_id in article_ids:
                    try:
                        response = collection.query.fetch_objects(
                            filters=Filter.by_property("article_id").equal(article_id),
                            limit=1
                        )
                        result[article_id] = len(response.objects) > 0
                    except Exception as e:
                        logger.warning(f"⚠️ خطا در بررسی مقاله {article_id}: {e}")
                        result[article_id] = False

                synced_count = sum(1 for v in result.values() if v)
                logger.info(f"✅ بررسی {len(article_ids)} مقاله در {collection_name}: {synced_count} همگام‌سازی شده")

                return result
            # ✅ client به صورت خودکار بسته می‌شود

        except Exception as e:
            logger.error(f"❌ خطا در بررسی وجود چندین مقاله در Weaviate: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise WeaviateError(f"خطا در بررسی وجود چندین مقاله: {e}") from e

    async def _sync_to_weaviate(
        self,
        article: KnowledgeBaseArticle,
        operation: str
    ) -> None:
        """
        همگام‌سازی مقاله با Weaviate با استراتژی ساده "حذف و ایجاد مجدد".
        این متد از Server-Side Vectorization استفاده می‌کند.

        Args:
            article: مقاله برای همگام‌سازی
            operation: نوع عملیات (create/update/delete)
        """
        try:
            from app.infrastructure.connection_manager import weaviate_client
            from app.core.config import settings
            from app.infrastructure.markdown_parser import markdown_parser
            from weaviate.classes.query import Filter

            # تعیین collection بر اساس مدل embedder
            from app.core.weaviate_utils import get_weaviate_collection_name
            collection_name = get_weaviate_collection_name()
            logger.info(f"🔄 همگام‌سازی مقاله '{article.title}' با collection: {collection_name}")

            with weaviate_client() as client:
                collection = client.collections.get(collection_name)

                # 1. همیشه گره‌های قدیمی این مقاله را حذف کن (برای create و update)
                if operation in ["create", "update"]:
                    collection.data.delete_many(
                        where=Filter.by_property("article_id").equal(str(article.id))
                    )
                    logger.info(f"🗑️ گره‌های قدیمی مقاله '{article.title}' از {collection_name} برای همگام‌سازی حذف شدند.")

                # 2. اگر عملیات حذف است، کار تمام است
                if operation == "delete":
                    collection.data.delete_many(
                        where=Filter.by_property("article_id").equal(str(article.id))
                    )
                    logger.info(f"🗑️ گره‌های مقاله '{article.title}' از {collection_name} حذف شدند.")

                    # برای عملیات delete، last_synced_at را ریست نکنید
                    # چون مقاله ممکن است دوباره منتشر شود
                    return

                # 3. اگر مقاله منتشر شده است، گره‌های جدید را اضافه کن
                if article.status != ArticleStatus.PUBLISHED:
                    logger.info(f"ℹ️ مقاله '{article.title}' در وضعیت {article.status} است، گره جدیدی به Weaviate اضافه نشد.")
                    return

                # پارس کردن محتوای جدید
                tree = markdown_parser.parse_to_tree(article.content_markdown, str(article.id))
                all_nodes = tree.get_all_nodes()

                if not all_nodes:
                    logger.warning(f"⚠️ مقاله '{article.title}' ساختار Markdown قابل پارسی نداشت.")
                    return

                # ✅ استفاده از Batch Insert برای درج تمام گره‌ها در یک درخواست
                with collection.batch.dynamic() as batch:
                    for node in all_nodes:
                        properties = self._node_to_properties(node, article)
                        # فقط properties را ارسال می‌کنیم، Weaviate خودش بردار را تولید خواهد کرد
                        batch.add_object(properties=properties)

                logger.info(f"✅ {len(all_nodes)} گره برای مقاله '{article.title}' با موفقیت در {collection_name} ذخیره شد.")

                # ✅ ثبت تاریخ همگام‌سازی موفق در MongoDB
                article.last_synced_at = datetime.utcnow()
                await article.save()
                logger.info(f"✅ تاریخ همگام‌سازی برای مقاله '{article.title}' در MongoDB ثبت شد.")

        except Exception as e:
            logger.error(f"❌ خطا در همگام‌سازی با Weaviate: {str(e)}")
            # برای جلوگیری از شکست کل عملیات، خطا را raise نکنید
            # اما خطا را log کنیم تا قابل پیگیری باشد







    def _node_to_properties(self, node: Any, article: KnowledgeBaseArticle) -> Dict[str, Any]:
        """
        تبدیل گره به properties برای Weaviate

        Args:
            node: گره از markdown parser
            article: مقاله والد

        Returns:
            دیکشنری properties
        """
        return {
            "node_id": node.id,
            "article_id": str(article.id),
            "title": node.title,
            "level": node.level,
            "content": node.content,
            "parent_id": node.parent_id,
            "path": node.path,
            "order": node.order,
            "full_content": article.content_markdown
        }

    # =============== STATISTICS ===============

    async def get_statistics(self) -> Dict[str, Any]:
        """آمار کلی پایگاه دانش"""
        try:
            total_articles = await KnowledgeBaseArticle.find_all().count()
            published_articles = await KnowledgeBaseArticle.find(
                KnowledgeBaseArticle.status == ArticleStatus.PUBLISHED
            ).count()
            draft_articles = await KnowledgeBaseArticle.find(
                KnowledgeBaseArticle.status == ArticleStatus.DRAFT
            ).count()

            total_categories = await Category.find_all().count()
            total_tags = await Tag.find_all().count()

            return {
                "total_articles": total_articles,
                "published_articles": published_articles,
                "draft_articles": draft_articles,
                "total_categories": total_categories,
                "total_tags": total_tags,
                "last_updated": datetime.utcnow()
            }

        except Exception as e:
            logger.error(f"❌ خطا در دریافت آمار: {str(e)}")
            return {}


    # =============== MARKDOWN STRUCTURE EXTRACTION ===============

    async def extract_markdown_structure(self, article_id: str) -> Dict[str, Any]:
        """
        استخراج ساختار درختی از محتوای Markdown برای پیمایش

        Args:
            article_id: شناسه مقاله

        Returns:
            ساختار درختی شامل هدرها و لینک‌ها
        """
        try:
            article = await KnowledgeBaseArticle.get(article_id)
            if not article or not article.content_markdown:
                return {"error": "Article not found or no markdown content"}

            import re

            # استخراج هدرها (از # تا ######)
            headers = []
            lines = article.content_markdown.split('\n')

            for i, line in enumerate(lines):
                # پیدا کردن هدرها
                header_match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
                if header_match:
                    level = len(header_match.group(1))  # تعداد # ها
                    title = header_match.group(2).strip()

                    # ایجاد anchor (برای لینک دادن)
                    anchor = re.sub(r'[^\w\s-]', '', title.lower())  # حذف کاراکترهای خاص
                    anchor = re.sub(r'[\s_-]+', '-', anchor).strip('-')  # تبدیل به kebab-case

                    headers.append({
                        "level": level,
                        "title": title,
                        "anchor": anchor,
                        "line_number": i + 1
                    })

            return {
                "article_id": str(article.id),
                "article_title": article.title,
                "headers": headers,
                "total_headers": len(headers)
            }

        except Exception as e:
            logger.error(f"❌ خطا در استخراج ساختار Markdown: {str(e)}")
            return {"error": str(e)}

    async def get_articles_with_structure(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        دریافت لیست مقالات با ساختار درختی آن‌ها

        Args:
            limit: حداکثر تعداد مقالات

        Returns:
            لیست مقالات با ساختار درختی
        """
        try:
            articles = await self.get_articles(limit=limit)

            result = []
            for article in articles:
                structure = await self.extract_markdown_structure(str(article.id))
                if "error" not in structure:
                    result.append({
                        "article": {
                            "id": str(article.id),
                            "title": article.title,
                            "summary": article.summary,
                            "category": article.category.name if article.category else "عمومی"
                        },
                        "structure": structure
                    })

            return result

        except Exception as e:
            logger.error(f"❌ خطا در دریافت مقالات با ساختار: {str(e)}")
            return []


# Singleton instance
knowledge_base_repository = KnowledgeBaseRepository()
