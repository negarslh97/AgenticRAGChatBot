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

logger = logging.getLogger(__name__)


class KnowledgeBaseRepository:
    """Repository برای مدیریت عملیات پایگاه دانش در MongoDB و Weaviate"""

    def __init__(self):
        self.weaviate_client = None
        self._weaviate_initialized = False

    async def _ensure_weaviate_client(self):
        """Initialize Weaviate client if not already done"""
        if self._weaviate_initialized:
            return

        try:
            import weaviate
            from app.infrastructure.database.weaviate import WeaviateMongoDBConnector

            connector = WeaviateMongoDBConnector()
            await connector.connect_mongodb()
            connector.connect_weaviate()

            if connector.weaviate_client:
                self.weaviate_client = connector.weaviate_client
                self._weaviate_initialized = True
                logger.info("✅ Weaviate client initialized for repository")
            else:
                logger.warning("⚠️ Could not initialize Weaviate client")

        except Exception as e:
            logger.error(f"❌ Error initializing Weaviate client: {str(e)}")

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

            # همگام‌سازی با Weaviate اگر مقاله منتشر شده باشد
            if status == ArticleStatus.PUBLISHED and visibility:
                await self._sync_to_weaviate(new_article, "create")

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

            # همگام‌سازی با Weaviate
            await self._sync_to_weaviate(article, "update")

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

            # حذف از Weaviate
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
        """جستجو در Weaviate"""
        try:
            await self._ensure_weaviate_client()
            if not self.weaviate_client:
                return []

            # جستجو در کلاس KnowledgeBaseArticle
            where_filter = {
                "operator": "And",
                "operands": [
                    {"path": ["status"], "operator": "Equal", "valueString": "published"}
                ]
            }

            # اضافه کردن فیلتر visibility
            if visibility_filter:
                visibility_values = [v.value for v in visibility_filter]
                where_filter["operands"].append({
                    "path": ["visibility"],
                    "operator": "In",
                    "valueString": visibility_values
                })

            # اضافه کردن فیلتر category
            if category_id:
                where_filter["operands"].append({
                    "path": ["category_id"],
                    "operator": "Equal",
                    "valueString": category_id
                })

            result = (
                self.weaviate_client.query
                .get("KnowledgeBaseArticle", ["title", "content", "summary", "article_id", "category", "tags"])
                .with_where(where_filter)
                .with_near_text({"concepts": [query]})
                .with_limit(limit)
                .with_additional(["certainty"])
                .do()
            )

            # پردازش نتایج
            articles = result.get("data", {}).get("Get", {}).get("KnowledgeBaseArticle", [])
            processed_results = []

            for article in articles:
                certainty = article.get("_additional", {}).get("certainty", 0)
                processed_results.append({
                    "id": article.get("article_id"),
                    "title": article.get("title", ""),
                    "summary": article.get("summary", ""),
                    "score": certainty,
                    "source": "weaviate"
                })

            return processed_results

        except Exception as e:
            logger.error(f"❌ خطا در جستجوی Weaviate: {str(e)}")
            return []

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

    async def _sync_to_weaviate(
        self,
        article: KnowledgeBaseArticle,
        operation: str
    ) -> None:
        """
        همگام‌سازی مقاله با Weaviate

        Args:
            article: مقاله برای همگام‌سازی
            operation: نوع عملیات (create/update/delete)
        """
        try:
            await self._ensure_weaviate_client()
            if not self.weaviate_client:
                return

            if operation == "delete":
                # حذف از Weaviate
                self.weaviate_client.data_object.delete(
                    class_name="KnowledgeBaseArticle",
                    where={
                        "operator": "Equal",
                        "path": ["article_id"],
                        "valueString": str(article.id)
                    }
                )
                logger.info(f"🗑️ مقاله '{article.title}' از Weaviate حذف شد")

            elif operation in ["create", "update"]:
                # آماده‌سازی داده‌ها برای Weaviate
                tags_list = [tag.name for tag in article.tags] if article.tags else []

                # Format dates properly for Weaviate (RFC3339)
                def format_datetime(dt):
                    if not dt:
                        return None
                    # Ensure it's a datetime object and make it timezone aware if not
                    if dt.tzinfo is None:
                        from datetime import timezone
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt.isoformat().replace('+00:00', 'Z')

                article_data = {
                    "title": article.title,
                    "content": article.content_markdown or article.content_html or "",  # ✅ اولویت به Markdown
                    "summary": article.summary or "",
                    "tags": tags_list,
                    "category": article.category.name if article.category else "عمومی",
                    "visibility": article.visibility.value if article.visibility else "",
                    "status": article.status.value,
                    "created_at": format_datetime(article.created_at),
                    "updated_at": format_datetime(article.updated_at),
                    "article_id": str(article.id)
                }

                # استفاده از vectorizer config - ابتدا OpenAI، سپس fallback محلی
                try:
                    # ابتدا سعی می‌کنیم با OpenAI vectorizer
                    self.weaviate_client.data_object.create(
                        data_object=article_data,
                        class_name="KnowledgeBaseArticle"
                    )
                    logger.info(f"🔄 مقاله '{article.title}' با OpenAI vectorizer همگام‌سازی شد")
                except Exception as e:
                    logger.warning(f"⚠️ OpenAI vectorizer شکست خورد، استفاده از fallback محلی: {str(e)}")
                    try:
                        # استفاده از fallback محلی
                        self.weaviate_client.data_object.create(
                            data_object=article_data,
                            class_name="KnowledgeBaseArticleLocal"
                        )
                        logger.info(f"🔄 مقاله '{article.title}' با local vectorizer همگام‌سازی شد")
                    except Exception as local_e:
                        logger.error(f"❌ هر دو vectorizer شکست خوردند: OpenAI={str(e)}, Local={str(local_e)}")
                        raise local_e

        except Exception as e:
            logger.error(f"❌ خطا در همگام‌سازی با Weaviate: {str(e)}")
            # ادامه عملیات بدون شکست خوردن کل فرآیند

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
