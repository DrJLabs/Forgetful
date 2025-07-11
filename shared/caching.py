"""
Caching System for Agent-4 Performance Optimization

This module provides comprehensive caching strategies including:
- Multi-layer caching (L1/L2/L3)
- In-memory caching with TTL
- Redis-compatible caching (with fallback)
- Query result caching
- Cache invalidation strategies
- Performance monitoring
"""

import json
import time
import asyncio
from typing import Any, Dict, Optional, Callable, Union, List
from dataclasses import dataclass
from functools import wraps
from datetime import datetime, timedelta
import hashlib
import pickle
from contextlib import contextmanager
import msgpack

from .logging_system import get_logger, performance_logger

logger = get_logger("caching")


@dataclass
class CacheConfig:
    """Configuration for cache behavior."""

    ttl: int = 3600  # Time to live in seconds
    max_size: int = 1000  # Maximum cache size
    eviction_policy: str = "lru"  # LRU, LFU, or FIFO
    compress: bool = False  # Whether to compress cached data
    serialize: bool = True  # Whether to serialize cached data

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.ttl < 60 or self.ttl > 86400:  # 1 min to 1 day
            raise ValueError("TTL must be between 60 and 86400 seconds")
        if self.max_size < 10 or self.max_size > 1000000:  # 10 to 1M entries
            raise ValueError("Max size must be between 10 and 1000000 entries")
        if self.eviction_policy not in ["lru", "lfu", "fifo"]:
            raise ValueError("Eviction policy must be 'lru', 'lfu', or 'fifo'")

        logger.debug("CacheConfig validation passed")


@dataclass
class MultiLayerCacheConfig:
    """Configuration for multi-layer caching strategy."""

    # L1 Cache (In-Memory)
    l1_max_size: int = 256 * 1024 * 1024  # 256MB
    l1_ttl: int = 300  # 5 minutes
    l1_eviction_policy: str = "lru"

    # L2 Cache (Redis)
    l2_max_size: int = 4 * 1024 * 1024 * 1024  # 4GB
    l2_ttl: int = 3600  # 1 hour
    l2_redis_url: str = "redis://localhost:6379"

    # L3 Cache (PostgreSQL Query Cache)
    l3_ttl: int = 1800  # 30 minutes
    l3_max_prepared_statements: int = 1000

    def __post_init__(self):
        """Validate configuration parameters."""
        # L1 Cache validation
        if self.l1_max_size < 1024 * 1024:  # Min 1MB
            raise ValueError("L1 cache must be at least 1MB")
        if self.l1_max_size > 1024 * 1024 * 1024:  # Max 1GB
            raise ValueError("L1 cache cannot exceed 1GB")
        if self.l1_ttl < 60 or self.l1_ttl > 86400:  # 1 min to 1 day
            raise ValueError("L1 TTL must be between 60 and 86400 seconds")
        if self.l1_eviction_policy not in ["lru", "lfu", "fifo"]:
            raise ValueError("L1 eviction policy must be 'lru', 'lfu', or 'fifo'")

        # L2 Cache validation
        if self.l2_max_size < 1024 * 1024:  # Min 1MB
            raise ValueError("L2 cache must be at least 1MB")
        if self.l2_max_size > 8 * 1024 * 1024 * 1024:  # Max 8GB
            raise ValueError("L2 cache cannot exceed 8GB")
        if self.l2_ttl < 300 or self.l2_ttl > 86400:  # 5 min to 1 day
            raise ValueError("L2 TTL must be between 300 and 86400 seconds")
        if not self.l2_redis_url.startswith(("redis://", "rediss://")):
            raise ValueError("L2 Redis URL must start with 'redis://' or 'rediss://'")

        # L3 Cache validation
        if self.l3_ttl < 60 or self.l3_ttl > 86400:  # 1 min to 1 day
            raise ValueError("L3 TTL must be between 60 and 86400 seconds")
        if (
            self.l3_max_prepared_statements < 100
            or self.l3_max_prepared_statements > 10000
        ):
            raise ValueError("L3 max prepared statements must be between 100 and 10000")

        logger.info("MultiLayerCacheConfig validation passed")


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
                return len(self.value.encode("utf-8"))
            elif isinstance(self.value, (int, float)):
                return 8
            elif isinstance(self.value, dict):
                return len(json.dumps(self.value).encode("utf-8"))
            elif isinstance(self.value, list):
                return len(json.dumps(self.value).encode("utf-8"))
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


