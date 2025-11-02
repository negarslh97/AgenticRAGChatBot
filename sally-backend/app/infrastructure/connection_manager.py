"""
Connection Manager - مدیریت اتصالات به Weaviate و MongoDB
========================================================

این ماژول برای مدیریت متمرکز و بهینه اتصالات به دیتابیس‌ها طراحی شده است.

ویژگی‌ها:
- Connection Pooling
- Auto cleanup با context manager
- Resource tracking
- Memory monitoring
"""

import weaviate
import tracemalloc
from typing import Optional
from contextlib import asynccontextmanager, contextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# فعال‌سازی tracemalloc برای شناسایی نشت حافظه
if settings.debug:
    tracemalloc.start()
    logger.info("🔍 tracemalloc activated for memory leak detection")


class WeaviateConnectionManager:
    """
    مدیریت اتصالات به Weaviate با Connection Pooling
    """
    
    _instance = None
    _client = None
    _connection_count = 0
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_client(self) -> weaviate.WeaviateClient:
        """
        دریافت یا ایجاد client (Singleton Pattern)
        """
        if self._client is None or not self._is_ready():
            self._create_client()
        
        self._connection_count += 1
        logger.debug(f"📊 Weaviate connections: {self._connection_count}")
        
        return self._client
    
    def _create_client(self):
        """ایجاد client جدید"""
        try:
            logger.info("🔌 Creating new Weaviate client...")
            
            weaviate_url = settings.weaviate_url_loaded or "http://localhost:8080"
            weaviate_api_key = settings.weaviate_api_key_loaded
            
            from urllib.parse import urlparse
            parsed_url = urlparse(weaviate_url)
            http_host = parsed_url.hostname or "localhost"
            http_port = parsed_url.port or 8080
            http_secure = parsed_url.scheme == "https"
            
            if weaviate_api_key:
                from weaviate.classes.init import Auth
                self._client = weaviate.connect_to_custom(
                    http_host=http_host,
                    http_port=http_port,
                    http_secure=http_secure,
                    grpc_host=http_host,
                    grpc_port=50051,
                    grpc_secure=http_secure,
                    auth_credentials=Auth.api_key(weaviate_api_key)
                )
            else:
                self._client = weaviate.connect_to_custom(
                    http_host=http_host,
                    http_port=http_port,
                    http_secure=http_secure,
                    grpc_host=http_host,
                    grpc_port=50051,
                    grpc_secure=http_secure
                )
            
            if self._client.is_ready():
                logger.info("✅ Weaviate client created and ready")
            else:
                logger.warning("⚠️ Weaviate client created but not ready")
                
        except Exception as e:
            logger.error(f"❌ Error creating Weaviate client: {e}")
            raise
    
    def _is_ready(self) -> bool:
        """بررسی وضعیت client"""
        try:
            return self._client is not None and self._client.is_ready()
        except:
            return False
    
    def close_client(self):
        """بستن client"""
        if self._client is not None:
            try:
                self._client.close()
                logger.info("🧹 Weaviate client closed")
                self._client = None
                self._connection_count = 0
            except Exception as e:
                logger.error(f"❌ Error closing Weaviate client: {e}")
    
    def release(self):
        """کاهش تعداد اتصالات فعال"""
        self._connection_count = max(0, self._connection_count - 1)
        logger.debug(f"📉 Weaviate connections: {self._connection_count}")
        
        # اگر اتصالی فعال نیست، client را ببند
        if self._connection_count == 0:
            self.close_client()
    
    def get_stats(self) -> dict:
        """دریافت آمار اتصالات"""
        return {
            "client_exists": self._client is not None,
            "is_ready": self._is_ready(),
            "connection_count": self._connection_count
        }


@contextmanager
def weaviate_client():
    """
    Context manager برای استفاده امن از Weaviate client
    
    Usage:
        with weaviate_client() as client:
            # استفاده از client
            results = client.collections.get("MyCollection").query.fetch_objects()
    """
    manager = WeaviateConnectionManager()
    client = manager.get_client()
    
    try:
        yield client
    finally:
        manager.release()
        logger.debug("🔓 Weaviate client released")


