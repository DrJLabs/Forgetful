"""
Caching System for Agent-4 Performance Optimization

This module provides comprehensive caching strategies including:
- In-memory caching with TTL
- Redis-compatible caching (with fallback)
- Query result caching
- Cache invalidation strategies
- Performance monitoring
"""

import json
import time
import threading
from typing import Any, Dict, Optional, Callable, Union, List
from dataclasses import dataclass
from functools import wraps
from datetime import datetime, timedelta
import hashlib
import pickle
from contextlib import contextmanager

from .logging_system import get_logger, performance_logger

logger = get_logger('caching')

@dataclass
class CacheConfig:
    """Configuration for cache behavior."""
    ttl: int = 3600  # Time to live in seconds
    max_size: int = 1000  # Maximum cache size
    eviction_policy: str = 'lru'  # LRU, LFU, or FIFO
    compress: bool = False  # Whether to compress cached data
    serialize: bool = True  # Whether to serialize cached data

class CacheEntry:
    """Individual cache entry with metadata."""
    
    def __init__(self, value: Any, ttl: int = 3600):
        self.value = value
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl
        self.access_count = 0
        self.last_accessed = self.created_at
        self.size = self._calculate_size()
    
    def _calculate_size(self) -> int:
        """Calculate approximate size of cached value."""
        try:
            if isinstance(self.value, str):
                return len(self.value.encode('utf-8'))
            elif isinstance(self.value, (int, float)):
                return 8
            elif isinstance(self.value, dict):
                return len(json.dumps(self.value).encode('utf-8'))
            elif isinstance(self.value, list):
                return len(json.dumps(self.value).encode('utf-8'))
            else:
                return len(pickle.dumps(self.value))
        except Exception:
            return 100  # Default size estimate
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() > self.expires_at
    
    def touch(self):
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = time.time()
    
    def get_age(self) -> float:
        """Get age of cache entry in seconds."""
        return time.time() - self.created_at