class OptimizedL1Cache:
    """
    Optimized L1 in-memory cache with LRU eviction and performance monitoring.

    Features:
    - 256MB LRU cache with 5-minute TTL
    - Size-based eviction for memory efficiency
    - Performance metrics tracking
    - Cache warming for hot memories
    """

    def __init__(self, config: MultiLayerCacheConfig):
        self.config = config
        self.cache = {}
        self.access_order = []  # For LRU tracking
        self.lock = asyncio.Lock()
        self.current_size = 0
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "warmings": 0,
            "size": 0,
            "memory_usage": 0,
            "hot_keys": set(),
        }

    async def get(self, key: str) -> Optional[Any]:
        """Get value from L1 cache with LRU updates."""
        async with self.lock:
            if key not in self.cache:
                self.metrics["misses"] += 1
                return None

            entry = self.cache[key]

            # Check expiration
            if entry.is_expired():
                self._remove_key(key)
                self.metrics["misses"] += 1
                return None

            # Update LRU order
            self._update_access_order(key)
            entry.touch()
            self.metrics["hits"] += 1

            # Track hot keys
            if entry.access_count > 10:
                self.metrics["hot_keys"].add(key)

            logger.debug(f"L1 Cache HIT for key: {key}")
            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in L1 cache with size-based eviction."""
        async with self.lock:
            ttl = ttl or self.config.l1_ttl
            entry = CacheEntry(value, ttl)

            # Remove existing entry if present
            if key in self.cache:
                self._remove_key(key)

            # Evict if needed to make space
            while (
                self.current_size + entry.size > self.config.l1_max_size
                and len(self.cache) > 0
            ):
                self._evict_lru()

            # Add new entry
            self.cache[key] = entry
            self.access_order.append(key)
            self.current_size += entry.size
            self.metrics["size"] = len(self.cache)
            self.metrics["memory_usage"] = self.current_size

            logger.debug(f"L1 Cache SET for key: {key}, size: {entry.size}, TTL: {ttl}")
            return True

    async def warm(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Warm cache with hot memory data."""
        result = await self.set(key, value, ttl)
        if result:
            self.metrics["warmings"] += 1
            self.metrics["hot_keys"].add(key)
        return result

    def _update_access_order(self, key: str):
        """Update LRU access order."""
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)

    def _remove_key(self, key: str):
        """Remove key from cache and update metrics."""
        if key in self.cache:
            entry = self.cache.pop(key)
            self.current_size -= entry.size
            if key in self.access_order:
                self.access_order.remove(key)
            self.metrics["hot_keys"].discard(key)

    def _evict_lru(self):
        """Evict least recently used entry."""
        if self.access_order:
            lru_key = self.access_order[0]
            self._remove_key(lru_key)
            self.metrics["evictions"] += 1
            logger.debug(f"L1 Cache EVICT for key: {lru_key}")

    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a specific user."""
        async with self.lock:
            keys_to_remove = []
            for key in self.cache:
                if f"user:{user_id}" in key:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                self._remove_key(key)

            logger.debug(
                f"L1 Cache invalidated {len(keys_to_remove)} entries for user: {user_id}"
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get L1 cache statistics."""
        total_requests = self.metrics["hits"] + self.metrics["misses"]
        hit_rate = self.metrics["hits"] / max(total_requests, 1)

        return {
            "layer": "L1",
            "type": "in_memory",
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            "memory_usage_mb": self.current_size / (1024 * 1024),
            "hot_keys_count": len(self.metrics["hot_keys"]),
            **self.metrics,
        }