class MongoDBConnectionManager:
    """
    مدیریت اتصالات به MongoDB با Connection Pooling
    """
    
    _instance = None
    _client: Optional[AsyncIOMotorClient] = None
    _connection_count = 0
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_client(self) -> AsyncIOMotorClient:
        """دریافت یا ایجاد client"""
        if self._client is None:
            self._create_client()
        
        self._connection_count += 1
        logger.debug(f"📊 MongoDB connections: {self._connection_count}")
        
        return self._client
    
    def _create_client(self):
        """ایجاد client جدید"""
        try:
            logger.info("🔌 Creating new MongoDB client...")
            
            # استفاده از connection pooling settings
            self._client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                maxPoolSize=50,  # تعداد حداکثر اتصالات همزمان
                minPoolSize=10,  # تعداد حداقل اتصالات
                maxIdleTimeMS=45000,  # زمان بیکاری قبل از بستن
                serverSelectionTimeoutMS=5000,  # timeout برای انتخاب server
                connectTimeoutMS=10000  # timeout برای اتصال
            )
            
            logger.info("✅ MongoDB client created with connection pooling")
            
        except Exception as e:
            logger.error(f"❌ Error creating MongoDB client: {e}")
            raise
    
    def close_client(self):
        """بستن client"""
        if self._client is not None:
            try:
                self._client.close()
                logger.info("🧹 MongoDB client closed")
                self._client = None
                self._connection_count = 0
            except Exception as e:
                logger.error(f"❌ Error closing MongoDB client: {e}")
    
    def release(self):
        """کاهش تعداد اتصالات فعال"""
        self._connection_count = max(0, self._connection_count - 1)
        logger.debug(f"📉 MongoDB connections: {self._connection_count}")
    
    def get_stats(self) -> dict:
        """دریافت آمار اتصالات"""
        return {
            "client_exists": self._client is not None,
            "connection_count": self._connection_count
        }


@asynccontextmanager
async def mongodb_client():
    """
    Async context manager برای استفاده امن از MongoDB client
    
    Usage:
        async with mongodb_client() as client:
            db = client.get_default_database()
            # استفاده از database
    """
    manager = MongoDBConnectionManager()
    client = manager.get_client()
    
    try:
        yield client
    finally:
        manager.release()
        logger.debug("🔓 MongoDB client released")


class ResourceMonitor:
    """
    نظارت بر مصرف منابع و اتصالات
    """
    
    @staticmethod
    def get_memory_usage() -> dict:
        """دریافت اطلاعات مصرف حافظه"""
        if not tracemalloc.is_tracing():
            return {"error": "tracemalloc not active"}
        
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        return {
            "current_size_mb": sum(stat.size for stat in top_stats) / (1024 * 1024),
            "peak_size_mb": tracemalloc.get_traced_memory()[1] / (1024 * 1024),
            "top_allocations": [
                {
                    "file": str(stat.traceback),
                    "size_mb": stat.size / (1024 * 1024),
                    "count": stat.count
                }
                for stat in top_stats[:5]
            ]
        }
    
    @staticmethod
    def get_connection_stats() -> dict:
        """دریافت آمار همه اتصالات"""
        weaviate_mgr = WeaviateConnectionManager()
        mongodb_mgr = MongoDBConnectionManager()
        
        return {
            "weaviate": weaviate_mgr.get_stats(),
            "mongodb": mongodb_mgr.get_stats(),
            "memory": ResourceMonitor.get_memory_usage()
        }
    
    @staticmethod
    def check_thresholds():
        """بررسی آستانه‌های هشدار"""
        stats = ResourceMonitor.get_connection_stats()
        
        warnings = []
        
        # بررسی تعداد اتصالات Weaviate
        if stats["weaviate"]["connection_count"] > 10:
            warnings.append(f"⚠️ High Weaviate connections: {stats['weaviate']['connection_count']}")
        
        # بررسی تعداد اتصالات MongoDB
        if stats["mongodb"]["connection_count"] > 50:
            warnings.append(f"⚠️ High MongoDB connections: {stats['mongodb']['connection_count']}")
        
        # بررسی مصرف حافظه
        if "current_size_mb" in stats["memory"]:
            if stats["memory"]["current_size_mb"] > 500:
                warnings.append(f"⚠️ High memory usage: {stats['memory']['current_size_mb']:.2f} MB")
        
        if warnings:
            for warning in warnings:
                logger.warning(warning)
        
        return warnings


def cleanup_all_connections():
    """
    بستن همه اتصالات (برای استفاده در shutdown)
    """
    logger.info("🧹 Cleaning up all connections...")
    
    weaviate_mgr = WeaviateConnectionManager()
    weaviate_mgr.close_client()
    
    mongodb_mgr = MongoDBConnectionManager()
    mongodb_mgr.close_client()
    
    if tracemalloc.is_tracing():
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        logger.info("📊 Final memory snapshot:")
        for stat in top_stats[:3]:
            logger.info(f"   {stat}")
        
        tracemalloc.stop()
    
    logger.info("✅ All connections cleaned up")


# برای استفاده در FastAPI lifespan
async def startup_connections():
    """راه‌اندازی اتصالات در startup"""
    logger.info("🚀 Initializing connection managers...")
    
    # Pre-initialize clients
    weaviate_mgr = WeaviateConnectionManager()
    mongodb_mgr = MongoDBConnectionManager()
    
    logger.info("✅ Connection managers ready")


async def shutdown_connections():
    """بستن اتصالات در shutdown"""
    cleanup_all_connections()




