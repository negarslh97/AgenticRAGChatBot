# connection_manager.py

"""
🚀 Optimized Connection Manager - مدیریت بهینه اتصالات به Weaviate و MongoDB
=============================================================================

نسخه استاندارد و بهینه‌شده برای کاهش تأخیر و افزایش سرعت عملکرد.

ویژگی‌ها:
✅ حذف نسخه‌های قدیمی و legacy
✅ ساده‌سازی معماری و کاهش پیچیدگی
✅ بهینه‌سازی performance و resource management
✅ حذف singleton pattern پیچیده
✅ استفاده مستقیم از clients
✅ مدیریت خطای پیشرفته
✅ Circuit Breaker integration
"""

import asyncio
import logging
import time
import threading
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager, contextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, circuit_breaker_protect
from .ai_exceptions import AIException, ErrorType, AISeverity

logger = logging.getLogger(__name__)

# Import settings directly from config
from app.core.config import settings


class WeaviateConnectionError(AIException):
    """Weaviate connection specific error"""
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(
            message=f"Weaviate Connection Error: {message}",
            error_type=ErrorType.CONNECTION_FAILED,
            severity=AISeverity.HIGH,
            original_error=original_error
        )


class MongoDBConnectionError(AIException):
    """MongoDB connection specific error"""
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(
            message=f"MongoDB Connection Error: {message}",
            error_type=ErrorType.CONNECTION_FAILED,
            severity=AISeverity.HIGH,
            original_error=original_error
        )


class OptimizedWeaviateConnectionManager:
    """
    🚀 مدیریت بهینه و استاندارد اتصالات به Weaviate
    
    ویژگی‌ها:
    - طراحی مدرن و ساده
    - Circuit Breaker protection
    - بهینه‌سازی عملکرد
    - مدیریت خطای پیشرفته
    - Thread-safe operations
    """
    
    def __init__(self, circuit_breaker_config: Optional[CircuitBreakerConfig] = None):
        self._client = None
        self._client_lock = threading.RLock()
        self._last_health_check = 0
        self._health_check_interval = 300  # 5 minutes
        
        # Setup circuit breaker
        cb_config = circuit_breaker_config or CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60,
            name="weaviate_connection"
        )
        self._circuit_breaker = CircuitBreaker(cb_config)
        
        logger.info("🚀 Optimized WeaviateConnectionManager initialized")
    
    @circuit_breaker_protect(name="weaviate_get_client")
    def get_client(self) -> 'weaviate.WeaviateClient':
        """
        دریافت client بهینه‌شده - با Circuit Breaker protection
        
        Returns:
            WeaviateClient instance
            
        Raises:
            WeaviateConnectionError: If unable to establish connection
        """
        current_time = time.time()
        
        try:
            # بررسی سریع health check
            if (current_time - self._last_health_check) > self._health_check_interval:
                if self._client and not self._is_client_healthy():
                    logger.info("🔄 Client unhealthy, creating new connection...")
                    self._client = None
                self._last_health_check = current_time
            
            # ایجاد client جدید در صورت نیاز
            if self._client is None:
                self._client = self._create_client()
            
            return self._client
            
        except Exception as e:
            raise WeaviateConnectionError(f"Failed to get Weaviate client: {str(e)}", e)
    
    def _create_client(self) -> 'weaviate.WeaviateClient':
        """ایجاد client جدید با تنظیمات بهینه"""
        start_time = time.time()
        
        try:
            logger.debug("🔌 Creating optimized Weaviate client...")
            
            # Use proper settings from config
            weaviate_url = settings.weaviate_url_loaded
            weaviate_api_key = settings.weaviate_api_key_loaded
            
            if not weaviate_url:
                logger.warning("⚠️ Weaviate URL not configured, using default")
                weaviate_url = settings.weaviate_url_loaded
                weaviate_api_key = settings.weaviate_api_key_loaded

            
            if not weaviate_url:
                raise ValueError("Weaviate URL is not configured")
            
            # Create client based on availability
            try:
                import weaviate.connect
                from weaviate import WeaviateClient
                from weaviate.connect import ConnectionParams
                from weaviate.auth import AuthApiKey
                
                # Extract host and port from URL properly
                from urllib.parse import urlparse
                parsed = urlparse(weaviate_url if weaviate_url.startswith(('http://', 'https://')) else f"http://{weaviate_url}")
                host = parsed.hostname or parsed.path  # Handle both formats
                port = parsed.port or 8080  # Use port from URL or default to 8080
                
                if weaviate_api_key:
                    auth_config = AuthApiKey(api_key=weaviate_api_key)
                    client = WeaviateClient(
                        connection_params=ConnectionParams(
                            http=weaviate.connect.ProtocolParams(
                                host=host,
                                port=port,
                                secure=parsed.scheme == 'https'
                            ),
                            grpc=weaviate.connect.ProtocolParams(
                                host=host,
                                port=50051,
                                secure=parsed.scheme == 'https'
                            )
                        ),
                        auth_config=auth_config
                    )
                else:
                    client = WeaviateClient(
                        connection_params=ConnectionParams(
                            http=weaviate.connect.ProtocolParams(
                                host=host,
                                port=port,
                                secure=parsed.scheme == 'https'
                            ),
                            grpc=weaviate.connect.ProtocolParams(
                                host=host,
                                port=50051,
                                secure=parsed.scheme == 'https'
                            )
                        )
                    )
            except ImportError:
                # Fallback for older versions
                import weaviate
                client = weaviate.Client(weaviate_url)
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Weaviate client created in {elapsed:.3f}s")
            
            if elapsed > 0.5:
                logger.warning(f"⚠️ Slow Weaviate client creation: {elapsed:.3f}s")
            
            return client
            
        except Exception as e:
            elapsed = time.time() - start_time
            raise WeaviateConnectionError(f"Error creating Weaviate client after {elapsed:.3f}s: {str(e)}", e)
    
    def _is_client_healthy(self) -> bool:
        """بررسی سریع سلامت client"""
        try:
            return self._client is not None and self._client.is_ready()
        except:
            return False
    
    @circuit_breaker_protect(name="weaviate_close_client")
    def close_client(self):
        """بستن client"""
        if self._client is not None:
            try:
                self._client.close()
                logger.info("🧹 Weaviate client closed")
            except Exception as e:
                logger.warning(f"⚠️ Error closing Weaviate client: {e}")
            finally:
                self._client = None
    
    def get_stats(self) -> Dict[str, Any]:
        """دریافت آمار ساده اتصالات"""
        current_time = time.time()
        
        return {
            "client_exists": self._client is not None,
            "is_ready": self._is_client_healthy(),
            "last_health_check": self._last_health_check,
            "health_check_interval": self._health_check_interval,
            "needs_health_check": (current_time - self._last_health_check) > self._health_check_interval,
            "circuit_breaker_state": self._circuit_breaker.get_state()
        }
    
    def reset_circuit_breaker(self):
        """Reset circuit breaker manually"""
        self._circuit_breaker.reset()
        logger.info("🔄 Weaviate circuit breaker reset")