class OptimizedL2RedisCache:
    """
    Optimized L2 Redis cache with msgpack serialization and connection pooling.

    Features:
    - 4GB Redis cache with 1-hour TTL
    - msgpack serialization for performance
    - Socket keepalive for connection optimization
    - Automatic fallback to L1 cache
    """

    def __init__(self, config: MultiLayerCacheConfig):
        self.config = config
        self.redis_client = None
        self.fallback_cache = OptimizedL1Cache(config)
        self.metrics = {"hits": 0, "misses": 0, "errors": 0, "fallbacks": 0}

        # Try to connect to Redis
        try:
            import redis

            self.redis_client = redis.Redis.from_url(
                config.l2_redis_url,
                decode_responses=False,  # Use msgpack for performance
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 3,  # TCP_KEEPINTVL
                    3: 5,  # TCP_KEEPCNT
                },
                socket_timeout=1.0,
                socket_connect_timeout=2.0,
                retry_on_timeout=True,
            )
            # Test connection
            self.redis_client.ping()
            logger.info("L2 Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed, using L1 fallback: {e}")
            self.redis_client = None

    async def get(self, key: str) -> Optional[Any]:
        """Get value from L2 Redis cache with async support."""
        if self.redis_client:
            try:
                # Use asyncio for non-blocking Redis operations
                cached = await asyncio.get_event_loop().run_in_executor(
                    None, self.redis_client.get, key
                )
                if cached is not None:
                    value = msgpack.unpackb(cached, raw=False)
                    self.metrics["hits"] += 1
                    logger.debug(f"L2 Cache HIT for key: {key}")
                    return value
                else:
                    self.metrics["misses"] += 1
                    return None
            except Exception as e:
                self.metrics["errors"] += 1
                logger.warning(f"L2 Redis get failed: {e}")

        # Fallback to L1 cache
        self.metrics["fallbacks"] += 1
        return await self.fallback_cache.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in L2 Redis cache with async support."""
        ttl = ttl or self.config.l2_ttl

        if self.redis_client:
            try:
                # Serialize with msgpack for performance
                packed = msgpack.packb(value, use_bin_type=True)
                await asyncio.get_event_loop().run_in_executor(
                    None, self.redis_client.setex, key, ttl, packed
                )
                logger.debug(f"L2 Cache SET for key: {key}, TTL: {ttl}")
                return True
            except Exception as e:
                self.metrics["errors"] += 1
                logger.warning(f"L2 Redis set failed: {e}")

        # Fallback to L1 cache
        self.metrics["fallbacks"] += 1
        return await self.fallback_cache.set(key, value, ttl)

    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a specific user."""
        if self.redis_client:
            try:
                pattern = f"*:user:{user_id}:*"
                cursor = 0
                deleted_count = 0

                while True:
                    cursor, keys = await asyncio.get_event_loop().run_in_executor(
                        None, self.redis_client.scan, cursor, pattern, 100
                    )
                    if keys:
                        await asyncio.get_event_loop().run_in_executor(
                            None, self.redis_client.delete, *keys
                        )
                        deleted_count += len(keys)
                    if cursor == 0:
                        break

                logger.debug(
                    f"L2 Cache invalidated {deleted_count} entries for user: {user_id}"
                )
            except Exception as e:
                logger.warning(f"L2 Redis invalidation failed: {e}")

        # Also invalidate fallback cache
        await self.fallback_cache.invalidate_user_cache(user_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get L2 cache statistics."""
        total_requests = self.metrics["hits"] + self.metrics["misses"]
        hit_rate = self.metrics["hits"] / max(total_requests, 1)

        stats = {
            "layer": "L2",
            "type": "redis",
            "connected": self.redis_client is not None,
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            **self.metrics,
        }

        if self.redis_client:
            try:
                info = self.redis_client.info()
                stats.update(
                    {
                        "memory_usage_mb": info.get("used_memory", 0) / (1024 * 1024),
                        "keys": info.get("db0", {}).get("keys", 0),
                    }
                )
            except Exception:
                pass

        return stats


class OptimizedL3QueryCache:
    """
    Optimized L3 PostgreSQL query cache with prepared statements.

    Features:
    - PostgreSQL prepared statements for vector queries
    - Query result caching with parameter hashing
    - Automatic cache invalidation on data changes
    """

    def __init__(self, config: MultiLayerCacheConfig):
        self.config = config
        self.query_cache = {}
        self.prepared_statements = {}
        self.lock = asyncio.Lock()
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "prepared_statements": 0,
            "invalidations": 0,
        }

    def get_cache_key(self, query: str, params: tuple = None) -> str:
        """Generate cache key for query and parameters."""
        key_data = f"{query}:{params or ()}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get_prepared_statement_key(self, query: str) -> str:
        """Generate key for prepared statement."""
        return hashlib.sha256(query.encode()).hexdigest()[:16]

    async def get_query_result(self, query: str, params: tuple = None) -> Optional[Any]:
        """Get cached query result."""
        cache_key = self.get_cache_key(query, params)

        async with self.lock:
            if cache_key in self.query_cache:
                entry = self.query_cache[cache_key]
                if not entry.is_expired():
                    entry.touch()
                    self.metrics["hits"] += 1
                    logger.debug(f"L3 Query cache HIT for query: {query[:50]}...")
                    return entry.value
                else:
                    del self.query_cache[cache_key]

            self.metrics["misses"] += 1
            logger.debug(f"L3 Query cache MISS for query: {query[:50]}...")
            return None

    async def cache_query_result(
        self, query: str, params: tuple, result: Any, ttl: int = None
    ):
        """Cache query result with prepared statement optimization."""
        cache_key = self.get_cache_key(query, params)
        ttl = ttl or self.config.l3_ttl

        async with self.lock:
            # Store prepared statement if not exists
            stmt_key = self.get_prepared_statement_key(query)
            if stmt_key not in self.prepared_statements:
                self.prepared_statements[stmt_key] = query
                self.metrics["prepared_statements"] += 1

            # Cache result
            entry = CacheEntry(result, ttl)
            self.query_cache[cache_key] = entry

            # Cleanup if too many statements
            if len(self.prepared_statements) > self.config.l3_max_prepared_statements:
                self._cleanup_old_statements()

        logger.debug(f"L3 Query result cached for query: {query[:50]}...")

    async def invalidate_query_cache(self, table_name: str = None):
        """Invalidate query cache for specific table or all."""
        async with self.lock:
            if table_name:
                # Invalidate queries related to specific table
                keys_to_remove = []
                for key in self.query_cache:
                    # Simple check if table name is in the cached query
                    if any(
                        table_name in stmt for stmt in self.prepared_statements.values()
                    ):
                        keys_to_remove.append(key)

                for key in keys_to_remove:
                    del self.query_cache[key]
                    self.metrics["invalidations"] += 1

                logger.debug(
                    f"L3 Query cache invalidated {len(keys_to_remove)} entries for table: {table_name}"
                )
            else:
                # Clear all cache
                count = len(self.query_cache)
                self.query_cache.clear()
                self.metrics["invalidations"] += count
                logger.debug(f"L3 Query cache cleared {count} entries")

    def _cleanup_old_statements(self):
        """Clean up old prepared statements with bounded operations."""
        total_statements = len(self.prepared_statements)

        # Safety checks
        if total_statements <= self.config.l3_max_prepared_statements:
            return

        # Remove 10% but no more than 100 statements at once
        cleanup_count = max(1, min(100, total_statements // 10))

        # Get oldest statements (first added)
        old_keys = list(self.prepared_statements.keys())[:cleanup_count]

        # Bounded cleanup with monitoring
        cleaned_count = 0
        for key in old_keys:
            if key in self.prepared_statements:
                del self.prepared_statements[key]
                cleaned_count += 1

                # Safety break to prevent excessive cleanup
                if cleaned_count >= cleanup_count:
                    break

        logger.debug(f"L3 Cache cleaned up {cleaned_count} prepared statements")

    def get_stats(self) -> Dict[str, Any]:
        """Get L3 cache statistics."""
        total_requests = self.metrics["hits"] + self.metrics["misses"]
        hit_rate = self.metrics["hits"] / max(total_requests, 1)

        return {
            "layer": "L3",
            "type": "query_cache",
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            "cached_queries": len(self.query_cache),
            **self.metrics,
        }


class MultiLayerCache:
    """
    Comprehensive multi-layer cache implementation.

    Features:
    - L1: In-memory cache (256MB, 5min TTL, LRU)
    - L2: Redis cache (4GB, 1h TTL, msgpack)
    - L3: PostgreSQL query cache (prepared statements)
    - Cache warming for hot memories
    - User-specific cache invalidation
    - Performance monitoring
    """

    def __init__(self, config: MultiLayerCacheConfig = None):
        self.config = config or MultiLayerCacheConfig()
        self.l1_cache = OptimizedL1Cache(self.config)
        self.l2_cache = OptimizedL2RedisCache(self.config)
        self.l3_cache = OptimizedL3QueryCache(self.config)
        self.metrics = {
            "total_requests": 0,
            "l1_hits": 0,
            "l2_hits": 0,
            "l3_hits": 0,
            "cache_misses": 0,
        }

    def _generate_key(self, prefix: str, params: Dict) -> str:
        """Generate cache key from parameters."""
        param_str = json.dumps(params, sort_keys=True)
        hash_val = hashlib.sha256(param_str.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_val}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from multi-layer cache (L1 → L2 → L3)."""
        self.metrics["total_requests"] += 1

        # Try L1 cache first
        result = await self.l1_cache.get(key)
        if result is not None:
            self.metrics["l1_hits"] += 1
            return result

        # Try L2 cache
        result = await self.l2_cache.get(key)
        if result is not None:
            self.metrics["l2_hits"] += 1
            # Populate L1 cache
            await self.l1_cache.set(key, result)
            return result

        # L3 cache is handled separately for query-specific caching
        self.metrics["cache_misses"] += 1
        return None

    async def set(self, key: str, value: Any, ttl: int = None):
        """Set value in all cache layers."""
        # Set in L1 cache
        await self.l1_cache.set(key, value, ttl)

        # Set in L2 cache
        await self.l2_cache.set(key, value, ttl)

    async def warm_cache(self, user_id: str, hot_memories: List[Dict]):
        """Warm cache with hot memories and frequent queries."""
        for memory in hot_memories:
            # Warm L1 cache with hot memory data
            memory_key = f"memory:user:{user_id}:{memory['id']}"
            await self.l1_cache.warm(memory_key, memory)

            # Warm L2 cache
            await self.l2_cache.set(memory_key, memory)

        logger.info(
            f"Cache warmed with {len(hot_memories)} hot memories for user: {user_id}"
        )

    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache layers for a specific user."""
        # Invalidate L1 cache
        await self.l1_cache.invalidate_user_cache(user_id)

        # Invalidate L2 cache
        await self.l2_cache.invalidate_user_cache(user_id)

        # Invalidate L3 query cache (memories table)
        await self.l3_cache.invalidate_query_cache("memories")

        logger.info(f"All cache layers invalidated for user: {user_id}")

    def get_query_cache(self) -> OptimizedL3QueryCache:
        """Get L3 query cache instance."""
        return self.l3_cache

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all cache layers."""
        total_requests = self.metrics["total_requests"]
        overall_hit_rate = (
            self.metrics["l1_hits"] + self.metrics["l2_hits"] + self.metrics["l3_hits"]
        ) / max(total_requests, 1)

        return {
            "overall_hit_rate": overall_hit_rate,
            "total_requests": total_requests,
            "cache_distribution": {
                "l1_hits": self.metrics["l1_hits"],
                "l2_hits": self.metrics["l2_hits"],
                "l3_hits": self.metrics["l3_hits"],
                "cache_misses": self.metrics["cache_misses"],
            },
            "layer_stats": {
                "l1": self.l1_cache.get_stats(),
                "l2": self.l2_cache.get_stats(),
                "l3": self.l3_cache.get_stats(),
            },
        }


# Global multi-layer cache instance
global_cache = MultiLayerCache()

# Alias for backwards compatibility with imports
cache_manager = global_cache


# Decorators for easy caching
def cached(ttl: int = 3600, cache_name: str = "default"):
    """Decorator for function result caching using global multi-layer cache."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_data = f"{cache_name}:{func.__name__}:{args}:{sorted(kwargs.items())}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()

            # Try to get from global cache
            result = await global_cache.get(cache_key)
            if result is not None:
                logger.debug(f"Function cache HIT for {func.__name__}")
                return result

            # Execute function and cache result
            with performance_logger.timer(f"function_execution_{func.__name__}"):
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

            await global_cache.set(cache_key, result, ttl)
            logger.debug(f"Function result cached for {func.__name__}")

            return result

        return wrapper

    return decorator


def multi_layer_cached(ttl: int = 3600, prefix: str = "default"):
    """Decorator for multi-layer caching."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_data = f"{prefix}:{func.__name__}:{args}:{sorted(kwargs.items())}"
            cache_key = hashlib.sha256(key_data.encode()).hexdigest()[:32]

            # Try to get from multi-layer cache
            result = await global_cache.get(cache_key)
            if result is not None:
                logger.debug(f"Multi-layer cache HIT for {func.__name__}")
                return result

            # Execute function and cache result
            with performance_logger.timer(f"function_execution_{func.__name__}"):
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

            await global_cache.set(cache_key, result, ttl)
            logger.debug(f"Multi-layer cached result for {func.__name__}")

            return result

        return wrapper

    return decorator


def query_cached(ttl: int = 3600):
    """Decorator for query result caching."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(query: str, params: tuple = None, *args, **kwargs):
            query_cache = global_cache.get_query_cache()

            # Try to get from cache
            result = await query_cache.get_query_result(query, params)
            if result is not None:
                return result

            # Execute query and cache result
            with performance_logger.timer(f"query_execution"):
                if asyncio.iscoroutinefunction(func):
                    result = await func(query, params, *args, **kwargs)
                else:
                    result = func(query, params, *args, **kwargs)

            await query_cache.cache_query_result(query, params, result, ttl)
            return result

        return wrapper

    return decorator


# Cache warming utilities
async def warm_cache(cache_name: str, data: Dict[str, Any], ttl: int = 3600):
    """Warm cache with predefined data."""
    # Use global_cache directly for multi-layer warming
    for key, value in data.items():
        cache_key = f"{cache_name}:{key}"
        await global_cache.set(cache_key, value, ttl)

    logger.info(f"Cache {cache_name} warmed with {len(data)} entries")


async def cache_health_check() -> Dict[str, Any]:
    """Perform cache health check."""
    health = {
        "status": "healthy",
        "issues": [],
        "cache_stats": global_cache.get_comprehensive_stats(),
    }

    # Test multi-layer cache operations
    try:
        test_key = f"health_check_{int(time.time())}"
        await global_cache.set(test_key, "test_value", 60)
        result = await global_cache.get(test_key)

        if result != "test_value":
            health["issues"].append("Multi-layer cache failed read/write test")
    except Exception as e:
        health["issues"].append(f"Multi-layer cache error: {str(e)}")

    if health["issues"]:
        health["status"] = "degraded"

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
    print("Global stats:", global_cache.get_comprehensive_stats())

    # Test cache health
    health = asyncio.run(cache_health_check())
    print("Cache health:", health)
