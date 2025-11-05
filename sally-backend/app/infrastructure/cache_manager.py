"""
Advanced caching system with multiple strategies and performance optimization.
"""

import asyncio
import logging
import time
import hashlib
import json
import psutil
import os
from typing import Any, Dict, Optional, Union, List, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from functools import wraps, lru_cache
import pickle
import threading
from concurrent.futures import ThreadPoolExecutor
import weakref

logger = logging.getLogger(__name__)


class CacheHandler:
    """Base class for cache handlers in Chain of Responsibility pattern."""
    
    def __init__(self, next_handler: Optional['CacheHandler'] = None):
        self.next_handler = next_handler
    
    def handle(self, key: str, value: Any, ttl: int) -> bool:
        """Handle the cache operation. Returns True if handled, False to pass to next handler."""
        raise NotImplementedError
    
    def get(self, key: str) -> Any:
        """Get value from cache. Returns None if not found."""
        raise NotImplementedError


class SerializationBlacklist:
    """Tracks objects that consistently fail serialization."""
    
    def __init__(self):
        self._blacklist = set()
        self._failure_counts = {}
        self._lock = threading.Lock()
        self._max_failures = 3
    
    def add_failure(self, obj_type: type):
        """Add a serialization failure for an object type."""
        with self._lock:
            obj_type_name = obj_type.__name__
            self._failure_counts[obj_type_name] = self._failure_counts.get(obj_type_name, 0) + 1
            
            if self._failure_counts[obj_type_name] >= self._max_failures:
                self._blacklist.add(obj_type_name)
                logger.warning(f"Added {obj_type_name} to serialization blacklist after {self._max_failures} failures")
    
    def is_blacklisted(self, obj: Any) -> bool:
        """Check if an object's type is blacklisted."""
        return type(obj).__name__ in self._blacklist
    
    def reset_failures(self, obj_type: type):
        """Reset failure count for an object type (e.g., when a newer version might work)."""
        with self._lock:
            obj_type_name = obj_type.__name__
            if obj_type_name in self._failure_counts:
                del self._failure_counts[obj_type_name]


# Global serialization blacklist instance
serialization_blacklist = SerializationBlacklist()


class CacheStrategy(str, Enum):
    """Cache eviction strategies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time To Live
    ADAPTIVE = "adaptive"  # Adaptive based on access patterns


class CacheLevel(str, Enum):
    """Cache levels for different use cases."""
    MEMORY = "memory"
    DISK = "disk"
    REDIS = "redis"
    HYBRID = "hybrid"


@dataclass
class CacheConfig:
    """Configuration for cache systems."""
    strategy: CacheStrategy = CacheStrategy.LRU
    max_size: int = 1000
    ttl: int = 300  # 5 minutes
    level: CacheLevel = CacheLevel.MEMORY
    enable_compression: bool = True
    enable_serialization: bool = True
    background_cleanup: bool = True
    cleanup_interval: int = 60  # seconds
    stats_enabled: bool = True
    compression_threshold: int = 1024  # Only compress entries larger than this
    
    # Memory pressure monitoring
    memory_pressure_enabled: bool = True
    memory_threshold_percent: float = 80.0  # Trigger cleanup when memory usage exceeds this percentage
    memory_cleanup_ratio: float = 0.3  # Remove this percentage of cache entries when memory pressure is detected
    memory_check_interval: int = 30  # Check memory pressure every X seconds
    
    def __post_init__(self):
        if self.max_size <= 0:
            raise ValueError("Max size must be positive")
        if self.ttl <= 0:
            raise ValueError("TTL must be positive")
        if self.cleanup_interval <= 0:
            raise ValueError("Cleanup interval must be positive")
        if self.memory_threshold_percent <= 0 or self.memory_threshold_percent > 100:
            raise ValueError("Memory threshold must be between 0 and 100")
        if self.memory_cleanup_ratio <= 0 or self.memory_cleanup_ratio > 1:
            raise ValueError("Memory cleanup ratio must be between 0 and 1")
        if self.memory_check_interval <= 0:
            raise ValueError("Memory check interval must be positive")


@dataclass
class CacheStats:
    """Cache statistics for monitoring."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    total_items: int = 0
    avg_access_time: float = 0.0
    compression_ratio: float = 0.0
    memory_usage: int = 0
    hit_rate: float = 0.0
    
    def update_hit_rate(self):
        """Update hit rate."""
        total = self.hits + self.misses
        if total > 0:
            self.hit_rate = self.hits / total
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        self.update_hit_rate()
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "size": self.size,
            "total_items": self.total_items,
            "avg_access_time": self.avg_access_time,
            "compression_ratio": self.compression_ratio,
            "memory_usage": self.memory_usage,
            "hit_rate": self.hit_rate
        }