class OptimizedMongoDBConnectionManager:
    """
    🚀 مدیریت بهینه و استاندارد اتصالات به MongoDB
    
    ویژگی‌ها:
    - طراحی مدرن و ساده
    - Circuit Breaker protection
    - Connection Pooling بهینه
    - مدیریت خطای پیشرفته
    - Thread-safe operations
    """
    
    def __init__(self, circuit_breaker_config: Optional[CircuitBreakerConfig] = None):
        self._client = None
        self._client_lock = threading.RLock()
        self._connection_count = 0
        
        # Setup circuit breaker
        cb_config = circuit_breaker_config or CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60,
            name="mongodb_connection"
        )
        self._circuit_breaker = CircuitBreaker(cb_config)
        
        logger.info("🚀 Optimized MongoDBConnectionManager initialized")
    
    @circuit_breaker_protect(name="mongodb_get_client")
    def get_client(self) -> AsyncIOMotorClient:
        """
        دریافت یا ایجاد client با تنظیمات بهینه
        
        Returns:
            AsyncIOMotorClient instance
            
        Raises:
            MongoDBConnectionError: If unable to establish connection
        """
        with self._client_lock:
            if self._client is None:
                self._client = self._create_client()
            
            self._connection_count += 1
            logger.debug(f"📊 MongoDB connections: {self._connection_count}")
            
            return self._client
    
    def _create_client(self) -> AsyncIOMotorClient:
        """ایجاد client جدید با تنظیمات بهینه"""
        try:
            logger.debug("🔌 Creating optimized MongoDB client...")
            
            # تنظیمات بهینه
            mongodb_url = settings.MONGODB_URL
            if not mongodb_url:
                raise ValueError("MongoDB URL is not configured in settings")
                
            self._client = AsyncIOMotorClient(
                mongodb_url,
                maxPoolSize=20,
                minPoolSize=5,
                maxIdleTimeMS=30000,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=30000,
                retryWrites=True,
                retryReads=True
            )
            
            logger.info(f"✅ MongoDB client created with optimized settings: {mongodb_url}")
            return self._client
            
        except Exception as e:
            raise MongoDBConnectionError(f"Error creating MongoDB client: {str(e)}", e)
    
    def release(self):
        """آزادسازی اتصال"""
        with self._client_lock:
            self._connection_count = max(0, self._connection_count - 1)
            logger.debug(f"📉 MongoDB connections: {self._connection_count}")
            
            # اگر اتصالی فعال نیست، client را ببند
            if self._connection_count == 0:
                self.close_client()
    
    @circuit_breaker_protect(name="mongodb_close_client")
    def close_client(self):
        """بستن client"""
        if self._client is not None:
            try:
                self._client.close()
                logger.info("🧹 MongoDB client closed")
            except Exception as e:
                logger.warning(f"⚠️ Error closing MongoDB client: {e}")
            finally:
                self._client = None
                self._connection_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """دریافت آمار اتصالات"""
        return {
            "client_exists": self._client is not None,
            "connection_count": self._connection_count,
            "circuit_breaker_state": self._circuit_breaker.get_state()
        }
    
    def reset_circuit_breaker(self):
        """Reset circuit breaker manually"""
        self._circuit_breaker.reset()
        logger.info("🔄 MongoDB circuit breaker reset")