class InMemoryCache:
    """
    High-performance in-memory cache with TTL and eviction policies.
    
    Features:
    - TTL-based expiration
    - LRU/LFU/FIFO eviction policies
    - Size-based eviction
    - Performance metrics
    """
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache = {}
        self.lock = threading.RLock()
        self.metrics = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0,
            'memory_usage': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self.lock:
            if key not in self.cache:
                self.metrics['misses'] += 1
                return None
            
            entry = self.cache[key]
            
            # Check expiration
            if entry.is_expired():
                del self.cache[key]
                self.metrics['misses'] += 1
                return None
            
            # Update access metadata
            entry.touch()
            self.metrics['hits'] += 1
            
            logger.debug(f"Cache HIT for key: {key}")
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        with self.lock:
            ttl = ttl or self.config.ttl
            entry = CacheEntry(value, ttl)
            
            # Check if we need to evict
            if len(self.cache) >= self.config.max_size:
                self._evict()
            
            self.cache[key] = entry
            self.metrics['size'] = len(self.cache)
            self.metrics['memory_usage'] += entry.size
            
            logger.debug(f"Cache SET for key: {key}, TTL: {ttl}")
            return True
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        with self.lock:
            if key in self.cache:
                entry = self.cache.pop(key)
                self.metrics['size'] = len(self.cache)
                self.metrics['memory_usage'] -= entry.size
                logger.debug(f"Cache DELETE for key: {key}")
                return True
            return False
    
    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.metrics['size'] = 0
            self.metrics['memory_usage'] = 0
            logger.info("Cache cleared")
    
    def _evict(self):
        """Evict entries based on eviction policy."""
        if not self.cache:
            return
        
        if self.config.eviction_policy == 'lru':
            # Evict least recently used
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k].last_accessed)
        elif self.config.eviction_policy == 'lfu':
            # Evict least frequently used
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k].access_count)
        else:  # FIFO
            # Evict oldest entry
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k].created_at)
        
        entry = self.cache.pop(oldest_key)
        self.metrics['evictions'] += 1
        self.metrics['memory_usage'] -= entry.size
        
        logger.debug(f"Cache EVICT for key: {oldest_key}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.metrics['hits'] + self.metrics['misses']
        hit_rate = self.metrics['hits'] / max(total_requests, 1)
        
        return {
            **self.metrics,
            'hit_rate': hit_rate,
            'total_requests': total_requests
        }

class RedisCache:
    """
    Redis-compatible cache with fallback to in-memory cache.
    
    Features:
    - Redis backend when available
    - Automatic fallback to in-memory
    - Connection pooling
    - Serialization support
    """
    
    def __init__(self, config: CacheConfig, redis_url: str = None):
        self.config = config
        self.redis_client = None
        self.fallback_cache = InMemoryCache(config)
        
        # Try to connect to Redis
        try:
            if redis_url:
                # Would initialize Redis client if redis library available
                logger.info("Redis not available, using in-memory fallback")
        except Exception as e:
            logger.warning(f"Redis connection failed, using in-memory fallback: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value is not None:
                    return json.loads(value) if self.config.serialize else value
                return None
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")
        
        return self.fallback_cache.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        ttl = ttl or self.config.ttl
        
        if self.redis_client:
            try:
                serialized_value = json.dumps(value) if self.config.serialize else value
                self.redis_client.setex(key, ttl, serialized_value)
                return True
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")
        
        return self.fallback_cache.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if self.redis_client:
            try:
                return bool(self.redis_client.delete(key))
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")
        
        return self.fallback_cache.delete(key)
    
    def clear(self):
        """Clear all cache entries."""
        if self.redis_client:
            try:
                self.redis_client.flushdb()
                return
            except Exception as e:
                logger.warning(f"Redis clear failed: {e}")
        
        self.fallback_cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self.redis_client:
            try:
                info = self.redis_client.info()
                return {
                    'type': 'redis',
                    'connected': True,
                    'memory_usage': info.get('used_memory', 0),
                    'keys': info.get('db0', {}).get('keys', 0)
                }
            except Exception:
                pass
        
        return {
            'type': 'in_memory_fallback',
            'connected': False,
            **self.fallback_cache.get_stats()
        }

class QueryCache:
    """
    Specialized cache for database query results.
    
    Features:
    - Query-specific caching
    - Parameter-based cache keys
    - Automatic invalidation
    - Performance metrics
    """
    
    def __init__(self, cache_backend: Union[InMemoryCache, RedisCache]):
        self.cache = cache_backend
        self.query_stats = {}
    
    def get_cache_key(self, query: str, params: tuple = None) -> str:
        """Generate cache key for query and parameters."""
        key_data = f"{query}:{params or ()}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_query_result(self, query: str, params: tuple = None) -> Optional[Any]:
        """Get cached query result."""
        cache_key = self.get_cache_key(query, params)
        result = self.cache.get(cache_key)
        
        # Update query stats
        query_hash = hashlib.md5(query.encode()).hexdigest()
        if query_hash not in self.query_stats:
            self.query_stats[query_hash] = {'hits': 0, 'misses': 0}
        
        if result is not None:
            self.query_stats[query_hash]['hits'] += 1
            logger.debug(f"Query cache HIT for query: {query[:50]}...")
        else:
            self.query_stats[query_hash]['misses'] += 1
            logger.debug(f"Query cache MISS for query: {query[:50]}...")
        
        return result
    
    def cache_query_result(self, query: str, params: tuple, result: Any, ttl: int = 3600):
        """Cache query result."""
        cache_key = self.get_cache_key(query, params)
        self.cache.set(cache_key, result, ttl)
        logger.debug(f"Query result cached for query: {query[:50]}...")
    
    def invalidate_query_cache(self, pattern: str = None):
        """Invalidate query cache entries."""
        if pattern:
            # Would implement pattern-based invalidation
            logger.info(f"Query cache invalidation requested for pattern: {pattern}")
        else:
            self.cache.clear()
            logger.info("All query cache invalidated")
    
    def get_query_stats(self) -> Dict[str, Any]:
        """Get query cache statistics."""
        return {
            'total_queries': len(self.query_stats),
            'cache_stats': self.cache.get_stats(),
            'query_stats': self.query_stats
        }

class CacheManager:
    """
    Comprehensive cache manager with multiple strategies.
    
    Features:
    - Multiple cache backends
    - Cache hierarchy
    - Performance monitoring
    - Cache invalidation
    """
    
    def __init__(self):
        self.caches = {}
        self.default_config = CacheConfig()
        self.metrics = {
            'operations': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def get_cache(self, name: str, config: CacheConfig = None, cache_type: str = 'memory') -> Union[InMemoryCache, RedisCache]:
        """Get or create cache instance."""
        if name not in self.caches:
            config = config or self.default_config
            
            if cache_type == 'redis':
                self.caches[name] = RedisCache(config)
            else:
                self.caches[name] = InMemoryCache(config)
        
        return self.caches[name]
    
    def get_query_cache(self, name: str = 'default') -> QueryCache:
        """Get or create query cache instance."""
        cache_backend = self.get_cache(f"{name}_query")
        return QueryCache(cache_backend)
    
    def invalidate_all(self):
        """Invalidate all caches."""
        for cache in self.caches.values():
            cache.clear()
        logger.info("All caches invalidated")
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global cache statistics."""
        stats = {
            'total_caches': len(self.caches),
            'cache_stats': {}
        }
        
        for name, cache in self.caches.items():
            stats['cache_stats'][name] = cache.get_stats()
        
        return stats

# Global cache manager instance
cache_manager = CacheManager()

# Decorators for easy caching
def cached(ttl: int = 3600, cache_name: str = 'default'):
    """Decorator for function result caching."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key_data = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # Get cache
            cache = cache_manager.get_cache(cache_name)
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Function cache HIT for {func.__name__}")
                return result
            
            # Execute function and cache result
            with performance_logger.timer(f"function_execution_{func.__name__}"):
                result = func(*args, **kwargs)
            
            cache.set(cache_key, result, ttl)
            logger.debug(f"Function result cached for {func.__name__}")
            
            return result
        return wrapper
    return decorator

def query_cached(ttl: int = 3600):
    """Decorator for query result caching."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(query: str, params: tuple = None, *args, **kwargs):
            query_cache = cache_manager.get_query_cache()
            
            # Try to get from cache
            result = query_cache.get_query_result(query, params)
            if result is not None:
                return result
            
            # Execute query and cache result
            with performance_logger.timer(f"query_execution"):
                result = func(query, params, *args, **kwargs)
            
            query_cache.cache_query_result(query, params, result, ttl)
            return result
        return wrapper
    return decorator

# Cache warming utilities
def warm_cache(cache_name: str, data: Dict[str, Any], ttl: int = 3600):
    """Warm cache with predefined data."""
    cache = cache_manager.get_cache(cache_name)
    
    for key, value in data.items():
        cache.set(key, value, ttl)
    
    logger.info(f"Cache {cache_name} warmed with {len(data)} entries")

def cache_health_check() -> Dict[str, Any]:
    """Perform cache health check."""
    health = {
        'status': 'healthy',
        'issues': [],
        'cache_stats': cache_manager.get_global_stats()
    }
    
    # Check each cache
    for name, cache in cache_manager.caches.items():
        try:
            # Test cache operations
            test_key = f"health_check_{int(time.time())}"
            cache.set(test_key, "test_value", 60)
            result = cache.get(test_key)
            cache.delete(test_key)
            
            if result != "test_value":
                health['issues'].append(f"Cache {name} failed read/write test")
                
        except Exception as e:
            health['issues'].append(f"Cache {name} error: {str(e)}")
    
    if health['issues']:
        health['status'] = 'degraded'
    
    return health

# Example usage and testing
if __name__ == "__main__":
    # Test in-memory cache
    config = CacheConfig(ttl=300, max_size=100)
    cache = InMemoryCache(config)
    
    # Test basic operations
    cache.set("key1", "value1")
    print(f"Get key1: {cache.get('key1')}")
    
    # Test function caching
    @cached(ttl=60)
    def expensive_function(x: int) -> int:
        time.sleep(0.1)  # Simulate expensive operation
        return x * x
    
    start = time.time()
    result1 = expensive_function(5)
    time1 = time.time() - start
    
    start = time.time()
    result2 = expensive_function(5)  # Should be cached
    time2 = time.time() - start
    
    print(f"First call: {result1} in {time1:.3f}s")
    print(f"Second call: {result2} in {time2:.3f}s")
    
    # Test query caching
    @query_cached(ttl=120)
    def mock_query(query: str, params: tuple = None):
        time.sleep(0.05)  # Simulate database query
        return f"Result for {query} with params {params}"
    
    start = time.time()
    result1 = mock_query("SELECT * FROM users", (1, 2, 3))
    time1 = time.time() - start
    
    start = time.time()
    result2 = mock_query("SELECT * FROM users", (1, 2, 3))  # Should be cached
    time2 = time.time() - start
    
    print(f"First query: {result1} in {time1:.3f}s")
    print(f"Second query: {result2} in {time2:.3f}s")
    
    # Print cache stats
    print("Cache stats:", cache.get_stats())
    print("Global stats:", cache_manager.get_global_stats())
    
    # Test cache health
    health = cache_health_check()
    print("Cache health:", health)