class CacheEntry:
    """Represents a cache entry with metadata."""
    
    def __init__(
        self,
        key: str,
        value: Any,
        ttl: int = 300,
        compressed: bool = False,
        serialized: bool = False
    ):
        self.key = key
        self.value = value
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.access_count = 0
        self.ttl = ttl
        self.compressed = compressed
        self.serialized = serialized
        self.size = self._calculate_size()
    
    def _calculate_size(self) -> int:
        """Calculate the size of the entry."""
        try:
            if self.serialized:
                return len(pickle.dumps(self.value))
            else:
                return len(str(self.value))
        except Exception:
            return len(str(self.value))
    
    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        return time.time() - self.created_at > self.ttl
    
    def access(self):
        """Mark the entry as accessed."""
        self.last_accessed = time.time()
        self.access_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "ttl": self.ttl,
            "compressed": self.compressed,
            "serialized": self.serialized,
            "size": self.size
        }


class BaseCache(Generic[TypeVar('T')]):
    """Base cache interface."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.stats = CacheStats()
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=2)
        
        if config.background_cleanup:
            self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        def cleanup_task():
            while True:
                time.sleep(self.config.cleanup_interval)
                self.cleanup()
        
        self._executor.submit(cleanup_task)
    
    def _start_memory_monitoring_task(self):
        """Start memory pressure monitoring task."""
        def memory_monitor_task():
            while True:
                time.sleep(self.config.memory_check_interval)
                self._check_memory_pressure()
        
        self._executor.submit(memory_monitor_task)
    
    def _check_memory_pressure(self):
        """Check if memory pressure is high and trigger cleanup if needed."""
        try:
            current_time = time.time()
            if current_time - self._last_memory_check < self.config.memory_check_interval:
                return
            
            # Get system memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Check if memory pressure is high
            if memory_percent > self.config.memory_threshold_percent:
                self._memory_pressure_active = True
                logger.info(f"Memory pressure detected: {memory_percent:.1f}% > {self.config.memory_threshold_percent}%")
                
                # Trigger memory-based cleanup
                cleaned_count = self._memory_pressure_cleanup()
                if cleaned_count > 0:
                    logger.info(f"Memory pressure cleanup removed {cleaned_count} cache entries")
                
                self._last_memory_check = current_time
            else:
                self._memory_pressure_active = False
                
        except Exception as e:
            logger.warning(f"Memory pressure monitoring failed: {e}")
    
    def _memory_pressure_cleanup(self) -> int:
        """Perform cleanup based on memory pressure."""
        if not self._cache:
            return 0
        
        # Calculate how many entries to remove
        total_entries = len(self._cache)
        entries_to_remove = int(total_entries * self.config.memory_cleanup_ratio)
        
        if entries_to_remove <= 0:
            return 0
        
        # Get list of keys sorted by priority for removal
        keys_to_remove = self._get_keys_for_removal(entries_to_remove)
        
        # Remove the selected keys
        cleaned_count = 0
        for key in keys_to_remove:
            if self.delete(key):
                cleaned_count += 1
        
        return cleaned_count
    
    def _get_keys_for_removal(self, count: int) -> List[str]:
        """Get keys that should be removed based on cache strategy."""
        if self.config.strategy == CacheStrategy.LRU:
            # Remove least recently used
            return self._access_order[:count]
        elif self.config.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            sorted_keys = sorted(self._access_frequency.keys(), key=lambda k: self._access_frequency[k])
            return sorted_keys[:count]
        elif self.config.strategy == CacheStrategy.FIFO:
            # Remove oldest entries
            return self._creation_order[:count]
        else:
            # Default: remove random entries
            keys = list(self._cache.keys())
            return keys[:count]
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        raise NotImplementedError
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        raise NotImplementedError
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        raise NotImplementedError
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        raise NotImplementedError
    
    def clear(self) -> bool:
        """Clear all values from cache."""
        raise NotImplementedError
    
    def cleanup(self) -> int:
        """Clean up expired entries."""
        raise NotImplementedError
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self.stats
    
    def _update_stats(self, hit: bool, access_time: float):
        """Update cache statistics."""
        if hit:
            self.stats.hits += 1
        else:
            self.stats.misses += 1
        
        self.stats.total_items += 1
        self.stats.avg_access_time = (
            (self.stats.avg_access_time * (self.stats.hits + self.stats.misses - 1) + access_time) /
            (self.stats.hits + self.stats.misses)
        )


class MemoryCacheHandler(CacheHandler):
    """Memory cache handler using Chain of Responsibility pattern."""
    
    def __init__(self, config: CacheConfig, next_handler: Optional[CacheHandler] = None):
        super().__init__(next_handler)
        self.config = config
        self.cache: Dict[str, CacheEntry] = {}
        self.stats = CacheStats()
        self._lock = threading.RLock()
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        
        if config.background_cleanup:
            self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread."""
        self._cleanup_thread = threading.Thread(
            target=self._background_cleanup,
            daemon=True,
            name="MemoryCacheCleanup"
        )
        self._cleanup_thread.start()
    
    def _background_cleanup(self):
        """Background cleanup process."""
        while not self._stop_cleanup.wait(self.config.cleanup_interval):
            try:
                self._cleanup_expired()
                self._check_memory_pressure()
            except Exception as e:
                logger.error(f"Background cleanup error: {e}")
    
    def _cleanup_expired(self):
        """Clean up expired entries."""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self.cache.items()
                if current_time - entry.created_at > entry.ttl
            ]
            
            for key in expired_keys:
                if key in self.cache:
                    del self.cache[key]
                    self.stats.evictions += 1
                    self.stats.total_items -= 1
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired entries")
    
    def _check_memory_pressure(self):
        """Check and handle memory pressure."""
        if not self.config.memory_pressure_enabled:
            return
        
        try:
            memory_percent = psutil.virtual_memory().percent
            
            if memory_percent > self.config.memory_threshold_percent:
                logger.warning(f"Memory pressure detected: {memory_percent:.1f}%")
                
                # Calculate how many entries to remove
                entries_to_remove = int(len(self.cache) * self.config.memory_cleanup_ratio)
                if entries_to_remove > 0:
                    # Remove least recently used entries
                    sorted_entries = sorted(
                        self.cache.items(),
                        key=lambda x: x[1].last_accessed
                    )
                    
                    removed_keys = [key for key, _ in sorted_entries[:entries_to_remove]]
                    for key in removed_keys:
                        if key in self.cache:
                            del self.cache[key]
                            self.stats.evictions += 1
                            self.stats.total_items -= 1
                    
                    logger.info(f"Removed {len(removed_keys)} entries due to memory pressure")
        except Exception as e:
            logger.error(f"Memory pressure check failed: {e}")
    
    def handle(self, key: str, value: Any, ttl: int) -> bool:
        """Handle cache set operation."""
        try:
            # Check if object is blacklisted for serialization
            if serialization_blacklist.is_blacklisted(value):
                logger.debug(f"Skipping serialization for blacklisted object type: {type(value).__name__}")
                # Store without serialization
                entry = CacheEntry(key, value, ttl, compressed=False, serialized=False)
            else:
                # Try serialization with blacklist tracking
                try:
                    serialized_value = self._serialize_value(value)
                    entry = CacheEntry(key, serialized_value, ttl, compressed=False, serialized=True)
                except Exception as e:
                    serialization_blacklist.add_failure(type(value))
                    logger.warning(f"Serialization failed for {type(value).__name__}, storing as-is: {e}")
                    entry = CacheEntry(key, value, ttl, compressed=False, serialized=False)
            
            with self._lock:
                # Check if we need to evict entries
                if len(self.cache) >= self.config.max_size:
                    self._evict_entry()
                
                self.cache[key] = entry
                self.stats.total_items += 1
                self.stats.size += len(str(value))
            
            return True
        
        except Exception as e:
            logger.error(f"Memory cache set failed: {e}")
            return False
    
    def get(self, key: str) -> Any:
        """Get value from memory cache."""
        with self._lock:
            entry = self.cache.get(key)
            
            if entry is None:
                self.stats.misses += 1
                return None
            
            if entry.is_expired():
                if key in self.cache:
                    del self.cache[key]
                    self.stats.evictions += 1
                    self.stats.total_items -= 1
                self.stats.misses += 1
                return None
            
            # Update access stats
            entry.access()
            self.stats.hits += 1
            
            # Deserialize if needed
            if entry.serialized:
                try:
                    return self._deserialize_value(entry.value)
                except Exception as e:
                    logger.warning(f"Deserialization failed: {e}")
                    return entry.value
            else:
                return entry.value
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value with error handling."""
        if self.config.enable_serialization:
            try:
                return pickle.dumps(value)
            except Exception as e:
                raise ValueError(f"Serialization failed: {e}")
        return value
    
    def _deserialize_value(self, value: bytes) -> Any:
        """Deserialize value with error handling."""
        if self.config.enable_serialization:
            try:
                return pickle.loads(value)
            except Exception as e:
                raise ValueError(f"Deserialization failed: {e}")
        return value
    
    def _evict_entry(self):
        """Evict an entry based on the configured strategy."""
        if self.config.strategy == CacheStrategy.LRU:
            self._evict_lru()
        elif self.config.strategy == CacheStrategy.LFU:
            self._evict_lfu()
        elif self.config.strategy == CacheStrategy.FIFO:
            self._evict_fifo()
        elif self.config.strategy == CacheStrategy.ADAPTIVE:
            self._evict_adaptive()
        else:
            # Default to LRU
            self._evict_lru()
    
    def _evict_lru(self):
        """Evict least recently used entry."""
        if not self.cache:
            return
        
        # Find least recently used entry
        lru_key = min(self.cache.keys(), key=lambda k: self.cache[k].last_accessed)
        if lru_key in self.cache:
            del self.cache[lru_key]
            self.stats.evictions += 1
            self.stats.total_items -= 1
    
    def _evict_lfu(self):
        """Evict least frequently used entry."""
        if not self.cache:
            return
        
        # Find least frequently used entry
        lfu_key = min(self.cache.keys(), key=lambda k: self.cache[k].access_count)
        if lfu_key in self.cache:
            del self.cache[lfu_key]
            self.stats.evictions += 1
            self.stats.total_items -= 1
    
    def _evict_fifo(self):
        """Evict first in first out entry."""
        if not self.cache:
            return
        
        # Find oldest entry
        fifo_key = min(self.cache.keys(), key=lambda k: self.cache[k].created_at)
        if fifo_key in self.cache:
            del self.cache[fifo_key]
            self.stats.evictions += 1
            self.stats.total_items -= 1
    
    def _evict_adaptive(self):
        """Adaptive eviction based on access patterns."""
        # Simple adaptive strategy: prefer LRU but use LFU if there are many frequent accesses
        if self.cache and max(entry.access_count for entry in self.cache.values()) > 10:
            self._evict_lfu()
        else:
            self._evict_lru()
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        with self._lock:
            if key not in self.cache:
                return False
            
            del self.cache[key]
            self.stats.evictions += 1
            self.stats.total_items -= 1
            
            logger.debug(f"Cache delete: {key}")
            return True
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        with self._lock:
            if key not in self.cache:
                return False
            
            entry = self.cache[key]
            if entry.is_expired():
                if key in self.cache:
                    del self.cache[key]
                    self.stats.evictions += 1
                    self.stats.total_items -= 1
                return False
            
            return True
    
    def clear(self) -> bool:
        """Clear all values from cache."""
        with self._lock:
            self.cache.clear()
            self.stats.size = 0
            self.stats.total_items = 0
            self.stats.evictions = 0
            
            logger.info("Cache cleared")
            return True
    
    def cleanup(self) -> int:
        """Clean up expired entries."""
        cleaned_count = 0
        
        with self._lock:
            expired_keys = [
                key for key, entry in self.cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                if key in self.cache:
                    del self.cache[key]
                    self.stats.evictions += 1
                    self.stats.total_items -= 1
                    cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired cache entries")
        
        return cleaned_count
    
    def stop(self):
        """Stop the cleanup thread."""
        self._stop_cleanup.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)


class CacheManager:
    """Main cache manager using Chain of Responsibility pattern."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.stats = CacheStats()
        self._lock = threading.RLock()
        
        # Initialize cache handlers based on config
        self.handlers = []
        
        if config.level in [CacheLevel.MEMORY, CacheLevel.HYBRID]:
            self.handlers.append(MemoryCacheHandler(config))
        
        # Start background cleanup for all handlers
        if config.background_cleanup:
            self._start_cleanup_threads()
    
    def _start_cleanup_threads(self):
        """Start cleanup threads for all handlers."""
        self.cleanup_threads = []
        for handler in self.handlers:
            if hasattr(handler, '_start_cleanup_thread'):
                thread = threading.Thread(
                    target=handler._background_cleanup,
                    daemon=True,
                    name=f"CacheCleanup-{handler.__class__.__name__}"
                )
                thread.start()
                self.cleanup_threads.append(thread)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in the cache."""
        if ttl is None:
            ttl = self.config.ttl
        
        # Start with the first handler in the chain
        if self.handlers:
            return self.handlers[0].handle(key, value, ttl)
        
        return False
    
    def get(self, key: str) -> Any:
        """Get a value from the cache."""
        # Start with the first handler in the chain
        if self.handlers:
            return self.handlers[0].get(key)
        
        return None
    
    def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        success = False
        
        for handler in self.handlers:
            if hasattr(handler, 'delete'):
                if handler.delete(key):
                    success = True
        
        if success:
            with self._lock:
                self.stats.total_items -= 1
        
        return success
    
    def clear(self) -> bool:
        """Clear all values from the cache."""
        success = True
        
        for handler in self.handlers:
            if hasattr(handler, 'clear'):
                if not handler.clear():
                    success = False
        
        if success:
            with self._lock:
                self.stats.total_items = 0
        
        return success
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return self.stats.to_dict()
    
    def stop(self):
        """Stop all background threads."""
        for handler in self.handlers:
            if hasattr(handler, 'stop'):
                handler.stop()


# Decorators for caching
def _generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Generate a secure cache key by filtering sensitive data."""
    # Filter out sensitive keys from kwargs
    safe_kwargs = {}
    sensitive_keys = {'token', 'password', 'secret', 'key', 'auth', 'credential', 'session'}
    
    for k, v in kwargs.items():
        if k.lower() in sensitive_keys:
            # Hash sensitive values
            safe_kwargs[k] = f"hashed_{hashlib.sha256(str(v).encode()).hexdigest()[:16]}"
        else:
            safe_kwargs[k] = v
    
    # Create key string
    key_parts = [func_name]
    
    # Add args (convert to string representation)
    for arg in args:
        if isinstance(arg, (dict, list)):
            # For complex objects, use hash to avoid very long keys
            key_parts.append(f"obj_{hash(str(arg))}")
        else:
            key_parts.append(str(arg))
    
    # Add safe kwargs
    for k, v in safe_kwargs.items():
        key_parts.append(f"{k}={v}")
    
    # Generate final key with hash to prevent key length issues
    key_str = ":".join(key_parts)
    return hashlib.md5(key_str.encode()).hexdigest()


def cache_result(ttl_seconds: int = 300, cache_key: Optional[str] = None):
    """Decorator to cache function results."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if cache_key:
                key = cache_key
            else:
                key = _generate_cache_key(func.__name__, args, kwargs)
            
            # Try to get from cache using global instance
            result = default_cache_manager.get(key)
            
            if result is not None:
                logger.debug(f"Cache hit for {key}")
                return result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            default_cache_manager.set(key, result, ttl=ttl_seconds)
            
            return result
        
        return wrapper
    return decorator


def cache_async_result(ttl_seconds: int = 300, cache_key: Optional[str] = None):
    """Decorator to cache async function results."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if cache_key:
                key = cache_key
            else:
                key = _generate_cache_key(func.__name__, args, kwargs)
            
            # Try to get from cache using global instance
            result = default_cache_manager.get(key)
            
            if result is not None:
                logger.debug(f"Cache hit for {key}")
                return result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            default_cache_manager.set(key, result, ttl=ttl_seconds)
            
            return result
        
        return wrapper
    return decorator


# Global cache manager instance
default_cache_manager = CacheManager(CacheConfig())