# Global optimized instances
_weaviate_manager = OptimizedWeaviateConnectionManager()
_mongodb_manager = OptimizedMongoDBConnectionManager()


@contextmanager
def weaviate_client():
    """
    Context manager بهینه‌شده برای استفاده امن از Weaviate client
    
    Usage:
        with weaviate_client() as client:
            # استفاده از client
            results = client.collections.get("MyCollection").query.fetch_objects()
    """
    client = _weaviate_manager.get_client()
    
    try:
        yield client
    finally:
        logger.debug("🔓 Weaviate client used")


@asynccontextmanager
async def mongodb_client():
    """
    Async context manager بهینه‌شده برای استفاده امن از MongoDB client
    
    Usage:
        async with mongodb_client() as client:
            db = client.get_default_database()
            # استفاده از database
    """
    client = _mongodb_manager.get_client()
    
    try:
        yield client
    finally:
        _mongodb_manager.release()
        logger.debug("🔓 MongoDB client released")


# Connection management functions
def cleanup_all_connections():
    """بستن همه اتصالات"""
    logger.info("🧹 Cleaning up all connections...")
    
    _weaviate_manager.close_client()
    _mongodb_manager.close_client()
    
    logger.info("✅ All connections cleaned up")


async def startup_connections():
    """راه‌اندازی ساده اتصالات در startup"""
    logger.info("🚀 Initializing optimized connection managers...")
    
    try:
        # Pre-initialize clients برای سرعت بیشتر
        _weaviate_manager.get_client()
        _mongodb_manager.get_client()
        logger.info("✅ Optimized connection managers ready")
    except Exception as e:
        logger.error(f"❌ Failed to initialize connections: {e}")
        raise


async def shutdown_connections():
    """بستن اتصالات در shutdown"""
    cleanup_all_connections()


# Utility functions
def get_weaviate_manager() -> OptimizedWeaviateConnectionManager:
    """دریافت Weaviate connection manager"""
    return _weaviate_manager


def get_mongodb_manager() -> OptimizedMongoDBConnectionManager:
    """دریافت MongoDB connection manager"""
    return _mongodb_manager


@contextmanager
def weaviate_client_context():
    """
    Context manager برای Weaviate client با مدیریت بهینه منابع
    
    Usage:
        with weaviate_client_context() as client:
            collections = client.collections.list()
    """
    manager = get_weaviate_manager()
    client = manager.get_client()
    
    try:
        yield client
    finally:
        logger.debug("🔓 Weaviate client released from context manager")


# Aliases for easy import
ConnectionManager = OptimizedWeaviateConnectionManager
MongoDBManager = OptimizedMongoDBConnectionManager

# Export main classes
__all__ = [
    'OptimizedWeaviateConnectionManager',
    'OptimizedMongoDBConnectionManager',
    'ConnectionManager',
    'MongoDBManager',
    'weaviate_client',
    'mongodb_client',
    'cleanup_all_connections',
    'startup_connections',
    'shutdown_connections',
    'get_weaviate_manager',
    'get_mongodb_manager',
    'weaviate_client_context'
]
