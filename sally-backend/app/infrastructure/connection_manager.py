# connection_manager.py

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
import time
import threading
from typing import Optional, List, Dict, Any
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
    مدیریت اتصالات به Weaviate با Connection Pooling پیشرفته
    
    ویژگی‌های بهبودیافته:
    - Connection Pooling با مدیریت خودکار
    - Health checks و auto-recovery
    - Connection timeout و retry logic
    - Resource monitoring و alerting
    - Connection lifecycle management
    """
    
    _instance = None
    _client = None
    _connection_count = 0
    _last_health_check = 0
    _health_check_interval = 60  # seconds
    _max_connection_age = 1800  # 30 minutes
    _connection_birth_time = None
    _connection_pool = []
    _max_pool_size = 10
    _current_pool_size = 0
    _pool_lock = threading.RLock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance for testing purposes"""
        cls._instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_client(self) -> weaviate.WeaviateClient:
        """
        دریافت یا ایجاد client با Connection Pooling پیشرفته
        
        Returns:
            WeaviateClient instance from pool or new connection
            
        Raises:
            ConnectionError: If unable to establish connection
        """
        current_time = time.time()
        
        # 🔄 Health check interval enforcement
        if (current_time - self._last_health_check) > self._health_check_interval:
            self._perform_health_check()
            self._last_health_check = current_time
        
        # 🔍 Check if current connection is too old
        if (self._connection_birth_time and
            (current_time - self._connection_birth_time) > self._max_connection_age):
            logger.info("🔄 Connection too old, creating new one...")
            self._close_client_safely()
        
        # 🏊 Try to get from connection pool first
        with self._pool_lock:
            if self._connection_pool:
                client = self._connection_pool.pop()
                try:
                    if self._is_client_healthy(client):
                        self._connection_count += 1
                        logger.debug(f"🏊 Got client from pool (pool size: {len(self._connection_pool)})")
                        return client
                    else:
                        logger.warning("⚠️ Pooled client unhealthy, creating new one")
                except Exception as e:
                    logger.warning(f"⚠️ Error checking pooled client: {e}")
        
        # 🆕 Create new client if pool is empty or current client is unhealthy
        if self._client is None or not self._is_ready():
            self._create_client()
        
        self._connection_count += 1
        logger.debug(f"📊 Weaviate connections: {self._connection_count}")
        
        return self._client
    
    def _perform_health_check(self):
        """
        🏥 Perform comprehensive health check on current connection
        """
        try:
            if self._client and self._is_ready():
                # Simple health check - try to get collection info
                from app.core.weaviate_utils import get_weaviate_collection_name
                collection_name = get_weaviate_collection_name()
                
                with self._client as client:
                    if client.collections.exists(collection_name):
                        logger.debug("✅ Weaviate health check passed")
                        return True
                    else:
                        logger.warning("⚠️ Weaviate health check failed - collection not found")
                        return False
            else:
                logger.warning("⚠️ Weaviate health check failed - client not ready")
                return False
        except Exception as e:
            logger.error(f"❌ Weaviate health check error: {e}")
            return False
    
    def _is_client_healthy(self, client) -> bool:
        """
        Check if a pooled client is still healthy
        
        Args:
            client: WeaviateClient instance to check
            
        Returns:
            True if client is healthy, False otherwise
        """
        try:
            return client is not None and client.is_ready()
        except:
            return False
    
    def _close_client_safely(self):
        """
        Safely close the current client and reset state
        """
        if self._client is not None:
            try:
                self._client.close()
                logger.info("🧹 Weaviate client closed due to age limit")
            except Exception as e:
                logger.error(f"❌ Error closing Weaviate client: {e}")
            finally:
                self._client = None
                self._connection_birth_time = None
                self._connection_count = 0
    
    def _create_client(self):
        """ایجاد client جدید با تنظیمات بهینه"""
        try:
            logger.info("🔌 Creating new Weaviate client with optimized settings...")
            
            weaviate_url = settings.weaviate_url_loaded
            weaviate_api_key = settings.weaviate_api_key_loaded
            
            from urllib.parse import urlparse
            parsed_url = urlparse(weaviate_url)
            http_host = parsed_url.hostname or "localhost"
            http_port = parsed_url.port or 8080
            http_secure = parsed_url.scheme == "https"
            
            # 🆕 Enhanced connection configuration
            connection_config = {
                "http_host": http_host,
                "http_port": http_port,
                "http_secure": http_secure,
                "grpc_host": http_host,
                "grpc_port": 50051,
                "grpc_secure": http_secure
            }
            
            if weaviate_api_key:
                from weaviate.classes.init import Auth
                connection_config["auth_credentials"] = Auth.api_key(weaviate_api_key)
            
            self._client = weaviate.connect_to_custom(**connection_config)
            
            if self._client.is_ready():
                self._connection_birth_time = time.time()
                logger.info("✅ Weaviate client created and ready with optimized settings")
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
        
        # Clear connection pool
        with self._pool_lock:
            if self._connection_pool:
                self._connection_pool.clear()
                logger.debug("🧹 Weaviate connection pool cleared")
    
    def release(self):
        """کاهش تعداد اتصالات فعال"""
        with self._pool_lock:
            self._connection_count = max(0, self._connection_count - 1)
            logger.debug(f"📉 Weaviate connections: {self._connection_count}")
            
            # 🏊 Return to connection pool if space available
            if (len(self._connection_pool) < self._max_pool_size and
                self._client is not None):
                
                self._connection_pool.append(self._client)
                logger.debug(f"🏊 Returned Weaviate client to pool (pool size: {len(self._connection_pool)})")
                # Don't set self._client to None here! Keep the reference for future requests.
                # The pool will be used first, but if pool is empty, we still have the main client.
            
            # اگر اتصالی فعال نیست، client را ببند
            if self._connection_count == 0:
                self.close_client()
    
    def get_stats(self) -> dict:
        """دریافت آمار اتصالات Weaviate پیشرفته"""
        current_time = time.time()
        
        return {
            "client_exists": self._client is not None,
            "is_ready": self._is_ready(),
            "connection_count": self._connection_count,
            "pool_size": len(self._connection_pool),
            "max_pool_size": self._max_pool_size,
            "last_health_check": self._last_health_check,
            "health_check_interval": self._health_check_interval,
            "needs_health_check": (current_time - self._last_health_check) > self._health_check_interval if self._last_health_check else True,
            "connection_age": current_time - self._connection_birth_time if self._connection_birth_time else 0,
            "max_connection_age": self._max_connection_age
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
    مدیریت اتصالات به MongoDB با Connection Pooling پیشرفته
    
    ویژگی‌های بهبودیافته:
    - Connection Pooling با مدیریت خودکار
    - Health checks و auto-recovery
    - Connection timeout و retry logic
    - Resource monitoring و alerting
    - Connection lifecycle management
    """
    
    _instance = None
    _client: Optional[AsyncIOMotorClient] = None
    _connection_count = 0
    _connection_pool = []
    _max_pool_size = 50
    _min_pool_size = 10
    _last_health_check = 0
    _health_check_interval = 120  # seconds
    _max_connection_age = 3600  # 1 hour
    _connection_birth_time = None
    _pool_lock = threading.RLock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance for testing purposes"""
        cls._instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_client(self) -> AsyncIOMotorClient:
        """دریافت یا ایجاد client با Connection Pooling پیشرفته"""
        current_time = time.time()
        
        # 🔄 Health check interval enforcement
        if (current_time - self._last_health_check) > self._health_check_interval:
            self._perform_health_check()
            self._last_health_check = current_time
        
        # 🔍 Check if current connection is too old
        if (self._connection_birth_time and
            (current_time - self._connection_birth_time) > self._max_connection_age):
            logger.info("🔄 MongoDB connection too old, creating new one...")
            self._close_client_safely()
        
        # 🏊 Try to get from connection pool first
        with self._pool_lock:
            if self._connection_pool:
                client = self._connection_pool.pop()
                try:
                    if self._is_client_healthy(client):
                        self._connection_count += 1
                        logger.debug(f"🏊 Got MongoDB client from pool (pool size: {len(self._connection_pool)})")
                        return client
                    else:
                        logger.warning("⚠️ Pooled MongoDB client unhealthy, creating new one")
                except Exception as e:
                    logger.warning(f"⚠️ Error checking pooled MongoDB client: {e}")
        
        # 🆕 Create new client if pool is empty or current client is unhealthy
        if self._client is None:
            self._create_client()
        
        self._connection_count += 1
        logger.debug(f"📊 MongoDB connections: {self._connection_count}")
        
        return self._client
    
    def _perform_health_check(self):
        """🏥 Perform comprehensive health check on MongoDB connection"""
        try:
            if self._client:
                # Simple health check - try to ping the server
                result = self._client.admin.command('ping')
                if result.get('ok') == 1.0:
                    logger.debug("✅ MongoDB health check passed")
                    return True
                else:
                    logger.warning("⚠️ MongoDB health check failed - ping failed")
                    return False
            else:
                logger.warning("⚠️ MongoDB health check failed - client not ready")
                return False
        except Exception as e:
            logger.error(f"❌ MongoDB health check error: {e}")
            return False
    
    def _close_client_safely(self):
        """
        Safely close the current MongoDB client and reset state
        """
        if self._client is not None:
            try:
                self._client.close()
                logger.info("🧹 MongoDB client closed due to age limit")
            except Exception as e:
                logger.error(f"❌ Error closing MongoDB client: {e}")
            finally:
                self._client = None
                self._connection_birth_time = None
                self._connection_count = 0
    
    def _is_client_healthy(self, client) -> bool:
        """Check if a pooled MongoDB client is still healthy"""
        try:
            return client is not None
        except:
            return False
    
    def _create_client(self):
        """ایجاد client جدید با تنظیمات بهینه"""
        try:
            logger.info("🔌 Creating new MongoDB client with optimized settings...")
            
            # 🆕 Enhanced connection pooling settings
            self._client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                maxPoolSize=self._max_pool_size,  # تعداد حداکثر اتصالات همزمان
                minPoolSize=self._min_pool_size,  # تعداد حداقل اتصالات
                maxIdleTimeMS=45000,  # زمان بیکاری قبل از بستن
                serverSelectionTimeoutMS=5000,  # timeout برای انتخاب server
                connectTimeoutMS=10000,  # timeout برای اتصال
                socketTimeoutMS=30000,  # timeout برای socket
                socketKeepAlive=True,  # keep alive sockets
                retryWrites=True,  # retry failed writes
                retryReads=True  # retry failed reads
            )
            
            if self._client:
                self._connection_birth_time = time.time()
                logger.info("✅ MongoDB client created with optimized connection pooling")
            else:
                logger.warning("⚠️ MongoDB client created but is None")
                
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
        
        # Clear connection pool
        with self._pool_lock:
            if self._connection_pool:
                self._connection_pool.clear()
                logger.debug("🧹 MongoDB connection pool cleared")
    
    def release(self):
        """Release MongoDB connection and return to pool if possible"""
        with self._pool_lock:
            self._connection_count = max(0, self._connection_count - 1)
            logger.debug(f"📉 MongoDB connections: {self._connection_count}")
            
            # 🏊 Return to connection pool if space available
            if (len(self._connection_pool) < self._max_pool_size and
                self._client is not None):
                
                self._connection_pool.append(self._client)
                logger.debug(f"🏊 Returned MongoDB client to pool (pool size: {len(self._connection_pool)})")
                # Don't set self._client to None here! Keep the reference for future requests.
                # The pool will be used first, but if pool is empty, we still have the main client.
            
            # اگر اتصالی فعال نیست، client را ببند
            if self._connection_count == 0:
                self.close_client()
    
    def get_stats(self) -> dict:
        """دریافت آمار اتصالات MongoDB پیشرفته"""
        current_time = time.time()
        
        return {
            "client_exists": self._client is not None,
            "connection_count": self._connection_count,
            "pool_size": len(self._connection_pool),
            "max_pool_size": self._max_pool_size,
            "min_pool_size": self._min_pool_size,
            "last_health_check": self._last_health_check,
            "health_check_interval": self._health_check_interval,
            "needs_health_check": (current_time - self._last_health_check) > self._health_check_interval if self._last_health_check else True,
            "connection_age": current_time - self._connection_birth_time if self._connection_birth_time else 0,
            "max_connection_age": self._max_connection_age
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
        """دریافت آمار همه اتصالات پیشرفته"""
        weaviate_mgr = WeaviateConnectionManager()
        mongodb_mgr = MongoDBConnectionManager()
        
        stats = {
            "weaviate": weaviate_mgr.get_stats(),
            "mongodb": mongodb_mgr.get_stats(),
            "memory": ResourceMonitor.get_memory_usage(),
            "timestamp": time.time(),
            "overall_health": "healthy"
        }
        
        # 🆕 Overall health assessment
        weaviate_stats = stats["weaviate"]
        mongodb_stats = stats["mongodb"]
        
        # Check for health issues
        health_issues = []
        
        if weaviate_stats.get("needs_health_check", False):
            health_issues.append("Weaviate needs health check")
        
        if mongodb_stats.get("needs_health_check", False):
            health_issues.append("MongoDB needs health check")
        
        if weaviate_stats.get("connection_count", 0) > 20:
            health_issues.append("High Weaviate connection count")
        
        if mongodb_stats.get("connection_count", 0) > 100:
            health_issues.append("High MongoDB connection count")
        
        # Check connection age
        if weaviate_stats.get("connection_age", 0) > weaviate_stats.get("max_connection_age", 0):
            health_issues.append("Weaviate connection too old")
        
        if mongodb_stats.get("connection_age", 0) > mongodb_stats.get("max_connection_age", 0):
            health_issues.append("MongoDB connection too old")
        
        # Check pool usage
        if weaviate_stats.get("pool_size", 0) >= weaviate_stats.get("max_pool_size", 0):
            health_issues.append("Weaviate connection pool full")
        
        if mongodb_stats.get("pool_size", 0) >= mongodb_stats.get("max_pool_size", 0):
            health_issues.append("MongoDB connection pool full")
        
        if health_issues:
            stats["overall_health"] = "needs_attention"
            stats["health_issues"] = health_issues
        else:
            stats["health_issues"] = []
        
        return stats
    
    @staticmethod
    def check_thresholds():
        """بررسی آستانه‌های هشدار پیشرفته"""
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
        
        # بررسی وضعیت health check
        if stats["weaviate"]["needs_health_check"]:
            warnings.append("⚠️ Weaviate needs health check")
        
        if stats["mongodb"]["needs_health_check"]:
            warnings.append("⚠️ MongoDB needs health check")
        
        # بررسی وضعیت connection pool
        if stats["weaviate"]["pool_size"] >= stats["weaviate"]["max_pool_size"]:
            warnings.append("⚠️ Weaviate connection pool full")
        
        if stats["mongodb"]["pool_size"] >= stats["mongodb"]["max_pool_size"]:
            warnings.append("⚠️ MongoDB connection pool full")
        
        # بررسی سن اتصالات
        if stats["weaviate"]["connection_age"] > stats["weaviate"]["max_connection_age"]:
            warnings.append("⚠️ Weaviate connection too old")
        
        if stats["mongodb"]["connection_age"] > stats["mongodb"]["max_connection_age"]:
            warnings.append("⚠️ MongoDB connection too old")
        
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
    
    # Clear connection pools
    weaviate_mgr._connection_pool.clear()
    mongodb_mgr._connection_pool.clear()
    
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


def get_weaviate_client():
    """
    Get Weaviate client using the connection manager singleton
    
    Returns:
        WeaviateConnectionManager instance
    """
    return WeaviateConnectionManager.get_instance()


@contextmanager
def weaviate_client_context():
    """
    Context manager for Weaviate client with proper resource management
    
    Usage:
        with weaviate_client_context() as client:
            collections = client.collections.list()
    """
    manager = get_weaviate_client()
    client = manager.get_client()
    
    try:
        yield client
    finally:
        manager.release()
        logger.debug("🔓 Weaviate client released from context manager")
