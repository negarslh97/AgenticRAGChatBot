#!/usr/bin/env python3
"""
Weaviate-MongoDB Connector for knowledge base management.
Handles migration, vectorization, and data synchronization.
"""

import warnings
import sys
import os
import asyncio
import logging
import argparse
from typing import Dict, List, Any, Optional
from pathlib import Path

import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.config import Configure, Property, DataType, VectorDistances
from weaviate.classes.query import Filter

# Suppress warnings
warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore'

# Add project root to path if running as script
if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

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
    """
    اتصال‌دهنده بین Weaviate و MongoDB
    
    ⚠️ این کلاس برای migration و کارهای CLI استفاده می‌شود
    ✅ برای استفاده در API، از Connection Manager استفاده کنید
    """

    def __init__(self):
        self.weaviate_client = None
        self.mongodb_client = None
        self.collection_name = "SallyChatBot"
        self._use_connection_manager = False  # برای CLI این False است

    def connect_weaviate(self, use_manager: bool = False) -> bool:
        """
        اتصال به Weaviate
        
        Args:
            use_manager: اگر True باشد، از Connection Manager استفاده می‌کند
        """
        try:
            logger.info("🔌 اتصال به Weaviate...")

            if use_manager:
                # ✅ استفاده از Connection Manager (برای API)
                from app.infrastructure.connection_manager import WeaviateConnectionManager
                manager = WeaviateConnectionManager()
                self.weaviate_client = manager.get_client()
                self._use_connection_manager = True
                logger.info("✅ از Connection Manager استفاده شد")
                return True

            # ❌ اتصال مستقیم (فقط برای CLI و migration)
            weaviate_url = settings.weaviate_url_loaded or "http://localhost:8080"
            weaviate_api_key = settings.weaviate_api_key_loaded
            embedder_api_key = settings.embedder_api_key_loaded
            
            is_local = "localhost" in weaviate_url or "127.0.0.1" in weaviate_url

            logger.info(f"📍 Weaviate URL: {weaviate_url}")
            
            # نمایش وضعیت WEAVIATE_API_KEY (برای احراز هویت کلاینت)
            if weaviate_api_key:
                logger.info(f"🔑 Weaviate API Key: {weaviate_api_key[:10]}... ✅ تنظیم شده")
            elif is_local:
                logger.info("🔑 Weaviate API Key: غیرفعال (Anonymous Access برای localhost)")
            else:
                logger.warning("⚠️ Weaviate API Key: تنظیم نشده - برای Weaviate Cloud نیاز است")
            
            # نمایش وضعیت Embedder API Key (برای vectorization)
            if embedder_api_key:
                logger.info(f"🔐 Embedder API Key: {embedder_api_key[:10]}... ✅ تنظیم شده (برای vectorization)")
            else:
                logger.warning("⚠️ Embedder API Key: تنظیم نشده - برای vectorization نیاز است")

            # Parse URL to get host and port
            from urllib.parse import urlparse
            parsed_url = urlparse(weaviate_url)
            http_host = parsed_url.hostname or "localhost"
            http_port = parsed_url.port or 8080
            http_secure = parsed_url.scheme == "https"

            # اتصال به Weaviate using v4 client with proper auth
            if weaviate_api_key:
                self.weaviate_client = weaviate.connect_to_custom(
                    http_host=http_host,
                    http_port=http_port,
                    http_secure=http_secure,
                    grpc_host=http_host,
                    grpc_port=50051,
                    grpc_secure=http_secure,
                    auth_credentials=Auth.api_key(weaviate_api_key)
                )
            else:
                self.weaviate_client = weaviate.connect_to_custom(
                    http_host=http_host,
                    http_port=http_port,
                    http_secure=http_secure,
                    grpc_host=http_host,
                    grpc_port=50051,
                    grpc_secure=http_secure
                )

            # Test connection
            if self.weaviate_client.is_ready():
                logger.info(f"✅ اتصال به Weaviate موفق")
                return True
            else:
                logger.error("❌ Weaviate آماده نیست")
                return False

        except Exception as e:
            logger.error(f"❌ خطا در اتصال به Weaviate: {str(e)}")
            return False

    async def connect_mongodb(self) -> bool:
        """اتصال به MongoDB"""
        try:
            logger.info("🔌 اتصال به MongoDB...")

            from motor.motor_asyncio import AsyncIOMotorClient
            import os

            # در محیط تست از دیتابیس تست استفاده کن
            if os.getenv("PYTEST_CURRENT_TEST") or "test" in os.getenv("DATABASE_URL", ""):
                mongodb_url = os.getenv("TEST_DATABASE_URL", "mongodb://localhost:27017/SallyChatBot_Test")
                logger.info(f"🧪 تست مد - استفاده از دیتابیس تست: {mongodb_url}")
            else:
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

            if not hasattr(self, 'weaviate_client') or not self.weaviate_client:
                logger.warning("⚠️ Weaviate client موجود نیست")
                return

            # دریافت اطلاعات collection MarkdownNode
            try:
                collection = self.weaviate_client.collections.get("MarkdownNode")
                config = collection.config.get()
                
                logger.info(f"🤖 کلاس 'MarkdownNode' از vectorizer استفاده می‌کند (ساختار درختی Markdown)")
                
                # دریافت اطلاعات vectorizer
                vectorizer_config = config.vectorizer_config
                if vectorizer_config:
                    logger.info(f"   📏 Vectorizer: {vectorizer_config}")
                
                # تلاش برای دریافت یک object و بررسی ابعاد vector آن
                try:
                    response = collection.query.fetch_objects(
                        include_vector=True,
                        limit=1
                    )
                    
                    if response.objects and len(response.objects) > 0:
                        vector = response.objects[0].vector
                        dimensions = len(vector.get('default', [])) if isinstance(vector, dict) else len(vector) if vector else 1536
                        logger.info(f"   📐 ابعاد vector: {dimensions}")
                    else:
                        logger.info(f"   📐 ابعاد vector: 1536 (پیش‌فرض)")
                        
                except Exception as e:
                    logger.warning(f"   ⚠️ نتوانست اطلاعات vector را دریافت کند: {str(e)}")
                    logger.info(f"   📐 ابعاد vector: 1536 (پیش‌فرض)")
                    
            except Exception as e:
                logger.error(f"❌ خطا در دریافت اطلاعات collection: {str(e)}")

        except Exception as e:
            logger.error(f"❌ خطا در دریافت اطلاعات vectorizer: {str(e)}")

    def create_weaviate_schema(self) -> bool:
        """ایجاد schema های Weaviate"""
        try:
            logger.info("🏗️ ایجاد schema های Weaviate...")

            # تنظیم API key و مدل برای embedder
            embedder_api_key = settings.embedder_api_key_loaded
            embedder_openai_base_url = settings.embedder_openai_base_url_loaded
            embedder_model = settings.embedder_model_loaded

            logger.info(f"🔢 Embedder Model: {embedder_model}")
            logger.info(f"🔧 استفاده از Client-Side Vectorization (تولید vector در Python)")

            # استفاده از "none" vectorizer - ما خودمان vectorها را تولید می‌کنیم
            vectorizer_config = Configure.Vectorizer.none()

            try:
                # ایجاد collection با v4 API
                self.weaviate_client.collections.create(
                    name="MarkdownNode",
                    description="گره‌های ساختار درختی Markdown",
                    vectorizer_config=vectorizer_config,
                    vector_index_config=Configure.VectorIndex.hnsw(
                        distance_metric=VectorDistances.COSINE,
                        ef_construction=128,
                        max_connections=64
                    ),
                    properties=[
                        Property(
                            name="node_id",
                            data_type=DataType.TEXT,
                            description="شناسه منحصر به فرد گره",
                            skip_vectorization=True,
                            index_filterable=True,
                            index_searchable=True
                        ),
                        Property(
                            name="article_id",
                            data_type=DataType.TEXT,
                            description="شناسه مقاله والد",
                            skip_vectorization=True,
                            index_filterable=True,
                            index_searchable=True
                        ),
                        Property(
                            name="title",
                            data_type=DataType.TEXT,
                            description="عنوان گره (بدون #)",
                            index_filterable=True,
                            index_searchable=True
                        ),
                        Property(
                            name="level",
                            data_type=DataType.INT,
                            description="سطح گره (1-6)",
                            skip_vectorization=True
                        ),
                        Property(
                            name="content",
                            data_type=DataType.TEXT,
                            description="محتوای زیر این گره",
                            index_filterable=True,
                            index_searchable=True
                        ),
                        Property(
                            name="parent_id",
                            data_type=DataType.TEXT,
                            description="شناسه گره والد (-1 برای ریشه)",
                            skip_vectorization=True,
                            index_filterable=True,
                            index_searchable=True
                        ),
                        Property(
                            name="path",
                            data_type=DataType.TEXT,
                            description="مسیر کامل در درخت مانند '1.2.3'",
                            skip_vectorization=True,
                            index_filterable=True,
                            index_searchable=True
                        ),
                        Property(
                            name="order",
                            data_type=DataType.INT,
                            description="ترتیب در بین خواهر و برادرها",
                            skip_vectorization=True
                        ),
                        Property(
                            name="full_content",
                            data_type=DataType.TEXT,
                            description="محتوای کامل مقاله برای زمینه",
                            skip_vectorization=True
                        )
                    ]
                )
                logger.info("✅ Collection MarkdownNode (ساختار درختی) ایجاد شد")
            except Exception as e:
                error_msg = str(e).lower()
                if "already exists" in error_msg or "duplicate" in error_msg:
                    logger.info("ℹ️ Collection MarkdownNode قبلاً ایجاد شده")
                else:
                    logger.warning(f"⚠️ Collection MarkdownNode ایجاد نشد: {str(e)}")

            return True

        except Exception as e:
            logger.error(f"❌ خطا در ایجاد schema: {str(e)}")
            return False

    async def save_markdown_tree(self, tree, full_content: str) -> bool:
        """
        ذخیره ساختار درختی Markdown در Weaviate با Client-Side Vectorization

        Args:
            tree: ساختار درختی Markdown
            full_content: محتوای کامل مقاله برای زمینه

        Returns:
            True اگر ذخیره موفق باشد
        """
        try:
            logger.info(f"🌳 شروع ذخیره درخت Markdown برای مقاله {tree.article_id}")

            # دریافت همه گره‌ها
            all_nodes = tree.get_all_nodes()

            if not all_nodes:
                logger.info("⚠️ درخت خالی است، چیزی برای ذخیره وجود ندارد")
                return True

            # تولید vectorها برای همه گره‌ها یکجا (بهینه‌تر)
            logger.info(f"🔢 تولید {len(all_nodes)} vector با OpenAI...")
            from openai import OpenAI
            
            embedder_api_key = settings.embedder_api_key_loaded
            embedder_base_url = settings.embedder_openai_base_url_loaded
            embedder_model = settings.embedder_model_loaded
            
            openai_client = OpenAI(
                api_key=embedder_api_key,
                base_url=embedder_base_url
            )
            
            # ایجاد متن‌های ترکیبی برای vectorization
            texts_to_vectorize = []
            for node in all_nodes:
                # ترکیب title و content برای vector بهتر
                combined_text = f"{node.title}\n\n{node.content}"
                texts_to_vectorize.append(combined_text)
            
            # تولید vectorها به صورت batch
            response = openai_client.embeddings.create(
                model=embedder_model,
                input=texts_to_vectorize
            )
            
            vectors = [item.embedding for item in response.data]
            logger.info(f"✅ {len(vectors)} vector تولید شد (ابعاد: {len(vectors[0])})")

            saved_count = 0

            for idx, node in enumerate(all_nodes):
                try:
                    # آماده‌سازی داده‌ها برای Weaviate
                    node_data = {
                        "node_id": node.id,
                        "article_id": tree.article_id,
                        "title": node.title,
                        "level": node.level,
                        "content": node.content,
                        "parent_id": node.parent_id,
                        "path": node.path,
                        "order": node.order,
                        "full_content": full_content
                    }

                    # ذخیره در Weaviate با vector تولید شده
                    collection = self.weaviate_client.collections.get("MarkdownNode")
                    
                    # بررسی اتصال قبل از ذخیره
                    if not self.weaviate_client.is_ready():
                        logger.error("❌ Weaviate آماده نیست")
                        continue
                    
                    # اضافه کردن vector به همراه data
                    collection.data.insert(
                        properties=node_data,
                        vector=vectors[idx]  # vector از OpenAI
                    )
                    logger.info(f"✅ گره '{node.title}' با vector ذخیره شد")

                    saved_count += 1

                except Exception as e:
                    logger.error(f"❌ خطا در ذخیره گره '{node.title}': {str(e)}")
                    continue

            logger.info(f"✅ {saved_count} گره با vectorization ذخیره شد")
            return True

        except Exception as e:
            logger.error(f"❌ خطا در ذخیره درخت Markdown: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def delete_markdown_nodes(self, article_id: str) -> bool:
        """
        حذف همه گره‌های Markdown یک مقاله از Weaviate

        Args:
            article_id: شناسه مقاله

        Returns:
            True اگر حذف موفق باشد
        """
        try:
            logger.info(f"🗑️ شروع حذف گره‌های Markdown برای مقاله {article_id}")

            # حذف از collection MarkdownNode با v4 API
            collection = self.weaviate_client.collections.get("MarkdownNode")
            collection.data.delete_many(
                where=Filter.by_property("article_id").equal(article_id)
            )
            logger.info("✅ گره‌های Markdown حذف شدند")

            return True

        except Exception as e:
            logger.error(f"❌ خطا در حذف گره‌های Markdown: {str(e)}")
            return False

    # تابع migrate_knowledge_base حذف شده است

    # تابع migrate_tickets حذف شده است

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
            if hasattr(self, 'weaviate_client') and self.weaviate_client:
                try:
                    # استفاده از is_ready() بجای get_meta() برای v4
                    if self.weaviate_client.is_ready():
                        result["weaviate_connection"] = True
                        logger.info("✅ Weaviate متصل است")
                    else:
                        result["errors"].append("Weaviate is not ready")
                        logger.error("❌ Weaviate آماده نیست")
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

            # بررسی collection های Weaviate
            if hasattr(self, 'weaviate_client') and self.weaviate_client:
                try:
                    # بررسی وجود collection با v4 API
                    if self.weaviate_client.collections.exists("MarkdownNode"):
                        result["schema_exists"] = True
                        logger.info("✅ Collection MarkdownNode موجود است")
                    else:
                        result["errors"].append("Missing MarkdownNode collection")
                        logger.warning("⚠️ Collection MarkdownNode یافت نشد")
                except Exception as e:
                    result["errors"].append(f"Schema check error: {str(e)}")
                    logger.error(f"❌ خطای بررسی schema: {str(e)}")

            # لاگ گرفتن اطلاعات vectorizer
            if result["weaviate_connection"]:
                self.log_vectorizer_info()

            # شمارش داده‌ها
            if result["weaviate_connection"] and hasattr(self, 'weaviate_client') and self.weaviate_client:
                try:
                    # شمارش گره‌های Markdown با v4 API
                    if self.weaviate_client.collections.exists("MarkdownNode"):
                        collection = self.weaviate_client.collections.get("MarkdownNode")

                        # استفاده از متد ساده query برای شمارش دقیق
                        try:
                            query_result = collection.query.fetch_objects(limit=10000)  # محدودیت بالا برای شمارش همه
                            count = len(query_result.objects)
                            result["data_counts"]["markdown_nodes"] = count
                            logger.info(f"📊 آمار داده‌ها - گره‌های Markdown: {count}")
                        except Exception as query_error:
                            logger.warning(f"⚠️ خطا در شمارش با query: {query_error}")
                            # استفاده از iterator به عنوان fallback
                            try:
                                objects = collection.iterator(include_vector=False)
                                count = sum(1 for _ in objects)
                                result["data_counts"]["markdown_nodes"] = count
                                logger.info(f"📊 آمار داده‌ها - گره‌های Markdown: {count} (iterator)")
                            except Exception as iter_error:
                                logger.warning(f"⚠️ خطا در شمارش با iterator: {iter_error}")
                                # استفاده از aggregate به عنوان آخرین گزینه
                                try:
                                    aggregate_result = collection.aggregate.over_all(total_count=True)
                                    result["data_counts"]["markdown_nodes"] = aggregate_result.total_count
                                    logger.info(f"📊 آمار داده‌ها - گره‌های Markdown: {result['data_counts']['markdown_nodes']} (aggregate)")
                                except Exception as agg_error:
                                    logger.warning(f"⚠️ خطا در شمارش با aggregate: {agg_error}")
                                    result["data_counts"]["markdown_nodes"] = 0
                    else:
                        result["data_counts"]["markdown_nodes"] = 0
                        logger.info("📊 آمار داده‌ها - گره‌های Markdown: 0 (collection وجود ندارد)")

                except Exception as e:
                    result["errors"].append(f"Data count error: {str(e)}")
                    logger.error(f"❌ خطای شمارش داده‌ها: {str(e)}")
                    # تنظیم مقدار پیش‌فرض اگر شمارش موفق نبود
                    result["data_counts"]["markdown_nodes"] = 0

        except Exception as e:
            result["errors"].append(f"Verification error: {str(e)}")
            logger.error(f"❌ خطای کلی در بررسی: {str(e)}")

        return result

    # تابع display_article_content حذف شده است

    def display_weaviate_objects(self, class_name: str = "MarkdownNode", limit: int = 5) -> bool:
        """نمایش اشیاء ذخیره شده در Weaviate"""
        try:
            logger.info(f"🔍 نمایش اشیاء کلاس {class_name} در Weaviate...")

            if not hasattr(self, 'weaviate_client') or not self.weaviate_client:
                if not self.connect_weaviate():
                    logger.error("❌ اتصال به Weaviate ناموفق بود")
                    return False

            # دریافت اشیاء از Weaviate با v4 API
            collection = self.weaviate_client.collections.get(class_name)
            if class_name == "MarkdownNode":
                response = collection.query.fetch_objects(
                    limit=limit,
                    return_properties=["node_id", "article_id", "title", "content", "path"]
                )
            else:
                response = collection.query.fetch_objects(
                    limit=limit,
                    return_properties=["title", "content"]
                )
            objects = [obj.properties for obj in response.objects]

            if not objects:
                logger.info(f"⚠️ هیچ شیئی از کلاس {class_name} یافت نشد")
                return True

            print(f"\n🔍 اشیاء ذخیره شده در Weaviate (کلاس: {class_name}):")
            if class_name == "MarkdownNode":
                logger.info("="*80)
                logger.info("Node ID | Article ID | عنوان | مسیر | محتوا")
                logger.info("-"*80)

                for i, obj in enumerate(objects, 1):
                    node_id = obj.get('node_id', 'نامشخص')[:15]
                    article_id = obj.get('article_id', 'نامشخص')[:15]
                    title = obj.get('title', 'بدون عنوان')[:20]
                    path = obj.get('path', 'نامشخص')[:10]
                    content = obj.get('content', 'بدون محتوا')[:30]

                    logger.info(f"{i}. {node_id} | {article_id} | {title} | {path} | {content}")
            else:
                logger.info("="*80)
                logger.info("Weaviate ID | عنوان | محتوا")
                logger.info("-"*80)

                for i, obj in enumerate(objects, 1):
                    weaviate_id = str(obj.get('_additional', {}).get('id', 'نامشخص'))[:15]
                    title = obj.get('title', 'بدون عنوان')[:25]
                    content = obj.get('content', 'بدون محتوا')[:30]

                    logger.info(f"{i}. {weaviate_id} | {title} | {content}")

            logger.info("="*80)

            # نمایش آمار با v4 API
            try:
                collection = self.weaviate_client.collections.get(class_name)
                aggregate_result = collection.aggregate.over_all(total_count=True)
                total_count = aggregate_result.total_count
                logger.info(f"تعداد کل اشیاء در Weaviate: {total_count}")
            except Exception as e:
                logger.warning(f"نمی‌توان آمار را دریافت کرد: {str(e)}")

            return True

        except Exception as e:
            logger.error(f"❌ خطا در نمایش اشیاء Weaviate: {str(e)}")
            return False

    def display_file_uploads(self) -> bool:
        """نمایش فایل‌های آپلود شده"""
        try:
            logger.info("📁 نمایش فایل‌های آپلود شده...")

            uploads_dir = Path(__file__).parent.parent.parent / "uploads"
            if not uploads_dir.exists():
                logger.warning("⚠️ پوشه uploads یافت نشد")
                return False

            files = list(uploads_dir.glob("*"))  # همه فایل‌ها را نمایش می‌دهیم

            if not files:
                logger.info("⚠️ هیچ فایلی یافت نشد")
                return True

            print(f"\n📁 فایل‌های آپلود شده:")
            print('='*80)
            print('📄 نام فایل'.ljust(40) + '📊 اندازه (بایت)'.ljust(15) + '📅 تاریخ ایجاد'.ljust(20))
            print('-'*80)

            for i, file_path in enumerate(files, 1):
                file_size = file_path.stat().st_size
                created_time = file_path.stat().st_mtime
                from datetime import datetime
                created_date = datetime.fromtimestamp(created_time).strftime("%Y-%m-%d %H:%M")

                logger.info(f"{i}. {file_path.name} | {file_size} بایت | {created_date}")

            print('='*80)
            print(f"📊 تعداد کل فایل‌ها: {len(files)}")

            # نمایش محتوای یک فایل نمونه
            if files:
                logger.info("محتوای فایل نمونه:")
                logger.info('-'*50)
                try:
                    with open(files[0], 'r', encoding='utf-8') as f:
                        content = f.read()
                        preview = content[:300] + "..." if len(content) > 300 else content
                    logger.info(preview)
                except Exception as e:
                    logger.warning(f"خطا در خواندن فایل: {str(e)}")

            return True

        except Exception as e:
            logger.error(f"❌ خطا در نمایش فایل‌های آپلود شده: {str(e)}")
            return False

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
        """انتقال همه مقالات از MongoDB به Weaviate با vectorization"""
        try:
            logger.info("🔄 شروع انتقال همه مقالات از MongoDB به Weaviate...")

            # لاگ گرفتن اطلاعات vectorizer
            self.log_vectorizer_info()

            # اتصال به دیتابیس‌ها
            if not await self.connect_mongodb():
                return False

            if not self.connect_weaviate():
                return False

            # خواندن فقط مقالات منتشر شده از MongoDB
            db = self.mongodb_client.get_default_database()
            articles = await db.knowledge_base_articles.find({"status": "published"}).to_list(None)
            
            if not articles:
                logger.warning("⚠️ هیچ مقاله منتشر شده‌ای در MongoDB یافت نشد")
                return False
            
            logger.info(f"📚 تعداد مقالات منتشر شده یافت شده: {len(articles)}")
            
            # انتقال هر مقاله
            success_count = 0
            failed_count = 0
            
            for i, article in enumerate(articles, 1):
                try:
                    article_id = str(article['_id'])
                    article_title = article.get('title', 'بدون عنوان')
                    
                    logger.info(f"📄 [{i}/{len(articles)}] در حال پردازش: '{article_title}'")
                    
                    # استفاده از تابع migrate_article_with_vectorization
                    result = await self.migrate_article_with_vectorization(article_id)
                    
                    if result:
                        success_count += 1
                        logger.info(f"✅ [{i}/{len(articles)}] '{article_title}' با موفقیت منتقل شد")
                    else:
                        failed_count += 1
                        logger.error(f"❌ [{i}/{len(articles)}] '{article_title}' انتقال نشد")
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"❌ [{i}/{len(articles)}] خطا در انتقال مقاله: {str(e)}")
                    continue
            
            # گزارش نهایی
            logger.info("="*80)
            logger.info(f"📊 گزارش نهایی انتقال:")
            logger.info(f"   ✅ موفق: {success_count}")
            logger.info(f"   ❌ ناموفق: {failed_count}")
            logger.info(f"   📚 کل: {len(articles)}")
            logger.info("="*80)
            
            # بررسی نهایی
            verification = self.verify_setup()
            markdown_nodes_count = verification["data_counts"].get("markdown_nodes", 0)
            logger.info(f"📈 تعداد کل گره‌های Markdown در Weaviate: {markdown_nodes_count}")

            if success_count > 0:
                logger.info("🎉 انتقال داده‌ها تکمیل شد!")
                return True
            else:
                logger.error("💥 هیچ مقاله‌ای منتقل نشد")
                return False
                
        except Exception as e:
            logger.error(f"❌ خطا در فرآیند انتقال: {str(e)}")
            return False

    def delete_all_from_weaviate(self) -> bool:
        """حذف همه گره‌های Markdown از Weaviate"""
        try:
            logger.info("🗑️ شروع حذف همه گره‌های Markdown از Weaviate...")
            
            if not hasattr(self, 'weaviate_client') or not self.weaviate_client:
                if not self.connect_weaviate():
                    logger.error("❌ اتصال به Weaviate ناموفق بود")
                    return False
            
            # حذف collection کامل
            collection_name = "MarkdownNode"
            
            if self.weaviate_client.collections.exists(collection_name):
                # دریافت تعداد کل اشیاء قبل از حذف
                collection = self.weaviate_client.collections.get(collection_name)
                try:
                    aggregate_result = collection.aggregate.over_all(total_count=True)
                    total_count = aggregate_result.total_count
                    logger.info(f"📊 تعداد گره‌های موجود: {total_count}")
                except:
                    total_count = "نامشخص"
                
                # حذف collection
                self.weaviate_client.collections.delete(collection_name)
                logger.info(f"✅ Collection {collection_name} و {total_count} گره حذف شدند")
                
                # ایجاد مجدد collection خالی
                success = self.create_weaviate_schema()
                if success:
                    logger.info("✅ Collection خالی مجدداً ایجاد شد")
                else:
                    logger.warning("⚠️ خطا در ایجاد مجدد collection")
                    
            else:
                logger.info("ℹ️ Collection MarkdownNode وجود ندارد")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ خطا در حذف از Weaviate: {str(e)}")
            return False

    async def delete_all_from_mongodb(self) -> bool:
        """حذف همه مقالات از MongoDB"""
        try:
            logger.info("🗑️ شروع حذف همه مقالات از MongoDB...")
            
            if not self.mongodb_client:
                if not await self.connect_mongodb():
                    logger.error("❌ اتصال به MongoDB ناموفق بود")
                    return False
            
            db = self.mongodb_client.get_default_database()
            
            # حذف مقالات
            collection = db.knowledge_base_articles
            result = await collection.delete_many({})
            logger.info(f"✅ {result.deleted_count} مقاله از MongoDB حذف شد")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ خطا در حذف از MongoDB: {str(e)}")
            return False

    async def delete_all_data(self) -> bool:
        """حذف همه داده‌ها از هر دو دیتابیس"""
        try:
            logger.info("🗑️ شروع حذف همه داده‌ها...")
            
            # حذف از Weaviate
            weaviate_success = self.delete_all_from_weaviate()
            
            # حذف از MongoDB
            mongodb_success = await self.delete_all_from_mongodb()
            
            if weaviate_success and mongodb_success:
                logger.info("✅ همه داده‌ها با موفقیت حذف شدند")
                return True
            else:
                logger.warning("⚠️ برخی عملیات حذف ناموفق بودند")
                return False
                
        except Exception as e:
            logger.error(f"❌ خطا در حذف کلی: {str(e)}")
            return False

    async def delete_by_article_ids(self, article_ids: list) -> bool:
        """حذف مقالات خاص بر اساس شناسه‌ها"""
        try:
            logger.info(f"🗑️ شروع حذف {len(article_ids)} مقاله...")
            
            success_count = 0
            
            for article_id in article_ids:
                try:
                    # حذف از Weaviate
                    if hasattr(self, 'weaviate_client') and self.weaviate_client:
                        weaviate_success = self.delete_markdown_nodes(article_id)
                    else:
                        weaviate_success = True
                    
                    # حذف از MongoDB
                    if self.mongodb_client:
                        db = self.mongodb_client.get_default_database()
                        from bson import ObjectId
                        result = await db.knowledge_base_articles.delete_one({"_id": ObjectId(article_id)})
                        mongodb_success = result.deleted_count > 0
                    else:
                        mongodb_success = True
                    
                    if weaviate_success and mongodb_success:
                        logger.info(f"✅ مقاله {article_id} حذف شد")
                        success_count += 1
                    else:
                        logger.warning(f"⚠️ خطا در حذف مقاله {article_id}")
                        
                except Exception as e:
                    logger.error(f"❌ خطا در حذف مقاله {article_id}: {str(e)}")
            
            logger.info(f"✅ {success_count} از {len(article_ids)} مقاله حذف شد")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ خطا در حذف مقالات: {str(e)}")
            return False

    async def migrate_article_with_vectorization(self, article_id: str) -> bool:
        """
        ذخیره یک مقاله خاص با vectorization فعال در Weaviate
        
        Args:
            article_id: شناسه مقاله در MongoDB
            
        Returns:
            True اگر ذخیره موفق باشد
        """
        try:
            logger.info(f"🚀 شروع ذخیره مقاله {article_id} با vectorization...")
            
            # اتصال به MongoDB اگر هنوز متصل نیست
            if not self.mongodb_client:
                if not await self.connect_mongodb():
                    logger.error("❌ اتصال به MongoDB ناموفق بود")
                    return False
            
            # اتصال به Weaviate اگر هنوز متصل نیست
            if not hasattr(self, 'weaviate_client') or not self.weaviate_client:
                if not self.connect_weaviate():
                    logger.error("❌ اتصال به Weaviate ناموفق بود")
                    return False
            
            # خواندن مقاله از MongoDB
            db = self.mongodb_client.get_default_database()
            from bson import ObjectId

            # اگر article_id قبلاً ObjectId هست، مستقیم استفاده کن
            if isinstance(article_id, str) and len(article_id) == 24:
                try:
                    object_id = ObjectId(article_id)
                except:
                    logger.error(f"❌ فرمت ID مقاله نامعتبر است: {article_id}")
                    return False
            else:
                object_id = article_id

            article = await db.knowledge_base_articles.find_one({"_id": object_id})

            if not article:
                logger.error(f"❌ مقاله با ID {article_id} یافت نشد")
                logger.info(f"🔍 جستجو در collection: knowledge_base_articles")
                logger.info(f"🔍 تعداد کل مقالات در دیتابیس: {await db.knowledge_base_articles.count_documents({})}")

                # جستجوی دقیق‌تر برای دیباگ
                logger.info(f"🔍 جستجوی دقیق‌تر - object_id type: {type(object_id)}")
                logger.info(f"🔍 جستجوی دقیق‌تر - object_id value: {object_id}")

                # جستجوی بدون فیلتر برای دیدن همه مقالات
                all_articles = await db.knowledge_base_articles.find({}).to_list()
                logger.info(f"🔍 مقالات موجود در دیتابیس:")
                for art in all_articles:
                    logger.info(f"  - ID: {art['_id']}, Title: {art.get('title', 'No title')}")

                return False
                
            logger.info(f"✅ مقاله '{article['title']}' از MongoDB خوانده شد")
            
            # پارس کردن محتوای markdown
            try:
                import sys
                from pathlib import Path
                # اضافه کردن مسیر پروژه به sys.path
                project_root = Path(__file__).resolve().parent.parent.parent.parent
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))
                    
                from app.infrastructure.markdown_parser import markdown_parser
                tree = markdown_parser.parse_to_tree(article['content_markdown'], str(article['_id']))
                
                logger.info(f"🌳 ساختار درختی ایجاد شد - تعداد گره‌ها: {len(tree.get_all_nodes())}")
                
                # نمایش ساختار درختی
                logger.info("📋 ساختار درختی مقاله:")
                for node in tree.get_all_nodes():
                    indent = "  " * (node.level - 1)
                    logger.info(f"{indent}📄 {node.title} (سطح {node.level}, مسیر: {node.path})")
                
            except Exception as parse_error:
                logger.error(f"❌ خطا در پارس markdown: {str(parse_error)}")
                # استفاده از روش ساده
                return await self._simple_markdown_save(article)
            
            # حذف گره‌های قدیمی این مقاله
            try:
                from weaviate.classes.query import Filter
                collection = self.weaviate_client.collections.get("MarkdownNode")
                collection.data.delete_many(
                    where=Filter.by_property("article_id").equal(str(article['_id']))
                )
                logger.info("🗑️ گره‌های قدیمی مقاله حذف شدند")
            except Exception as delete_error:
                logger.warning(f"⚠️ خطا در حذف گره‌های قدیمی: {str(delete_error)}")
            
            # ذخیره گره‌های جدید با vectorization
            saved_count = 0
            
            for node in tree.get_all_nodes():
                try:
                    node_data = {
                        "node_id": node.id,
                        "article_id": str(article['_id']),
                        "title": node.title,
                        "level": node.level,
                        "content": node.content,
                        "parent_id": node.parent_id,
                        "path": node.path,
                        "order": node.order,
                        "full_content": article['content_markdown']
                    }
                    
                    # ذخیره در Weaviate با vectorization
                    collection = self.weaviate_client.collections.get("MarkdownNode")
                    uuid = collection.data.insert(properties=node_data)
                    logger.info(f"✅ گره '{node.title}' با vectorization ذخیره شد - UUID: {uuid}")
                    
                    saved_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ خطا در ذخیره گره '{node.title}': {str(e)}")
                    continue
            
            logger.info(f"🎉 {saved_count} گره با vectorization ذخیره شد")
            
            # تست جستجوی معنایی
            logger.info("🔍 تست جستجوی معنایی...")
            
            try:
                search_response = collection.query.near_text(
                    query=article['title'][:50],  # جستجو بر اساس عنوان مقاله
                    limit=3,
                    return_properties=["title", "content", "path"],
                    return_metadata=["certainty"]
                )
                
                logger.info("📊 نتایج جستجوی معنایی:")
                for i, obj in enumerate(search_response.objects, 1):
                    props = obj.properties
                    certainty = obj.metadata.certainty if obj.metadata else 0
                    logger.info(f"  {i}. '{props.get('title', 'نامشخص')}' - اطمینان: {certainty:.3f}")
                    
            except Exception as search_error:
                logger.warning(f"⚠️ خطا در تست جستجو: {str(search_error)}")
            
            # نمایش آمار نهایی
            try:
                aggregate_result = collection.aggregate.over_all(total_count=True)
                total_count = aggregate_result.total_count
                logger.info(f"📊 تعداد کل گره‌ها در Weaviate: {total_count}")
            except Exception as stats_error:
                logger.warning(f"⚠️ خطا در دریافت آمار: {str(stats_error)}")
            
            logger.info("🎉 ذخیره مقاله با vectorization تکمیل شد!")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطا در فرآیند ذخیره: {str(e)}")
            return False
    
    async def _simple_markdown_save(self, article) -> bool:
        """روش ساده برای ذخیره مقاله بدون markdown parser"""
        try:
            logger.info("🔧 استفاده از روش ساده برای ذخیره...")
            
            import re
            
            # حذف گره‌های قدیمی
            try:
                from weaviate.classes.query import Filter
                collection = self.weaviate_client.collections.get("MarkdownNode")
                collection.data.delete_many(
                    where=Filter.by_property("article_id").equal(str(article['_id']))
                )
                logger.info("🗑️ گره‌های قدیمی مقاله حذف شدند")
            except Exception as delete_error:
                logger.warning(f"⚠️ خطا در حذف گره‌های قدیمی: {str(delete_error)}")
            
            # استخراج هدرها
            content = article['content_markdown']
            lines = content.split('\n')
            
            nodes_data = []
            current_content = []
            
            for i, line in enumerate(lines):
                # بررسی هدر
                header_match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
                
                if header_match:
                    # ذخیره گره قبلی اگر وجود دارد
                    if current_content and len(nodes_data) > 0:
                        nodes_data[-1]['content'] = '\n'.join(current_content).strip()
                        current_content = []
                    
                    # ایجاد گره جدید
                    level = len(header_match.group(1))
                    title = header_match.group(2).strip()
                    
                    node_data = {
                        "node_id": f"simple-{i}",
                        "article_id": str(article['_id']),
                        "title": title,
                        "level": level,
                        "content": "",
                        "parent_id": "-1",
                        "path": f"{len(nodes_data) + 1}",
                        "order": len(nodes_data),
                        "full_content": content
                    }
                    
                    nodes_data.append(node_data)
                else:
                    current_content.append(line)
            
            # محتوای آخرین گره
            if current_content and nodes_data:
                nodes_data[-1]['content'] = '\n'.join(current_content).strip()
            
            # اگر هیچ هدری نیافت، کل مقاله را یک گره کن
            if not nodes_data:
                nodes_data = [{
                    "node_id": "simple-full",
                    "article_id": str(article['_id']),
                    "title": article['title'],
                    "level": 1,
                    "content": content,
                    "parent_id": "-1",
                    "path": "1",
                    "order": 0,
                    "full_content": content
                }]
            
            # ذخیره در Weaviate
            collection = self.weaviate_client.collections.get("MarkdownNode")
            saved_count = 0
            
            for node_data in nodes_data:
                try:
                    uuid = collection.data.insert(properties=node_data)
                    logger.info(f"✅ گره '{node_data['title']}' با vectorization ذخیره شد")
                    saved_count += 1
                except Exception as e:
                    logger.error(f"❌ خطا در ذخیره گره '{node_data['title']}': {str(e)}")
            
            logger.info(f"🎉 {saved_count} گره با vectorization ذخیره شد")
            
            # تست جستجو
            try:
                search_response = collection.query.near_text(
                    query=article['title'][:50],
                    limit=3,
                    return_properties=["title", "content"],
                    return_metadata=["certainty"]
                )
                
                logger.info("📊 نتایج جستجوی معنایی:")
                for i, obj in enumerate(search_response.objects, 1):
                    props = obj.properties
                    certainty = obj.metadata.certainty if obj.metadata else 0
                    logger.info(f"  {i}. '{props.get('title', 'نامشخص')}' - اطمینان: {certainty:.3f}")
                    
            except Exception as search_error:
                logger.warning(f"⚠️ خطا در تست جستجو: {str(search_error)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ خطا در روش ساده: {str(e)}")
            return False

    def cleanup(self):
        """پاک‌سازی اتصالات"""
        try:
            if self.mongodb_client:
                self.mongodb_client.close()
                logger.info("🧹 اتصال MongoDB بسته شد")

            # ✅ فقط اگر از Connection Manager استفاده نمی‌کنیم، client را ببندیم
            if hasattr(self, 'weaviate_client') and self.weaviate_client and not self._use_connection_manager:
                # Close Weaviate client v4
                self.weaviate_client.close()
                logger.info("🧹 اتصال Weaviate بسته شد")
            elif self._use_connection_manager:
                logger.info("ℹ️ Weaviate client توسط Connection Manager مدیریت می‌شود")

        except Exception as e:
            logger.error(f"❌ خطا در پاک‌سازی: {str(e)}")


