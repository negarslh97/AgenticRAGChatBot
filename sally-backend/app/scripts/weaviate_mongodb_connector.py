#!/usr/bin/env python3
"""
Weaviate-MongoDB Connection and Data Migration Script

این اسکریپت اتصال بین پروژه SallyBot، Weaviate vector database و MongoDB را برقرار کرده
و عملیات انتقال داده‌ها را انجام می‌دهد.

نحوه استفاده:
    python app/scripts/weaviate_mongodb_connector.py --setup
    python app/scripts/weaviate_mongodb_connector.py --migrate
    python app/scripts/weaviate_mongodb_connector.py --verify
"""

# فیلتر کردن همه warningها قبل از هر چیز دیگر
import warnings
import sys
import os

# Suppress all warnings
warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore'

import asyncio
import sys
import os
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import argparse

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('weaviate_mongodb_connector.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class WeaviateMongoDBConnector:
    """اتصال‌دهنده بین Weaviate و MongoDB"""

    def __init__(self):
        self.weaviate_client = None
        self.mongodb_client = None
        self.collection_name = "SallyChatBot"

    def connect_weaviate(self) -> bool:
        """اتصال به Weaviate"""
        try:
            logger.info("🔌 اتصال به Weaviate...")

            import weaviate

            weaviate_url = settings.weaviate_url_loaded or "http://localhost:8080"
            weaviate_api_key = settings.weaviate_api_key_loaded

            logger.info(f"📍 Weaviate URL: {weaviate_url}")
            logger.info(f"🔑 API Key تنظیم شده: {'بله' if weaviate_api_key else 'خیر'}")

            # اتصال به Weaviate - بدون authentication چون server روی anonymous access تنظیم شده
            # Suppress warnings temporarily
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.weaviate_client = weaviate.Client(url=weaviate_url)

            # تنظیم API key در محیط برای embeddings
            import os
            embedder_api_key = settings.embedder_api_key_loaded
            if embedder_api_key:
                os.environ['OPENAI_APIKEY'] = embedder_api_key
                logger.info("🔑 OPENAI_APIKEY در محیط تنظیم شد")

            # تست اتصال
            meta = self.weaviate_client.get_meta()
            logger.info(f"✅ اتصال به Weaviate موفق - نسخه: {meta.get('version', 'Unknown')}")
            return True

        except Exception as e:
            logger.error(f"❌ خطا در اتصال به Weaviate: {str(e)}")
            return False

    async def connect_mongodb(self) -> bool:
        """اتصال به MongoDB"""
        try:
            logger.info("🔌 اتصال به MongoDB...")

            from motor.motor_asyncio import AsyncIOMotorClient

            mongodb_url = settings.database_url
            logger.info(f"📍 MongoDB URL: {mongodb_url}")

            self.mongodb_client = AsyncIOMotorClient(mongodb_url)
            db = self.mongodb_client.get_default_database()

            # تست اتصال
            await self.mongodb_client.admin.command('ping')
            logger.info("✅ اتصال به MongoDB موفق")

            # نمایش آمار دیتابیس
            collections = await db.list_collection_names()
            logger.info(f"📊 کالکشن‌های موجود: {collections}")

            return True

        except Exception as e:
            logger.error(f"❌ خطا در اتصال به MongoDB: {str(e)}")
            return False

    def log_vectorizer_info(self) -> None:
        """لاگ گرفتن اطلاعات vectorizer و مدل"""
        try:
            logger.info("🔍 بررسی اطلاعات Vectorizer...")

            # دریافت اطلاعات schema
            schema = self.weaviate_client.schema.get()
            classes = schema.get("classes", [])

            for class_info in classes:
                class_name = class_info.get("class")
                vectorizer = class_info.get("vectorizer")

                if vectorizer == "text2vec-openai":
                    if class_name == "KnowledgeBaseArticle":
                        logger.info(f"🤖 کلاس '{class_name}' از vectorizer استفاده می‌کند (پایگاه دانش)")
                    elif class_name == "SupportTicket":
                        # این کلاس نباید vectorizer داشته باشد، اما اگر دارد، نمایش می‌دهیم
                        logger.info(f"⚠️ کلاس '{class_name}' هنوز vectorizer دارد (برای حذف نیاز به recreate schema)")
                    else:
                        logger.info(f"🤖 کلاس '{class_name}' از vectorizer استفاده می‌کند")

                    # دریافت تنظیمات vectorizer
                    vectorizer_config = class_info.get("vectorizerConfig", {})
                    model = vectorizer_config.get("model", "text-embedding-ada-002")  # default
                    provider = "OpenAI"

                    # بررسی ابعاد vector (از طریق بررسی یک object موجود یا استفاده از default)
                    try:
                        # تلاش برای دریافت یک object و بررسی ابعاد vector آن
                        result = self.weaviate_client.query.get(class_name).with_additional("vector").with_limit(1).do()
                        objects = result.get("data", {}).get("Get", {}).get(class_name, [])

                        if objects:
                            vector = objects[0].get("_additional", {}).get("vector", [])
                            dimensions = len(vector) if vector else 1536  # default for ada-002
                        else:
                            dimensions = 1536  # default for text-embedding-ada-002

                        logger.info(f"   📏 مدل: {model}")
                        logger.info(f"   🏢 ارائه‌دهنده: {provider}")
                        logger.info(f"   📐 ابعاد vector: {dimensions}")

                    except Exception as e:
                        logger.warning(f"   ⚠️ نتوانست اطلاعات vector را دریافت کند: {str(e)}")
                        logger.info(f"   📏 مدل: {model} (پیش‌فرض)")
                        logger.info(f"   🏢 ارائه‌دهنده: {provider}")
                        logger.info(f"   📐 ابعاد vector: 1536 (پیش‌فرض)")

                elif class_name == "KnowledgeBaseArticle":
                    logger.info(f"📚 کلاس '{class_name}' برای vectorization پایگاه دانش طراحی شده")
                else:
                    logger.info(f"📄 کلاس '{class_name}' فاقد vectorization است")

        except Exception as e:
            logger.error(f"❌ خطا در دریافت اطلاعات vectorizer: {str(e)}")

    def create_weaviate_schema(self) -> bool:
        """ایجاد schema های Weaviate"""
        try:
            logger.info("🏗️ ایجاد schema های Weaviate...")

            # تعریف کلاس KnowledgeBaseArticle
            article_class = {
                "class": "KnowledgeBaseArticle",
                "description": "مقالات پایگاه دانش برای سیستم پشتیبانی مشتری",
                "vectorizer": "text2vec-openai",
                "vectorIndexType": "hnsw",
                "vectorIndexConfig": {
                    "distance": "cosine",
                    "ef": -1,
                    "efConstruction": 128,
                    "maxConnections": 64
                },
                "properties": [
                    {
                        "name": "title",
                        "dataType": ["text"],
                        "description": "عنوان مقاله",
                        "indexInverted": True
                    },
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "محتوای مقاله",
                        "indexInverted": True
                    },
                    {
                        "name": "summary",
                        "dataType": ["text"],
                        "description": "خلاصه مقاله",
                        "indexInverted": True
                    },
                    {
                        "name": "tags",
                        "dataType": ["text[]"],
                        "description": "تگ‌های مقاله",
                        "indexInverted": True
                    },
                    {
                        "name": "category",
                        "dataType": ["text"],
                        "description": "دسته‌بندی مقاله",
                        "indexInverted": True
                    },
                    {
                        "name": "visibility",
                        "dataType": ["text"],
                        "description": "سطح دسترسی مقاله",
                        "indexInverted": True
                    },
                    {
                        "name": "status",
                        "dataType": ["text"],
                        "description": "وضعیت مقاله",
                        "indexInverted": True
                    },
                    {
                        "name": "created_at",
                        "dataType": ["date"],
                        "description": "تاریخ ایجاد"
                    },
                    {
                        "name": "updated_at",
                        "dataType": ["date"],
                        "description": "تاریخ بروزرسانی"
                    },
                    {
                        "name": "article_id",
                        "dataType": ["text"],
                        "description": "شناسه مقاله در MongoDB",
                        "indexInverted": True
                    }
                ]
            }

            # تعریف کلاس Ticket (بدون vectorizer - فقط برای جستجوی متنی)
            ticket_class = {
                "class": "SupportTicket",
                "description": "تیکت‌های پشتیبانی مشتری (بدون vectorization)",
                "vectorIndexType": "hnsw",
                "vectorIndexConfig": {
                    "distance": "cosine",
                    "ef": -1,
                    "efConstruction": 128,
                    "maxConnections": 64
                },
                "properties": [
                    {
                        "name": "title",
                        "dataType": ["text"],
                        "description": "عنوان تیکت",
                        "indexInverted": True
                    },
                    {
                        "name": "description",
                        "dataType": ["text"],
                        "description": "توضیحات تیکت",
                        "indexInverted": True
                    },
                    {
                        "name": "status",
                        "dataType": ["text"],
                        "description": "وضعیت تیکت",
                        "indexInverted": True
                    },
                    {
                        "name": "priority",
                        "dataType": ["text"],
                        "description": "اولویت تیکت",
                        "indexInverted": True
                    },
                    {
                        "name": "created_at",
                        "dataType": ["date"],
                        "description": "تاریخ ایجاد"
                    },
                    {
                        "name": "updated_at",
                        "dataType": ["date"],
                        "description": "تاریخ بروزرسانی"
                    },
                    {
                        "name": "ticket_id",
                        "dataType": ["text"],
                        "description": "شناسه تیکت در MongoDB",
                        "indexInverted": True
                    },
                    {
                        "name": "customer_id",
                        "dataType": ["text"],
                        "description": "شناسه مشتری",
                        "indexInverted": True
                    }
                ]
            }

            # ایجاد کلاس‌ها در Weaviate (اگر وجود نداشته باشند)
            try:
                self.weaviate_client.schema.create_class(article_class)
                logger.info("✅ کلاس KnowledgeBaseArticle ایجاد شد")
            except Exception as e:
                if "already exists" in str(e):
                    logger.info("ℹ️ کلاس KnowledgeBaseArticle قبلاً ایجاد شده")
                else:
                    raise e

            try:
                self.weaviate_client.schema.create_class(ticket_class)
                logger.info("✅ کلاس SupportTicket ایجاد شد")
            except Exception as e:
                if "already exists" in str(e):
                    logger.info("ℹ️ کلاس SupportTicket قبلاً ایجاد شده")
                else:
                    raise e

            return True

        except Exception as e:
            logger.error(f"❌ خطا در ایجاد schema: {str(e)}")
            return False

    async def migrate_knowledge_base(self) -> bool:
        """انتقال مقالات پایگاه دانش از MongoDB به Weaviate"""
        try:
            logger.info("📚 شروع انتقال مقالات پایگاه دانش...")

            from app.domain.entities_refactored import KnowledgeBaseArticle
            from app.infrastructure.database_refactored import init_db

            # اطمینان از initialize شدن database
            await init_db()

            # دریافت همه مقالات منتشر شده
            articles = await KnowledgeBaseArticle.find_all().to_list()
            logger.info(f"📊 تعداد مقالات یافت شده: {len(articles)}")

            if not articles:
                logger.info("⚠️ هیچ مقاله‌ای یافت نشد")
                return True

            migrated_count = 0
            for article in articles:
                try:
                    # آماده‌سازی داده‌ها برای Weaviate
                    # تبدیل tags به لیست string
                    tags_list = []
                    if article.tags:
                        for tag in article.tags:
                            if hasattr(tag, 'name'):
                                tags_list.append(tag.name)
                            elif isinstance(tag, str):
                                tags_list.append(tag)
                            else:
                                tags_list.append(str(tag))

                    # تبدیل تاریخ‌ها به RFC3339 format
                    created_at_rfc3339 = None
                    updated_at_rfc3339 = None

                    if article.created_at:
                        # اضافه کردن Z برای UTC timezone
                        created_at_rfc3339 = article.created_at.isoformat() + "Z"
                    if article.updated_at:
                        updated_at_rfc3339 = article.updated_at.isoformat() + "Z"

                    article_data = {
                        "title": article.title,
                        "content": article.content_html or article.content_markdown or "",
                        "summary": article.summary or "",
                        "tags": tags_list,
                        "category": article.category or "عمومی",
                        "visibility": article.visibility.value if hasattr(article.visibility, 'value') else str(article.visibility),
                        "status": article.status.value if hasattr(article.status, 'value') else str(article.status),
                        "created_at": created_at_rfc3339,
                        "updated_at": updated_at_rfc3339,
                        "article_id": str(article.id)
                    }

                    # اضافه کردن به Weaviate با تنظیم header
                    import requests
                    embedder_api_key = settings.embedder_api_key_loaded

                    headers = {}
                    if embedder_api_key:
                        headers['X-OpenAI-Api-Key'] = embedder_api_key

                    # استفاده از requests برای ارسال مستقیم با header
                    weaviate_url = settings.weaviate_url_loaded or "http://localhost:8080"
                    response = requests.post(
                        f"{weaviate_url}/v1/objects",
                        json={
                            "class": "KnowledgeBaseArticle",
                            "properties": article_data
                        },
                        headers=headers
                    )

                    if response.status_code not in [200, 201]:
                        raise Exception(f"HTTP {response.status_code}: {response.text}")

                    migrated_count += 1

                    if migrated_count % 10 == 0:
                        logger.info(f"📝 {migrated_count} مقاله منتقل شد...")

                except Exception as e:
                    logger.error(f"❌ خطا در انتقال مقاله {getattr(article, 'title', 'Unknown')}: {str(e)}")
                    logger.error(f"Article data: {article}")
                    continue

            logger.info(f"✅ انتقال مقالات تکمیل شد: {migrated_count} مقاله")
            return True

        except Exception as e:
            logger.error(f"❌ خطا در انتقال مقالات: {str(e)}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return False

    async def migrate_tickets(self) -> bool:
        """انتقال تیکت‌ها از MongoDB به Weaviate"""
        try:
            logger.info("🎫 شروع انتقال تیکت‌ها...")

            from app.domain.entities_refactored import Ticket
            from app.infrastructure.database_refactored import init_db

            # اطمینان از initialize شدن database
            await init_db()

            # دریافت همه تیکت‌ها
            tickets = await Ticket.find_all().to_list()
            logger.info(f"📊 تعداد تیکت‌های یافت شده: {len(tickets)}")

            if not tickets:
                logger.info("⚠️ هیچ تیکتی یافت نشد")
                return True

            migrated_count = 0
            for ticket in tickets:
                try:
                    # آماده‌سازی داده‌ها برای Weaviate
                    # تبدیل تاریخ‌ها به RFC3339 format
                    created_at_rfc3339 = None
                    updated_at_rfc3339 = None

                    if ticket.created_at:
                        created_at_rfc3339 = ticket.created_at.isoformat() + "Z"
                    if ticket.updated_at:
                        updated_at_rfc3339 = ticket.updated_at.isoformat() + "Z"

                    ticket_data = {
                        "title": ticket.title,
                        "description": ticket.description or "",
                        "status": ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status),
                        "priority": ticket.priority.value if hasattr(ticket.priority, 'value') else str(ticket.priority),
                        "created_at": created_at_rfc3339,
                        "updated_at": updated_at_rfc3339,
                        "ticket_id": str(ticket.id),
                        "customer_id": str(ticket.customer_id) if ticket.customer_id else ""
                    }

                    # اضافه کردن به Weaviate با تنظیم header
                    import requests
                    embedder_api_key = settings.embedder_api_key_loaded

                    headers = {}
                    if embedder_api_key:
                        headers['X-OpenAI-Api-Key'] = embedder_api_key

                    # استفاده از requests برای ارسال مستقیم با header
                    weaviate_url = settings.weaviate_url_loaded or "http://localhost:8080"
                    response = requests.post(
                        f"{weaviate_url}/v1/objects",
                        json={
                            "class": "SupportTicket",
                            "properties": ticket_data
                        },
                        headers=headers
                    )

                    if response.status_code not in [200, 201]:
                        raise Exception(f"HTTP {response.status_code}: {response.text}")

                    migrated_count += 1

                    if migrated_count % 10 == 0:
                        logger.info(f"📝 {migrated_count} تیکت منتقل شد...")

                except Exception as e:
                    logger.error(f"❌ خطا در انتقال تیکت {getattr(ticket, 'title', 'Unknown')}: {str(e)}")
                    logger.error(f"Ticket data: {ticket}")
                    continue

            logger.info(f"✅ انتقال تیکت‌ها تکمیل شد: {migrated_count} تیکت")
            return True

        except Exception as e:
            logger.error(f"❌ خطا در انتقال تیکت‌ها: {str(e)}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return False

    def verify_setup(self) -> Dict[str, Any]:
        """بررسی صحت تنظیمات"""
        result = {
            "weaviate_connection": False,
            "mongodb_connection": False,
            "schema_exists": False,
            "data_counts": {},
            "errors": []
        }

        try:
            # بررسی اتصال Weaviate
            if self.weaviate_client:
                try:
                    meta = self.weaviate_client.get_meta()
                    result["weaviate_connection"] = True
                    logger.info("✅ Weaviate متصل است")
                except Exception as e:
                    result["errors"].append(f"Weaviate connection error: {str(e)}")
                    logger.error(f"❌ خطای اتصال Weaviate: {str(e)}")
            else:
                result["errors"].append("Weaviate client not initialized")

            # بررسی اتصال MongoDB
            if self.mongodb_client:
                try:
                    db = self.mongodb_client.get_default_database()
                    collections = db.list_collection_names()
                    result["mongodb_connection"] = True
                    logger.info("✅ MongoDB متصل است")
                except Exception as e:
                    result["errors"].append(f"MongoDB connection error: {str(e)}")
                    logger.error(f"❌ خطای اتصال MongoDB: {str(e)}")
            else:
                result["errors"].append("MongoDB client not initialized")

            # بررسی schema های Weaviate
            if self.weaviate_client:
                try:
                    schema = self.weaviate_client.schema.get()
                    classes = [cls["class"] for cls in schema["classes"]]
                    if "KnowledgeBaseArticle" in classes and "SupportTicket" in classes:
                        result["schema_exists"] = True
                        logger.info("✅ Schema های Weaviate موجود هستند")
                    else:
                        result["errors"].append(f"Missing classes: {classes}")
                        logger.warning(f"⚠️ کلاس‌های موجود: {classes}")
                except Exception as e:
                    result["errors"].append(f"Schema check error: {str(e)}")
                    logger.error(f"❌ خطای بررسی schema: {str(e)}")

            # لاگ گرفتن اطلاعات vectorizer
            if result["weaviate_connection"]:
                self.log_vectorizer_info()

            # شمارش داده‌ها
            if result["weaviate_connection"]:
                try:
                    # شمارش مقالات
                    article_count = self.weaviate_client.query.aggregate("KnowledgeBaseArticle").with_meta_count().do()
                    result["data_counts"]["articles"] = article_count["data"]["Aggregate"]["KnowledgeBaseArticle"][0]["meta"]["count"]

                    # شمارش تیکت‌ها
                    ticket_count = self.weaviate_client.query.aggregate("SupportTicket").with_meta_count().do()
                    result["data_counts"]["tickets"] = ticket_count["data"]["Aggregate"]["SupportTicket"][0]["meta"]["count"]

                    logger.info(f"📊 آمار داده‌ها - مقالات: {result['data_counts']['articles']}, تیکت‌ها: {result['data_counts']['tickets']}")

                except Exception as e:
                    result["errors"].append(f"Data count error: {str(e)}")
                    logger.error(f"❌ خطای شمارش داده‌ها: {str(e)}")
                    # تنظیم مقادیر پیش‌فرض اگر شمارش موفق نبود
                    result["data_counts"]["articles"] = 0
                    result["data_counts"]["tickets"] = 0

        except Exception as e:
            result["errors"].append(f"Verification error: {str(e)}")
            logger.error(f"❌ خطای کلی در بررسی: {str(e)}")

        return result

    async def setup_and_verify(self) -> bool:
        """راه‌اندازی کامل و بررسی"""
        logger.info("🚀 شروع راه‌اندازی سیستم...")

        # اتصال به MongoDB
        if not await self.connect_mongodb():
            return False

        # اتصال به Weaviate
        if not self.connect_weaviate():
            return False

        # ایجاد schema
        if not self.create_weaviate_schema():
            return False

        # بررسی نهایی
        verification = self.verify_setup()

        if verification["weaviate_connection"] and verification["mongodb_connection"] and verification["schema_exists"]:
            logger.info("✅ راه‌اندازی با موفقیت تکمیل شد!")
            return True
        else:
            logger.error("❌ راه‌اندازی ناموفق بود")
            for error in verification["errors"]:
                logger.error(f"  - {error}")
            return False

    async def migrate_all_data(self) -> bool:
        """انتقال همه داده‌ها"""
        logger.info("🔄 شروع انتقال داده‌ها...")

        # لاگ گرفتن اطلاعات vectorizer
        self.log_vectorizer_info()

        # اتصال به دیتابیس‌ها
        if not await self.connect_mongodb():
            return False

        if not self.connect_weaviate():
            return False

        # انتقال مقالات
        if not await self.migrate_knowledge_base():
            logger.warning("⚠️ انتقال مقالات ناموفق بود")

        # انتقال تیکت‌ها
        if not await self.migrate_tickets():
            logger.warning("⚠️ انتقال تیکت‌ها ناموفق بود")

        # بررسی نهایی
        verification = self.verify_setup()

        articles_count = verification["data_counts"].get("articles", 0)
        tickets_count = verification["data_counts"].get("tickets", 0)

        if articles_count > 0 or tickets_count > 0:
            logger.info("✅ انتقال داده‌ها تکمیل شد!")
            return True
        else:
            logger.warning("⚠️ هیچ داده‌ای منتقل نشد")
            return False

    async def delete_all_articles_from_mongodb(self) -> bool:
        """حذف همه مقالات از MongoDB"""
        try:
            logger.info("🗑️ شروع حذف همه مقالات از MongoDB...")
            
            from app.domain.entities_refactored import KnowledgeBaseArticle
            from app.infrastructure.database_refactored import init_db
            
            # اطمینان از initialize شدن database
            await init_db()
            
            # پیدا کردن همه مقالات
            articles = await KnowledgeBaseArticle.find_all().to_list()
            logger.info(f"📊 تعداد مقالات برای حذف: {len(articles)}")
            
            if not articles:
                logger.info("⚠️ هیچ مقاله‌ای برای حذف یافت نشد")
                return True
            
            deleted_count = 0
            for article in articles:
                try:
                    await article.delete()
                    deleted_count += 1
                    logger.info(f"✅ مقاله '{article.title}' حذف شد")
                except Exception as e:
                    logger.error(f"❌ خطا در حذف مقاله '{article.title}': {str(e)}")
                    continue
            
            logger.info(f"✅ {deleted_count} مقاله با موفقیت از MongoDB حذف شدند")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطا در حذف مقالات از MongoDB: {str(e)}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return False

    async def delete_articles_by_ids_from_mongodb(self, article_ids: List[str]) -> bool:
        """حذف مقالات خاص از MongoDB بر اساس شناسه‌ها"""
        try:
            logger.info(f"🗑️ شروع حذف {len(article_ids)} مقاله از MongoDB...")
            
            from app.domain.entities_refactored import KnowledgeBaseArticle
            from app.infrastructure.database_refactored import init_db
            
            # اطمینان از initialize شدن database
            await init_db()
            
            deleted_count = 0
            for article_id in article_ids:
                try:
                    article = await KnowledgeBaseArticle.get(article_id)
                    if article:
                        await article.delete()
                        deleted_count += 1
                        logger.info(f"✅ مقاله '{article.title}' حذف شد")
                    else:
                        logger.warning(f"⚠️ مقاله با شناسه {article_id} یافت نشد")
                except Exception as e:
                    logger.error(f"❌ خطا در حذف مقاله با شناسه {article_id}: {str(e)}")
                    continue
            
            logger.info(f"✅ {deleted_count} مقاله با موفقیت از MongoDB حذف شدند")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطا در حذف مقالات از MongoDB: {str(e)}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return False

    def delete_all_articles_from_weaviate(self) -> bool:
        """حذف همه مقالات از Weaviate"""
        try:
            logger.info("🗑️ شروع حذف همه مقالات از Weaviate...")

            # اتصال به Weaviate اگر برقرار نیست
            if not self.weaviate_client:
                if not self.connect_weaviate():
                    logger.error("❌ اتصال به Weaviate ناموفق بود")
                    return False

            # دریافت همه مقالات برای شمارش
            query = self.weaviate_client.query.get('KnowledgeBaseArticle').with_additional('id').with_limit(10000).do()
            articles = query.get('data', {}).get('Get', {}).get('KnowledgeBaseArticle', [])
            logger.info(f"📊 تعداد مقالات برای حذف: {len(articles)}")

            if not articles:
                logger.info("⚠️ هیچ مقاله‌ای برای حذف یافت نشد")
                return True

            # روش بهتر: حذف یکی یکی با استفاده از REST API
            deleted_count = 0
            for article in articles:
                try:
                    article_id = article.get('_additional', {}).get('id')
                    if article_id:
                        # حذف با استفاده از REST API
                        import requests
                        weaviate_url = settings.weaviate_url_loaded or "http://localhost:8080"
                        response = requests.delete(f"{weaviate_url}/v1/objects/{article_id}")

                        if response.status_code in [200, 204]:
                            deleted_count += 1
                        else:
                            logger.warning(f"⚠️ خطا در حذف مقاله {article_id}: HTTP {response.status_code}")
                    else:
                        logger.warning("⚠️ مقاله بدون شناسه یافت شد")

                except Exception as e:
                    logger.warning(f"⚠️ خطا در حذف مقاله: {str(e)}")
                    continue

            logger.info(f"✅ {deleted_count} مقاله با موفقیت از Weaviate حذف شدند")
            return True

        except Exception as e:
            logger.error(f"❌ خطا در حذف مقالات از Weaviate: {str(e)}")
            return False

    def delete_articles_by_ids_from_weaviate(self, article_ids: List[str]) -> bool:
        """حذف مقالات خاص از Weaviate بر اساس شناسه‌ها"""
        try:
            logger.info(f"🗑️ شروع حذف {len(article_ids)} مقاله از Weaviate...")

            # اتصال به Weaviate اگر برقرار نیست
            if not self.weaviate_client:
                if not self.connect_weaviate():
                    logger.error("❌ اتصال به Weaviate ناموفق بود")
                    return False

            deleted_count = 0
            for article_id in article_ids:
                try:
                    # حذف بر اساس شناسه MongoDB با استفاده از Weaviate client
                    result = self.weaviate_client.data_object.delete(
                        class_name='KnowledgeBaseArticle',
                        where={
                            'path': ['article_id'],
                            'operator': 'Equal',
                            'valueText': article_id
                        }
                    )
                    deleted_count += 1
                    logger.info(f"✅ مقاله با شناسه {article_id} حذف شد")
                except Exception as e:
                    logger.warning(f"⚠️ خطا در حذف مقاله با شناسه {article_id}: {str(e)}")
                    continue

            logger.info(f"✅ {deleted_count} مقاله با موفقیت از Weaviate حذف شدند")
            return True

        except Exception as e:
            logger.error(f"❌ خطا در حذف مقالات از Weaviate: {str(e)}")
            return False

    async def delete_all_articles_from_both_databases(self) -> bool:
        """حذف همه مقالات از هر دو دیتابیس (MongoDB و Weaviate)"""
        try:
            logger.info("🗑️ شروع حذف همه مقالات از هر دو دیتابیس...")
            
            # اتصال به دیتابیس‌ها
            if not await self.connect_mongodb():
                logger.error("❌ اتصال به MongoDB ناموفق بود")
                return False
                
            if not self.connect_weaviate():
                logger.error("❌ اتصال به Weaviate ناموفق بود")
                return False
            
            # حذف از MongoDB
            mongodb_success = await self.delete_all_articles_from_mongodb()
            
            # حذف از Weaviate
            weaviate_success = self.delete_all_articles_from_weaviate()
            
            if mongodb_success and weaviate_success:
                logger.info("✅ همه مقالات با موفقیت از هر دو دیتابیس حذف شدند")
                return True
            else:
                logger.error("❌ حذف مقالات از یکی از دیتابیس‌ها ناموفق بود")
                return False
                
        except Exception as e:
            logger.error(f"❌ خطا در حذف مقالات: {str(e)}")
            return False

    async def delete_articles_by_ids_from_both_databases(self, article_ids: List[str]) -> bool:
        """حذف مقالات خاص از هر دو دیتابیس بر اساس شناسه‌ها"""
        try:
            logger.info(f"🗑️ شروع حذف {len(article_ids)} مقاله از هر دو دیتابیس...")
            
            # اتصال به دیتابیس‌ها
            if not await self.connect_mongodb():
                logger.error("❌ اتصال به MongoDB ناموفق بود")
                return False
                
            if not self.connect_weaviate():
                logger.error("❌ اتصال به Weaviate ناموفق بود")
                return False
            
            # حذف از MongoDB
            mongodb_success = await self.delete_articles_by_ids_from_mongodb(article_ids)
            
            # حذف از Weaviate
            weaviate_success = self.delete_articles_by_ids_from_weaviate(article_ids)
            
            if mongodb_success and weaviate_success:
                logger.info(f"✅ {len(article_ids)} مقاله با موفقیت از هر دو دیتابیس حذف شدند")
                return True
            else:
                logger.error("❌ حذف مقالات از یکی از دیتابیس‌ها ناموفق بود")
                return False
                
        except Exception as e:
            logger.error(f"❌ خطا در حذف مقالات: {str(e)}")
            return False

    def cleanup(self):
        """پاک‌سازی اتصالات"""
        try:
            if self.mongodb_client:
                self.mongodb_client.close()
                logger.info("🧹 اتصال MongoDB بسته شد")

            if self.weaviate_client:
                # Weaviate client doesn't need explicit closing
                logger.info("🧹 اتصال Weaviate پاک‌سازی شد")

        except Exception as e:
            logger.error(f"❌ خطا در پاک‌سازی: {str(e)}")


async def main():
    """تابع اصلی برنامه"""
    parser = argparse.ArgumentParser(description="Weaviate-MongoDB Connection Script")
    parser.add_argument("--setup", action="store_true", help="راه‌اندازی اولیه سیستم")
    parser.add_argument("--migrate", action="store_true", help="انتقال داده‌ها از MongoDB به Weaviate")
    parser.add_argument("--verify", action="store_true", help="بررسی وضعیت سیستم")
    parser.add_argument("--test-connection", action="store_true", help="تست اتصال به هر دو دیتابیس")
    parser.add_argument("--delete-all", action="store_true", help="حذف همه مقالات از هر دو دیتابیس")
    parser.add_argument("--delete-by-ids", nargs='+', help="حذف مقالات خاص بر اساس شناسه‌ها")
    parser.add_argument("--delete-from-mongodb", action="store_true", help="حذف همه مقالات فقط از MongoDB")
    parser.add_argument("--delete-from-weaviate", action="store_true", help="حذف همه مقالات فقط از Weaviate")

    args = parser.parse_args()

    if not any([args.setup, args.migrate, args.verify, args.test_connection, 
                args.delete_all, args.delete_by_ids, args.delete_from_mongodb, args.delete_from_weaviate]):
        parser.print_help()
        return

    connector = WeaviateMongoDBConnector()

    try:
        if args.test_connection:
            logger.info("🔍 تست اتصال...")
            mongodb_ok = await connector.connect_mongodb()
            weaviate_ok = connector.connect_weaviate()

            logger.info(f"MongoDB: {'✅' if mongodb_ok else '❌'}")
            logger.info(f"Weaviate: {'✅' if weaviate_ok else '❌'}")

            if mongodb_ok and weaviate_ok:
                logger.info("✅ هر دو اتصال موفق هستند!")
            else:
                logger.error("❌ یک یا چند اتصال ناموفق بود")

        elif args.setup:
            success = await connector.setup_and_verify()
            if success:
                logger.info("🎉 سیستم آماده استفاده است!")
            else:
                logger.error("💥 راه‌اندازی سیستم ناموفق بود")

        elif args.migrate:
            success = await connector.migrate_all_data()
            if success:
                logger.info("🎉 انتقال داده‌ها تکمیل شد!")
            else:
                logger.error("💥 انتقال داده‌ها ناموفق بود")

        elif args.verify:
            # اتصال برای بررسی
            await connector.connect_mongodb()
            connector.connect_weaviate()

            result = connector.verify_setup()

            logger.info("📋 گزارش وضعیت سیستم:")
            logger.info(f"  Weaviate متصل: {'✅' if result['weaviate_connection'] else '❌'}")
            logger.info(f"  MongoDB متصل: {'✅' if result['mongodb_connection'] else '❌'}")
            logger.info(f"  Schema موجود: {'✅' if result['schema_exists'] else '❌'}")
            logger.info(f"  تعداد مقالات: {result['data_counts'].get('articles', 0)}")
            logger.info(f"  تعداد تیکت‌ها: {result['data_counts'].get('tickets', 0)}")

            if result["errors"]:
                logger.info("❌ خطاها:")
                for error in result["errors"]:
                    logger.info(f"  - {error}")

        elif args.delete_all:
            logger.info("🗑️ حذف همه مقالات از هر دو دیتابیس...")
            success = await connector.delete_all_articles_from_both_databases()
            if success:
                logger.info("🎉 همه مقالات با موفقیت حذف شدند!")
            else:
                logger.error("💥 حذف مقالات ناموفق بود")

        elif args.delete_by_ids:
            logger.info(f"🗑️ حذف مقالات با شناسه‌ها: {args.delete_by_ids}")
            success = await connector.delete_articles_by_ids_from_both_databases(args.delete_by_ids)
            if success:
                logger.info("🎉 مقالات انتخابی با موفقیت حذف شدند!")
            else:
                logger.error("💥 حذف مقالات انتخابی ناموفق بود")

        elif args.delete_from_mongodb:
            logger.info("🗑️ حذف همه مقالات از MongoDB...")
            success = await connector.delete_all_articles_from_mongodb()
            if success:
                logger.info("🎉 همه مقالات از MongoDB حذف شدند!")
            else:
                logger.error("💥 حذف مقالات از MongoDB ناموفق بود")

        elif args.delete_from_weaviate:
            logger.info("🗑️ حذف همه مقالات از Weaviate...")
            success = connector.delete_all_articles_from_weaviate()
            if success:
                logger.info("🎉 همه مقالات از Weaviate حذف شدند!")
            else:
                logger.error("💥 حذف مقالات از Weaviate ناموفق بود")

    finally:
        connector.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
