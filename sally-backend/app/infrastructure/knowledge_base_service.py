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
        # Check if tag exists
        tag = await Tag.find_one(Tag.name == tag_name)
        if not tag:
            # Create new tag
            tag = Tag(name=tag_name)
            await tag.insert()
            logger.info(f"✨ Created new tag: {tag_name}")
        article_tags.append(ArticleTag(id=str(tag.id), name=tag.name, color=tag.color))
    return article_tags


# Singleton instance
knowledge_base_service = KnowledgeBaseService()