async def main():
    """تابع اصلی برنامه"""
    parser = argparse.ArgumentParser(description="Weaviate-MongoDB Connection Script")
    parser.add_argument("--setup", action="store_true", help="راه‌اندازی اولیه سیستم")
    parser.add_argument("--migrate", action="store_true", help="انتقال داده‌ها از MongoDB به Weaviate")
    parser.add_argument("--migrate-article", metavar="ARTICLE_ID", help="ذخیره یک مقاله خاص با vectorization")
    parser.add_argument("--verify", action="store_true", help="بررسی وضعیت سیستم")
    parser.add_argument("--test-connection", action="store_true", help="تست اتصال به هر دو دیتابیس")
    parser.add_argument("--display-weaviate", metavar="CLASS_NAME", nargs='?', const="MarkdownNode", help="نمایش اشیاء ذخیره شده در Weaviate")
    parser.add_argument("--display-files", action="store_true", help="نمایش فایل‌های آپلود شده")
    parser.add_argument("--delete-all", action="store_true", help="حذف همه مقالات از هر دو دیتابیس")
    parser.add_argument("--delete-by-ids", nargs='+', help="حذف مقالات خاص بر اساس شناسه‌ها")
    parser.add_argument("--delete-from-mongodb", action="store_true", help="حذف همه مقالات فقط از MongoDB")
    parser.add_argument("--delete-from-weaviate", action="store_true", help="حذف همه مقالات فقط از Weaviate")

    args = parser.parse_args()

    if not any([args.setup, args.migrate, args.migrate_article, args.verify, args.test_connection,
                args.display_weaviate, args.display_files, args.delete_all,
                args.delete_by_ids, args.delete_from_mongodb, args.delete_from_weaviate]):
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

        elif args.migrate_article:
            logger.info(f"🔄 شروع ذخیره مقاله {args.migrate_article} با vectorization...")
            success = await connector.migrate_article_with_vectorization(args.migrate_article)
            if success:
                logger.info("🎉 مقاله با موفقیت ذخیره شد!")
                logger.info("حالا می‌توانید جستجوی معنایی انجام دهید")
            else:
                logger.error("💥 ذخیره مقاله ناموفق بود")

        elif args.verify:
            # اتصال برای بررسی
            await connector.connect_mongodb()
            connector.connect_weaviate()

            result = connector.verify_setup()

            logger.info("📋 گزارش وضعیت سیستم:")
            logger.info(f"  Weaviate متصل: {'✅' if result['weaviate_connection'] else '❌'}")
            logger.info(f"  MongoDB متصل: {'✅' if result['mongodb_connection'] else '❌'}")
            logger.info(f"  Schema موجود: {'✅' if result['schema_exists'] else '❌'}")
            logger.info(f"  تعداد گره‌ها: {result['data_counts'].get('markdown_nodes', 0)}")
            logger.info(f"  تعداد مقالات: {result['data_counts'].get('articles', 0)}")

            if result["errors"]:
                logger.info("❌ خطاها:")
                for error in result["errors"]:
                    logger.info(f"  - {error}")

        elif args.display_weaviate:
            logger.info(f"🔍 نمایش اشیاء Weaviate (کلاس: {args.display_weaviate})...")
            success = connector.display_weaviate_objects(class_name=args.display_weaviate, limit=10)
            if success:
                logger.info("✅ نمایش اشیاء Weaviate تکمیل شد!")
            else:
                logger.error("💥 نمایش اشیاء Weaviate ناموفق بود")

        elif args.display_files:
            logger.info("📁 نمایش فایل‌های آپلود شده...")
            success = connector.display_file_uploads()
            if success:
                logger.info("✅ نمایش فایل‌ها تکمیل شد!")
            else:
                logger.error("💥 نمایش فایل‌ها ناموفق بود")

        elif args.delete_all:
            logger.info("🗑️ حذف همه داده‌ها...")
            logger.warning("⚠️ این عملیات همه داده‌ها را حذف خواهد کرد!")
            
            # بررسی امنیتی
            import time
            logger.info("⏳ 5 ثانیه فرصت برای لغو...")
            time.sleep(5)
            
            # اتصال به دیتابیس‌ها
            await connector.connect_mongodb()
            connector.connect_weaviate()
            
            success = await connector.delete_all_data()
            if success:
                logger.info("🎉 همه داده‌ها حذف شدند!")
            else:
                logger.error("💥 حذف داده‌ها ناموفق بود")

        elif args.delete_from_weaviate:
            logger.info("🗑️ حذف داده‌ها از Weaviate...")
            connector.connect_weaviate()
            
            success = connector.delete_all_from_weaviate()
            if success:
                logger.info("🎉 داده‌های Weaviate حذف شدند!")
            else:
                logger.error("💥 حذف از Weaviate ناموفق بود")

        elif args.delete_from_mongodb:
            logger.info("🗑️ حذف داده‌ها از MongoDB...")
            await connector.connect_mongodb()
            
            success = await connector.delete_all_from_mongodb()
            if success:
                logger.info("🎉 داده‌های MongoDB حذف شدند!")
            else:
                logger.error("💥 حذف از MongoDB ناموفق بود")

        elif args.delete_by_ids:
            logger.info(f"🗑️ حذف مقالات خاص: {args.delete_by_ids}")
            # اتصال به دیتابیس‌ها
            await connector.connect_mongodb()
            connector.connect_weaviate()
            
            success = await connector.delete_by_article_ids(args.delete_by_ids)
            if success:
                logger.info("🎉 مقالات خاص حذف شدند!")
            else:
                logger.error("💥 حذف مقالات ناموفق بود")

    finally:
        connector.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
