"""
Knowledge Base Service - لایه بیزینس لاژیک برای پایگاه دانش

این فایل عملیات بیزینس پیشرفته برای KnowledgeBaseArticle را مدیریت می‌کند
و بین API layer و Repository layer قرار می‌گیرد.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import logging
import markdown
import re

from app.domain.entities import (
    KnowledgeBaseArticle, ArticleStatus, ArticleVisibility,
    Category, Tag, Admin, Customer, Role
)
from app.infrastructure.knowledge_base_repository import knowledge_base_repository
from app.core.config import settings
from app.core.permissions import Permission

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """سرویس بیزینس لاژیک برای پایگاه دانش"""

    def __init__(self):
        self.repository = knowledge_base_repository

    # =============== ACCESS CONTROL METHODS ===============

    async def check_admin_permission(self, admin: Admin, permission: str) -> bool:
        """
        بررسی دسترسی ادمین

        Args:
            admin: ادمین مورد بررسی
            permission: دسترسی مورد نیاز

        Returns:
            True اگر دسترسی وجود دارد
        """
        try:
            role = await admin.get_role()
            if not role or not role.is_active:
                return False

            permission_keys = {perm.permission_key for perm in role.permissions}
            return permission in permission_keys

        except Exception as e:
            logger.error(f"❌ خطا در بررسی دسترسی ادمین: {str(e)}")
            return False

    async def can_create_article(self, admin: Admin) -> bool:
        """بررسی دسترسی ایجاد مقاله"""
        return await self.check_admin_permission(admin, Permission.CREATE_KB_ARTICLES)

    async def can_update_article(self, admin: Admin) -> bool:
        """بررسی دسترسی بروزرسانی مقاله"""
        return await self.check_admin_permission(admin, Permission.UPDATE_KB_ARTICLES)

    async def can_publish_article(self, admin: Admin) -> bool:
        """بررسی دسترسی انتشار مقاله"""
        return await self.check_admin_permission(admin, Permission.PUBLISH_ARTICLES)

    async def can_delete_article(self, admin: Admin) -> bool:
        """بررسی دسترسی حذف مقاله"""
        return await self.check_admin_permission(admin, Permission.DELETE_ARTICLES)

    async def can_manage_articles(self, admin: Admin) -> bool:
        """بررسی دسترسی مدیریت کامل مقالات"""
        return await self.check_admin_permission(admin, Permission.MANAGE_KB_ARTICLES)

    async def can_view_private_articles(self, admin: Admin) -> bool:
        """بررسی دسترسی مشاهده مقالات خصوصی"""
        return await self.check_admin_permission(admin, Permission.MANAGE_KB_ARTICLES)

    def get_visibility_levels_for_user(self, user: Optional[Admin] = None, customer: Optional[Customer] = None) -> List[ArticleVisibility]:
        """
        تعیین سطوح دسترسی قابل مشاهده برای کاربر

        Args:
            user: ادمین (اختیاری)
            customer: مشتری (اختیاری)

        Returns:
            لیست سطوح دسترسی قابل مشاهده
        """
        if user:
            # ادمین می‌تواند همه مقالات را ببیند
            return [ArticleVisibility.PUBLIC, ArticleVisibility.CUSTOMER, ArticleVisibility.INTERNAL]
        elif customer:
            # مشتری می‌تواند مقالات عمومی و مشتری را ببیند
            return [ArticleVisibility.PUBLIC, ArticleVisibility.CUSTOMER]
        else:
            # کاربر مهمان فقط مقالات عمومی را می‌بیند
            return [ArticleVisibility.PUBLIC]

    # =============== ARTICLE CREATION ===============

    async def create_article_from_text(
        self,
        title: str,
        content: str,
        author: Admin,
        category_id: Optional[str] = None,
        tag_names: Optional[List[str]] = None,
        is_markdown: bool = True,
        generate_summary: bool = True,
        auto_publish: bool = False
    ) -> KnowledgeBaseArticle:
        """
        ایجاد مقاله از متن با بررسی دسترسی

        Args:
            title: عنوان مقاله
            content: محتوای مقاله
            author: نویسنده مقاله (باید دسترسی ایجاد داشته باشد)
            category_id: دسته‌بندی
            tag_names: تگ‌ها
            is_markdown: آیا محتوا markdown است
            generate_summary: تولید خلاصه
            auto_publish: انتشار خودکار

        Returns:
            مقاله ایجاد شده

        Raises:
            PermissionError: اگر دسترسی کافی وجود نداشته باشد
        """
        # بررسی دسترسی ایجاد مقاله
        if not await self.can_create_article(author):
            raise PermissionError("شما دسترسی ایجاد مقاله ندارید")

        # اگر auto_publish فعال باشد، بررسی دسترسی انتشار
        if auto_publish and not await self.can_publish_article(author):
            raise PermissionError("شما دسترسی انتشار مقاله ندارید")
        try:
            # تبدیل محتوا به HTML اگر markdown است
            content_html = content
            content_markdown = content

            if is_markdown:
                content_html = markdown.markdown(content, extensions=['extra', 'codehilite'])
            else:
                # اگر HTML است، markdown را از آن استخراج کنیم
                content_markdown = self._html_to_markdown(content)

            # تولید خلاصه اگر درخواست شده
            summary = None
            if generate_summary:
                summary = await self._generate_summary(title, content_html)

            # تعیین وضعیت اولیه
            status = ArticleStatus.PUBLISHED if auto_publish else ArticleStatus.DRAFT
            visibility = ArticleVisibility.PUBLIC if auto_publish else None

            # ایجاد مقاله
            article = await self.repository.create_article(
                title=title,
                content_markdown=content_markdown,
                content_html=content_html,
                author_id=str(author.id),
                category_id=category_id,
                tag_names=tag_names,
                summary=summary,
                status=status,
                visibility=visibility
            )

            logger.info(f"📝 مقاله '{title}' توسط {author.full_name} ایجاد شد")
            return article

        except Exception as e:
            logger.error(f"❌ خطا در ایجاد مقاله: {str(e)}")
            raise

    async def create_article_from_file(
        self,
        file_path: str,
        file_name: str,
        author: Admin,
        category_id: Optional[str] = None,
        tag_names: Optional[List[str]] = None
    ) -> KnowledgeBaseArticle:
        """
        ایجاد مقاله از فایل آپلود شده

        Args:
            file_path: مسیر فایل
            file_name: نام فایل
            author: نویسنده
            category_id: دسته‌بندی
            tag_names: تگ‌ها

        Returns:
            مقاله ایجاد شده
        """
        try:
            # استخراج متن از فایل
            extracted_text = await self._extract_text_from_file(file_path, file_name)

            # تولید عنوان از نام فایل اگر عنوان مناسبی پیدا نشد
            title = self._generate_title_from_filename(file_name)

            # تولید خلاصه
            summary = await self._generate_summary(title, extracted_text)

            # ایجاد مقاله
            article = await self.repository.create_article(
                title=title,
                content_markdown=extracted_text,
                content_html=markdown.markdown(extracted_text, extensions=['extra']),
                author_id=str(author.id),
                category_id=category_id,
                tag_names=tag_names,
                summary=summary,
                status=ArticleStatus.DRAFT
            )

            logger.info(f"📄 مقاله از فایل '{file_name}' ایجاد شد")
            return article

        except Exception as e:
            logger.error(f"❌ خطا در ایجاد مقاله از فایل: {str(e)}")
            raise

    # =============== ARTICLE MANAGEMENT ===============

    async def update_article_content(
        self,
        article_id: str,
        updater: Admin,
        title: Optional[str] = None,
        content: Optional[str] = None,
        is_markdown: bool = True,
        regenerate_summary: bool = False
    ) -> Optional[KnowledgeBaseArticle]:
        """
        بروزرسانی محتوای مقاله با بررسی دسترسی

        Args:
            article_id: شناسه مقاله
            title: عنوان جدید
            content: محتوای جدید
            is_markdown: آیا محتوا markdown است
            updater: بروزرسان‌کننده (باید دسترسی بروزرسانی داشته باشد)
            regenerate_summary: آیا خلاصه دوباره تولید شود

        Returns:
            مقاله بروزرسانی شده

        Raises:
            PermissionError: اگر دسترسی کافی وجود نداشته باشد
        """
        # بررسی دسترسی بروزرسانی
        if not await self.can_update_article(updater):
            raise PermissionError("شما دسترسی بروزرسانی مقاله ندارید")
        try:
            updates = {}

            if title:
                updates["title"] = title

            if content:
                if is_markdown:
                    updates["content_markdown"] = content
                    updates["content_html"] = markdown.markdown(content, extensions=['extra', 'codehilite'])
                else:
                    updates["content_html"] = content
                    updates["content_markdown"] = self._html_to_markdown(content)

            if regenerate_summary and content:
                content_for_summary = updates.get("content_html", content)
                updates["summary"] = await self._generate_summary(
                    title or "Article",
                    content_for_summary
                )

            return await self.repository.update_article(
                article_id=article_id,
                updates=updates,
                updated_by=str(updater.id)
            )

        except Exception as e:
            logger.error(f"❌ خطا در بروزرسانی مقاله: {str(e)}")
            return None

    async def publish_article(
        self,
        article_id: str,
        visibility: ArticleVisibility,
        publisher: Admin
    ) -> Optional[KnowledgeBaseArticle]:
        """
        انتشار مقاله با بررسی دسترسی

        Args:
            article_id: شناسه مقاله
            visibility: سطح دسترسی
            publisher: ناشر (باید دسترسی انتشار داشته باشد)

        Returns:
            مقاله منتشر شده

        Raises:
            PermissionError: اگر دسترسی کافی وجود نداشته باشد
        """
        # بررسی دسترسی انتشار
        if not await self.can_publish_article(publisher):
            raise PermissionError("شما دسترسی انتشار مقاله ندارید")
        try:
            # دریافت مقاله
            article = await self.repository.get_article_by_id(article_id)
            if not article:
                raise ValueError("مقاله یافت نشد")

            # اعتبارسنجی
            if not article.title or not article.content_html:
                raise ValueError("مقاله باید دارای عنوان و محتوا باشد")

            if not article.summary:
                # تولید خلاصه اگر وجود ندارد
                summary = await self._generate_summary(article.title, article.content_html)
                await self.repository.update_article(
                    article_id,
                    {"summary": summary},
                    str(publisher.id),
                    new_version=False
                )

            # انتشار مقاله
            return await self.repository.publish_article(article_id, visibility, publisher)

        except Exception as e:
            logger.error(f"❌ خطا در انتشار مقاله: {str(e)}")
            raise

    # =============== SEARCH & RETRIEVAL ===============

    async def search_articles(
        self,
        query: str,
        user: Optional[Admin] = None,
        customer: Optional[Customer] = None,
        category_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        جستجوی پیشرفته با احراز هویت

        Args:
            query: عبارت جستجو
            user: کاربر ادمین (اختیاری)
            customer: مشتری (اختیاری)
            category_id: فیلتر دسته‌بندی
            limit: حداکثر نتایج

        Returns:
            نتایج جستجو
        """
        try:
            # تعیین سطح دسترسی بر اساس نقش کاربر
            visibility_filter = self.get_visibility_levels_for_user(user, customer)

            return await self.repository.search_articles(
                query=query,
                visibility_filter=visibility_filter,
                category_id=category_id,
                limit=limit
            )

        except Exception as e:
            logger.error(f"❌ خطا در جستجو: {str(e)}")
            return []

    # =============== BULK OPERATIONS ===============

    async def bulk_update_status(
        self,
        article_ids: List[str],
        new_status: ArticleStatus,
        updater: Admin,
        visibility: Optional[ArticleVisibility] = None
    ) -> Dict[str, Any]:
        """
        بروزرسانی وضعیت چندین مقاله به طور همزمان

        Args:
            article_ids: لیست شناسه مقالات
            new_status: وضعیت جدید
            updater: بروزرسان‌کننده
            visibility: سطح دسترسی جدید (برای انتشار)

        Returns:
            نتیجه عملیات
        """
        try:
            successful = []
            failed = []

            for article_id in article_ids:
                try:
                    updates = {"status": new_status}
                    if new_status == ArticleStatus.PUBLISHED and visibility:
                        updates["visibility"] = visibility
                        updates["published_at"] = datetime.utcnow()
                        updates["publisher_id"] = str(updater.id)

                    article = await self.repository.update_article(
                        article_id, updates, str(updater.id)
                    )

                    if article:
                        successful.append(article_id)
                    else:
                        failed.append(article_id)

                except Exception as e:
                    logger.error(f"❌ خطا در بروزرسانی مقاله {article_id}: {str(e)}")
                    failed.append(article_id)

            return {
                "successful": successful,
                "failed": failed,
                "total": len(article_ids),
                "success_count": len(successful),
                "failure_count": len(failed)
            }

        except Exception as e:
            logger.error(f"❌ خطا در عملیات bulk: {str(e)}")
            raise

    async def delete_article(
        self,
        article_id: str,
        deleter: Admin
    ) -> bool:
        """
        حذف مقاله با بررسی دسترسی

        Args:
            article_id: شناسه مقاله
            deleter: حذف‌کننده (باید دسترسی حذف داشته باشد)

        Returns:
            True اگر حذف موفق بود

        Raises:
            PermissionError: اگر دسترسی کافی وجود نداشته باشد
        """
        # بررسی دسترسی حذف
        if not await self.can_delete_article(deleter):
            raise PermissionError("شما دسترسی حذف مقاله ندارید")

        return await self.repository.delete_article(article_id)

    # =============== ANALYTICS & REPORTING ===============

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """
        آمار داشبورد مدیریت

        Returns:
            آمار کلی سیستم
        """
        try:
            # آمار پایه
            stats = await self.repository.get_statistics()

            # آمار اضافی
            recent_articles = await self.repository.get_articles(
                limit=5,
                status=ArticleStatus.PUBLISHED
            )

            # تبدیل به dict برای JSON serialization
            recent_articles_data = []
            for article in recent_articles:
                recent_articles_data.append({
                    "id": str(article.id),
                    "title": article.title,
                    "created_at": article.created_at.isoformat() if article.created_at else None,
                    "author_id": article.author_id
                })

            stats["recent_articles"] = recent_articles_data
            stats["generated_at"] = datetime.utcnow().isoformat()

            return stats

        except Exception as e:
            logger.error(f"❌ خطا در دریافت آمار داشبورد: {str(e)}")
            return {}

    async def get_category_stats(self) -> Dict[str, Any]:
        """
        آمار پیشرفته دسته‌بندی‌ها

        Returns:
            آمار تفصیلی دسته‌بندی‌ها
        """
        try:
            # آمار دسته‌بندی‌ها
            all_categories = await Category.find_all().to_list()
            public_categories = [c for c in all_categories if c.is_public]
            private_categories = [c for c in all_categories if not c.is_public]

            # آمار مقالات در هر دسته‌بندی
            category_stats = []
            for category in all_categories:
                article_count = await KnowledgeBaseArticle.find(
                    {"category.id": str(category.id)}
                ).count()

                category_stats.append({
                    "id": str(category.id),
                    "name": category.name,
                    "slug": category.slug,
                    "is_public": category.is_public,
                    "article_count": article_count,
                    "has_children": await Category.find({"parent.$id": category.id}).count() > 0
                })

            # آمار تگ‌ها
            total_tags = await Tag.find_all().count()
            system_tags = await Tag.find(Tag.is_system == True).count()
            popular_tags = await get_popular_tags(10)

            return {
                "categories": {
                    "total": len(all_categories),
                    "public": len(public_categories),
                    "private": len(private_categories),
                    "with_articles": len([c for c in category_stats if c["article_count"] > 0]),
                    "details": category_stats
                },
                "tags": {
                    "total": total_tags,
                    "system": system_tags,
                    "user_created": total_tags - system_tags,
                    "popular": [
                        {
                            "name": tag.name,
                            "usage_count": tag.usage_count,
                            "color": tag.color
                        } for tag in popular_tags
                    ]
                },
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ خطا در دریافت آمار دسته‌بندی‌ها: {str(e)}")
            return {}

    # =============== HELPER METHODS ===============

    async def _generate_summary(self, title: str, content: str, max_length: int = 200) -> str:
        """
        تولید خلاصه هوشمند از محتوا

        Args:
            title: عنوان مقاله
            content: محتوای مقاله
            max_length: حداکثر طول خلاصه

        Returns:
            خلاصه تولید شده
        """
        try:
            # حذف HTML tags
            clean_content = re.sub(r'<[^>]+>', '', content)

            # استخراج پاراگراف اول یا چند جمله اول
            sentences = re.split(r'[.!?]+', clean_content.strip())

            # فیلتر کردن جملات خالی
            sentences = [s.strip() for s in sentences if s.strip()]

            if not sentences:
                return f"خلاصه مقاله: {title}"

            # انتخاب جملات اولیه
            summary_sentences = []
            current_length = 0

            for sentence in sentences[:3]:  # حداکثر ۳ جمله اول
                if current_length + len(sentence) <= max_length:
                    summary_sentences.append(sentence)
                    current_length += len(sentence)
                else:
                    break

            summary = '. '.join(summary_sentences)
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."

            return summary

        except Exception as e:
            logger.error(f"❌ خطا در تولید خلاصه: {str(e)}")
            return f"خلاصه مقاله: {title}"

    async def _extract_text_from_file(self, file_path: str, file_name: str) -> str:
        """
        استخراج متن از فایل‌های مختلف

        Args:
            file_path: مسیر فایل
            file_name: نام فایل

        Returns:
            متن استخراج شده
        """
        try:
            file_extension = file_name.lower().split('.')[-1]

            if file_extension == 'txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            elif file_extension == 'md':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            elif file_extension == 'pdf':
                # استفاده از PyPDF2 اگر موجود باشد
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(file_path)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text.strip()
                except ImportError:
                    return "محتوای PDF قابل استخراج نیست (PyPDF2 نصب نیست)"
            else:
                return f"فایل {file_extension} پشتیبانی نمی‌شود"

        except Exception as e:
            logger.error(f"❌ خطا در استخراج متن از فایل: {str(e)}")
            return f"خطا در پردازش فایل: {str(e)}"

    def _generate_title_from_filename(self, filename: str) -> str:
        """تولید عنوان از نام فایل"""
        # حذف پسوند فایل
        name_without_ext = filename.rsplit('.', 1)[0]

        # تبدیل underscores و dashes به spaces
        title = name_without_ext.replace('_', ' ').replace('-', ' ')

        # Capitalize هر کلمه
        title = ' '.join(word.capitalize() for word in title.split())

        return title

    def _html_to_markdown(self, html_content: str) -> str:
        """
        تبدیل HTML به Markdown (ساده)

        Args:
            html_content: محتوای HTML

        Returns:
            محتوای Markdown
        """
        try:
            import html2text
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = False
            return h.handle(html_content)
        except ImportError:
            # Fallback ساده
            # حذف tags HTML و تبدیل برخی عناصر پایه
            text = re.sub(r'<br\s*/?>', '\n', html_content)
            text = re.sub(r'</p>', '\n\n', text)
            text = re.sub(r'<[^>]+>', '', text)
            return text.strip()

    # =============== CATEGORY MANAGEMENT METHODS ===============

    async def create_category(
        self,
        name: str,
        slug: str,
        description: Optional[str] = None,
        parent_id: Optional[str] = None,
        is_public: bool = True
    ) -> Category:
        """
        ایجاد دسته‌بندی جدید
        
        Args:
            name: نام دسته‌بندی
            slug: شناسه URL-friendly (باید یکتا باشد)
            description: توضیحات دسته‌بندی
            parent_id: شناسه دسته‌بندی والد (اختیاری)
            is_public: آیا عمومی است؟
            
        Returns:
            دسته‌بندی ایجاد شده
        """
        try:
            # بررسی یکتا بودن slug
            existing = await Category.find_one(Category.slug == slug)
            if existing:
                raise ValueError(f"دسته‌بندی با slug '{slug}' قبلاً وجود دارد")
            
            # ایجاد دسته‌بندی جدید
            category = Category(
                name=name,
                slug=slug,
                description=description,
                is_public=is_public
            )
            
            # تنظیم parent اگر وجود داشته باشد
            if parent_id:
                parent = await Category.get(parent_id)
                if parent:
                    category.parent = parent
                else:
                    raise ValueError(f"دسته‌بندی والد با ID '{parent_id}' یافت نشد")
            
            await category.insert()
            await category.update_ancestors()
            await category.save()
            
            logger.info(f"✅ دسته‌بندی '{name}' ایجاد شد - ID: {category.id}")
            return category
            
        except Exception as e:
            logger.error(f"❌ خطا در ایجاد دسته‌بندی: {str(e)}")
            raise

    async def get_category_by_id(self, category_id: str) -> Optional[Category]:
        """دریافت دسته‌بندی با ID"""
        try:
            return await Category.get(category_id)
        except Exception as e:
            logger.error(f"❌ خطا در دریافت دسته‌بندی: {str(e)}")
            return None

    async def get_category_by_slug(self, slug: str) -> Optional[Category]:
        """دریافت دسته‌بندی با slug"""
        try:
            return await Category.find_one(Category.slug == slug)
        except Exception as e:
            logger.error(f"❌ خطا در دریافت دسته‌بندی: {str(e)}")
            return None

    async def get_all_categories(
        self,
        is_public_only: bool = False,
        parent_id: Optional[str] = None
    ) -> List[Category]:
        """
        دریافت همه دسته‌بندی‌ها
        
        Args:
            is_public_only: فقط دسته‌بندی‌های عمومی
            parent_id: فیلتر بر اساس والد (None = root categories)
            
        Returns:
            لیست دسته‌بندی‌ها
        """
        try:
            query = {}
            
            if is_public_only:
                query["is_public"] = True
            
            if parent_id:
                parent = await Category.get(parent_id)
                query["parent.$id"] = parent.id
            elif parent_id is None:
                # فقط root categories (بدون والد)
                query["parent"] = None
            
            categories = await Category.find(query).to_list()
            return categories
            
        except Exception as e:
            logger.error(f"❌ خطا در دریافت دسته‌بندی‌ها: {str(e)}")
            return []

    async def update_category(
        self,
        category_id: str,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        parent_id: Optional[str] = None,
        is_public: Optional[bool] = None,
        update_articles: bool = True
    ) -> Category:
        """
        به‌روزرسانی دسته‌بندی
        
        Args:
            category_id: شناسه دسته‌بندی
            name: نام جدید (اختیاری)
            slug: slug جدید (اختیاری)
            description: توضیحات جدید (اختیاری)
            parent_id: والد جدید (اختیاری)
            is_public: وضعیت عمومی بودن
            update_articles: آیا مقالات هم به‌روز شوند؟
            
        Returns:
            دسته‌بندی به‌روز شده
        """
        try:
            category = await Category.get(category_id)
            if not category:
                raise ValueError(f"دسته‌بندی با ID '{category_id}' یافت نشد")
            
            old_name = category.name
            old_slug = category.slug
            
            # به‌روزرسانی فیلدها
            if name is not None:
                category.name = name
            
            if slug is not None and slug != old_slug:
                # بررسی یکتا بودن slug جدید
                existing = await Category.find_one(Category.slug == slug)
                if existing and str(existing.id) != category_id:
                    raise ValueError(f"دسته‌بندی با slug '{slug}' قبلاً وجود دارد")
                category.slug = slug
            
            if description is not None:
                category.description = description
            
            if is_public is not None:
                category.is_public = is_public
            
            if parent_id is not None:
                if parent_id == "":  # حذف والد
                    category.parent = None
                else:
                    parent = await Category.get(parent_id)
                    if not parent:
                        raise ValueError(f"دسته‌بندی والد با ID '{parent_id}' یافت نشد")
                    
                    # جلوگیری از circular reference
                    if str(parent.id) == category_id:
                        raise ValueError("دسته‌بندی نمی‌تواند والد خودش باشد")
                    
                    category.parent = parent
            
            await category.update_ancestors()
            await category.save()
            
            logger.info(f"✅ دسته‌بندی '{old_name}' به‌روز شد")
            
            # به‌روزرسانی مقالات مرتبط اگر نام یا slug تغییر کرده باشد
            if update_articles and (name != old_name or slug != old_slug):
                await self._update_articles_category(category_id, category.name, category.slug)
            
            return category
            
        except Exception as e:
            logger.error(f"❌ خطا در به‌روزرسانی دسته‌بندی: {str(e)}")
            raise

    async def _update_articles_category(self, category_id: str, new_name: str, new_slug: str):
        """به‌روزرسانی اطلاعات دسته‌بندی در تمام مقالات مرتبط"""
        try:
            from app.domain.entities import ArticleCategory
            
            # پیدا کردن تمام مقالاتی که این دسته‌بندی را دارند
            articles = await KnowledgeBaseArticle.find(
                {"category.id": category_id}
            ).to_list()
            
            updated_count = 0
            for article in articles:
                if article.category:
                    article.category = ArticleCategory(
                        id=category_id,
                        name=new_name,
                        slug=new_slug
                    )
                    await article.save()
                    updated_count += 1
            
            logger.info(f"✅ {updated_count} مقاله با اطلاعات دسته‌بندی جدید به‌روز شدند")
            
        except Exception as e:
            logger.error(f"❌ خطا در به‌روزرسانی مقالات: {str(e)}")

    async def delete_category(
        self,
        category_id: str,
        cascade: bool = False,
        move_to_parent: bool = True
    ) -> Dict[str, Any]:
        """
        حذف دسته‌بندی
        
        Args:
            category_id: شناسه دسته‌بندی
            cascade: اگر True باشد، زیردسته‌ها و مقالات هم حذف می‌شوند
            move_to_parent: اگر True باشد، زیردسته‌ها به والد منتقل می‌شوند
            
        Returns:
            اطلاعات عملیات حذف
        """
        try:
            category = await Category.get(category_id)
            if not category:
                raise ValueError(f"دسته‌بندی با ID '{category_id}' یافت نشد")
            
            # بررسی زیردسته‌ها
            children = await Category.find({"parent.$id": category.id}).to_list()
            
            # بررسی مقالات مرتبط
            articles = await KnowledgeBaseArticle.find(
                {"category.id": category_id}
            ).to_list()
            
            result = {
                "category_name": category.name,
                "children_count": len(children),
                "articles_count": len(articles),
                "deleted_categories": [category_id],
                "affected_articles": [],
                "moved_children": []
            }
            
            # مدیریت زیردسته‌ها
            if children:
                if cascade:
                    # حذف تمام زیردسته‌ها به صورت بازگشتی
                    for child in children:
                        child_result = await self.delete_category(
                            str(child.id),
                            cascade=True,
                            move_to_parent=False
                        )
                        result["deleted_categories"].extend(child_result["deleted_categories"])
                        result["affected_articles"].extend(child_result["affected_articles"])
                        
                elif move_to_parent:
                    # انتقال زیردسته‌ها به والد این دسته‌بندی
                    for child in children:
                        child.parent = category.parent
                        await child.update_ancestors()
                        await child.save()
                        result["moved_children"].append(str(child.id))
                        logger.info(f"📦 زیردسته '{child.name}' به والد منتقل شد")
                else:
                    raise ValueError(
                        f"این دسته‌بندی {len(children)} زیردسته دارد. "
                        "برای حذف باید cascade=True یا move_to_parent=True باشد"
                    )
            
            # مدیریت مقالات
            if articles:
                if cascade:
                    # حذف تمام مقالات
                    for article in articles:
                        await article.delete()
                        result["affected_articles"].append({
                            "id": str(article.id),
                            "title": article.title,
                            "action": "deleted"
                        })
                    logger.info(f"🗑️ {len(articles)} مقاله حذف شدند")
                else:
                    # حذف category از مقالات
                    for article in articles:
                        article.category = None
                        await article.save()
                        result["affected_articles"].append({
                            "id": str(article.id),
                            "title": article.title,
                            "action": "category_removed"
                        })
                    logger.info(f"📝 دسته‌بندی از {len(articles)} مقاله حذف شد")
            
            # حذف دسته‌بندی
            await category.delete()
            logger.info(f"✅ دسته‌بندی '{category.name}' حذف شد")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ خطا در حذف دسته‌بندی: {str(e)}")
            raise

    async def get_category_tree(self, is_public_only: bool = False) -> List[Dict[str, Any]]:
        """
        دریافت درخت کامل دسته‌بندی‌ها
        
        Returns:
            درخت سلسله‌مراتبی دسته‌بندی‌ها
        """
        try:
            # دریافت تمام دسته‌بندی‌ها
            query = {"is_public": True} if is_public_only else {}
            all_categories = await Category.find(query).to_list()
            
            # ساخت mapping از ID به category
            categories_map = {str(cat.id): cat for cat in all_categories}
            
            # ساخت درخت
            def build_tree_node(category: Category) -> Dict[str, Any]:
                node = {
                    "id": str(category.id),
                    "name": category.name,
                    "slug": category.slug,
                    "description": category.description,
                    "is_public": category.is_public,
                    "children": []
                }
                
                # پیدا کردن فرزندان
                for cat_id, cat in categories_map.items():
                    if cat.parent and str(cat.parent.id) == str(category.id):
                        node["children"].append(build_tree_node(cat))
                
                return node
            
            # ساخت درخت از root categories
            tree = []
            for category in all_categories:
                if not category.parent:
                    tree.append(build_tree_node(category))
            
            return tree
            
        except Exception as e:
            logger.error(f"❌ خطا در ساخت درخت دسته‌بندی: {str(e)}")
            return []


# =============== HELPER FUNCTIONS (Shared across modules) ===============

async def get_or_create_tags(tag_names: List[str]) -> List[Any]:
    """
    Get or create tags and return ArticleTag objects.

    این تابع مشترک برای ایجاد یا دریافت تگ‌ها است و در چند ماژول مختلف استفاده می‌شود.

    Args:
        tag_names: لیست نام تگ‌ها

    Returns:
        لیست ArticleTag objects
    """
    from app.domain.entities import ArticleTag

    article_tags = []
    for tag_name in tag_names:
        # Normalize tag name
        normalized_name = tag_name.lower().strip()

        # Check if tag exists
        tag = await Tag.find_one(Tag.name == normalized_name)
        if not tag:
            # Create new tag
            tag = Tag(
                name=normalized_name,
                description=f"تگ: {tag_name}",
                usage_count=0,
                is_system=False
            )
            await tag.insert()
            logger.info(f"✨ Created new tag: {tag_name}")
        else:
            # Increment usage count
            await tag.increment_usage()

        article_tags.append(ArticleTag(
            id=str(tag.id),
            name=tag.name,
            color=tag.color,
            description=tag.description,
            is_system=tag.is_system
        ))
    return article_tags

# =============== TAG MANAGEMENT METHODS ===============

async def create_tag(
    name: str,
    color: Optional[str] = None,
    description: Optional[str] = None,
    is_system: bool = False
) -> Tag:
    """
    ایجاد تگ جدید

    Args:
        name: نام تگ
        color: رنگ تگ (اختیاری)
        description: توضیحات تگ
        is_system: آیا تگ سیستمی است؟

    Returns:
        تگ ایجاد شده
    """
    try:
        normalized_name = name.lower().strip()

        # بررسی وجود تگ
        existing = await Tag.find_one(Tag.name == normalized_name)
        if existing:
            raise ValueError(f"تگ '{name}' قبلاً وجود دارد")

        tag = Tag(
            name=normalized_name,
            color=color,
            description=description,
            is_system=is_system,
            usage_count=0
        )

        await tag.insert()
        logger.info(f"✅ تگ '{name}' ایجاد شد")
        return tag

    except Exception as e:
        logger.error(f"❌ خطا در ایجاد تگ: {str(e)}")
        raise

async def get_popular_tags(limit: int = 20) -> List[Tag]:
    """
    دریافت تگ‌های محبوب بر اساس تعداد استفاده

    Args:
        limit: حداکثر تعداد تگ‌ها

    Returns:
        لیست تگ‌های محبوب
    """
    try:
        tags = await Tag.find(Tag.is_system == False).sort(-Tag.usage_count).limit(limit).to_list()
        return tags
    except Exception as e:
        logger.error(f"❌ خطا در دریافت تگ‌های محبوب: {str(e)}")
        return []

async def update_tag_usage(tag_ids: List[str]) -> None:
    """
    بروزرسانی شمارنده استفاده تگ‌ها

    Args:
        tag_ids: لیست ID تگ‌ها
    """
    try:
        for tag_id in tag_ids:
            tag = await Tag.get(tag_id)
            if tag:
                await tag.increment_usage()
    except Exception as e:
        logger.error(f"❌ خطا در بروزرسانی استفاده تگ: {str(e)}")

async def cleanup_unused_tags() -> int:
    """
    پاکسازی تگ‌های استفاده نشده (غیر سیستمی)

    Returns:
        تعداد تگ‌های حذف شده
    """
    try:
        unused_tags = await Tag.find(
            Tag.usage_count == 0,
            Tag.is_system == False
        ).to_list()

        deleted_count = 0
        for tag in unused_tags:
            await tag.delete()
            deleted_count += 1

        logger.info(f"🧹 {deleted_count} تگ استفاده نشده حذف شدند")
        return deleted_count

    except Exception as e:
        logger.error(f"❌ خطا در پاکسازی تگ‌ها: {str(e)}")
        return 0


# Singleton instance
knowledge_base_service = KnowledgeBaseService()
