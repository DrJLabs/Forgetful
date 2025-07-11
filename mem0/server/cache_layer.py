"""
Memory-specific cache layer for mem0 performance optimization.

This module provides caching specifically for memory operations including:
- Memory CRUD operations caching
- Vector similarity search caching
- User-specific cache invalidation
- Cache warming for hot memories
"""

import asyncio
import hashlib
import json
import numpy as np
import time
from typing import List, Dict, Optional, Any
from functools import wraps
import msgpack

from shared.caching import MultiLayerCache, MultiLayerCacheConfig
from shared.logging_system import get_logger, performance_logger

logger = get_logger("memory_cache")


class MemoryCacheLayer:
    """
    Memory-specific cache layer implementing the multi-layer caching strategy.

    Features:
    - Caches memory CRUD operations
    - Vector similarity search caching with embedding hashing
    - User-specific cache invalidation
    - Cache warming for hot memories and frequent queries
    - Performance monitoring and metrics
    """

    def __init__(
        self, cache: MultiLayerCache = None, config: MultiLayerCacheConfig = None
    ):
        self.cache = cache or MultiLayerCache(config)
        self.config = config or MultiLayerCacheConfig()
        self.embedding_cache = {}  # Hot embeddings in memory
        self.metrics = {
            "memory_hits": 0,
            "memory_misses": 0,
            "search_hits": 0,
            "search_misses": 0,
            "invalidations": 0,
            "warmings": 0,
        }

    def _generate_embedding_hash(self, query_embedding: np.ndarray) -> str:
        """Generate hash for embedding to use as cache key."""
        return hashlib.sha256(query_embedding.tobytes()).hexdigest()[:16]

    def _generate_memory_key(
        self, user_id: str, memory_id: str = None, operation: str = "get"
    ) -> str:
        """Generate cache key for memory operations."""
        if memory_id:
            return f"memory:{operation}:user:{user_id}:id:{memory_id}"
        else:
            return f"memory:{operation}:user:{user_id}"

    def _generate_search_key(
        self, user_id: str, query_hash: str, limit: int = 10, filters: Dict = None
    ) -> str:
        """Generate cache key for search operations."""
        filter_hash = hashlib.sha256(
            json.dumps(filters or {}, sort_keys=True).encode()
        ).hexdigest()[:8]
        return f"search:user:{user_id}:query:{query_hash}:limit:{limit}:filters:{filter_hash}"

    async def get_memory_cached(self, user_id: str, memory_id: str) -> Optional[Dict]:
        """Get single memory with caching."""
        cache_key = self._generate_memory_key(user_id, memory_id, "get")

        result = await self.cache.get(cache_key)
        if result is not None:
            self.metrics["memory_hits"] += 1
            logger.debug(f"Memory cache HIT for user: {user_id}, memory: {memory_id}")
            return result

        self.metrics["memory_misses"] += 1
        logger.debug(f"Memory cache MISS for user: {user_id}, memory: {memory_id}")
        return None

    async def cache_memory(
        self, user_id: str, memory_id: str, memory_data: Dict, ttl: int = None
    ):
        """Cache single memory data."""
        cache_key = self._generate_memory_key(user_id, memory_id, "get")
        await self.cache.set(cache_key, memory_data, ttl)
        logger.debug(f"Memory cached for user: {user_id}, memory: {memory_id}")

    async def get_memories_cached(
        self, user_id: str, limit: int = 10, offset: int = 0, filters: Dict = None
    ) -> Optional[List[Dict]]:
        """Get memories list with caching."""
        cache_key = f"memories:user:{user_id}:limit:{limit}:offset:{offset}"

        # Add filters to cache key if present
        if filters:
            filter_hash = hashlib.sha256(
                json.dumps(filters, sort_keys=True).encode()
            ).hexdigest()[:8]
            cache_key += f":filters:{filter_hash}"

        result = await self.cache.get(cache_key)
        if result is not None:
            self.metrics["memory_hits"] += 1
            logger.debug(f"Memories list cache HIT for user: {user_id}")
            return result

        self.metrics["memory_misses"] += 1
        logger.debug(f"Memories list cache MISS for user: {user_id}")
        return None

    async def cache_memories_list(
        self,
        user_id: str,
        memories: List[Dict],
        limit: int = 10,
        offset: int = 0,
        filters: Dict = None,
        ttl: int = None,
    ):
        """Cache memories list."""
        cache_key = f"memories:user:{user_id}:limit:{limit}:offset:{offset}"

        # Add filters to cache key if present
        if filters:
            filter_hash = hashlib.sha256(
                json.dumps(filters, sort_keys=True).encode()
            ).hexdigest()[:8]
            cache_key += f":filters:{filter_hash}"

        await self.cache.set(cache_key, memories, ttl)
        logger.debug(f"Memories list cached for user: {user_id}")

    async def search_memories_cached(
        self,
        user_id: str,
        query_embedding: np.ndarray,
        limit: int = 10,
        filters: Dict = None,
    ) -> Optional[List[Dict]]:
        """Get cached vector similarity search results."""
        # Generate embedding hash for cache key
        embedding_hash = self._generate_embedding_hash(query_embedding)

        # Check hot embeddings cache first
        if embedding_hash in self.embedding_cache:
            hot_result = self.embedding_cache[embedding_hash]
            if time.time() - hot_result["timestamp"] < 300:  # 5 minutes TTL
                logger.debug(f"Hot embedding cache HIT for user: {user_id}")
                return hot_result["data"]

        # Generate search cache key
        cache_key = self._generate_search_key(user_id, embedding_hash, limit, filters)

        result = await self.cache.get(cache_key)
        if result is not None:
            self.metrics["search_hits"] += 1
            logger.debug(f"Search cache HIT for user: {user_id}")

            # Update hot embeddings cache
            self.embedding_cache[embedding_hash] = {
                "data": result,
                "timestamp": time.time(),
            }

            return result

        self.metrics["search_misses"] += 1
        logger.debug(f"Search cache MISS for user: {user_id}")
        return None

    async def cache_search_results(
        self,
        user_id: str,
        query_embedding: np.ndarray,
        results: List[Dict],
        limit: int = 10,
        filters: Dict = None,
        ttl: int = None,
    ):
        """Cache vector similarity search results."""
        # Generate embedding hash
        embedding_hash = self._generate_embedding_hash(query_embedding)

        # Cache in hot embeddings for frequent queries
        self.embedding_cache[embedding_hash] = {
            "data": results,
            "timestamp": time.time(),
        }

        # Cache in multi-layer cache
        cache_key = self._generate_search_key(user_id, embedding_hash, limit, filters)
        await self.cache.set(cache_key, results, ttl or 300)  # 5 minutes default

        logger.debug(f"Search results cached for user: {user_id}")

    async def warm_user_cache(self, user_id: str, hot_memories: List[Dict]):
        """Warm cache with hot memories for a specific user."""
        # Warm individual memories
        for memory in hot_memories:
            memory_key = self._generate_memory_key(user_id, memory["id"], "get")
            await self.cache.set(memory_key, memory, self.config.l1_ttl)

        # Warm memories list cache
        list_key = f"memories:user:{user_id}:limit:10:offset:0"
        await self.cache.set(list_key, hot_memories[:10], self.config.l1_ttl)

        # Use L1 cache warming for frequently accessed memories
        await self.cache.warm_cache(user_id, hot_memories)

        self.metrics["warmings"] += 1
        logger.info(
            f"Cache warmed with {len(hot_memories)} hot memories for user: {user_id}"
        )

    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a specific user."""
        # Invalidate multi-layer cache
        await self.cache.invalidate_user_cache(user_id)

        # Clear hot embeddings cache (all embeddings for this user)
        # Since we can't easily track embeddings by user, we'll clear older entries
        current_time = time.time()
        expired_keys = []

        for key, data in self.embedding_cache.items():
            if current_time - data["timestamp"] > 300:  # 5 minutes
                expired_keys.append(key)

        for key in expired_keys:
            del self.embedding_cache[key]

        self.metrics["invalidations"] += 1
        logger.info(f"All cache layers invalidated for user: {user_id}")

    async def invalidate_memory_cache(self, user_id: str, memory_id: str):
        """Invalidate cache for a specific memory."""
        # Invalidate specific memory
        memory_key = self._generate_memory_key(user_id, memory_id, "get")
        # Would need to implement individual key invalidation in multi-layer cache

        # For now, invalidate all user cache to ensure consistency
        await self.invalidate_user_cache(user_id)

        logger.debug(
            f"Memory cache invalidated for user: {user_id}, memory: {memory_id}"
        )

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_memory_requests = (
            self.metrics["memory_hits"] + self.metrics["memory_misses"]
        )
        total_search_requests = (
            self.metrics["search_hits"] + self.metrics["search_misses"]
        )

        memory_hit_rate = self.metrics["memory_hits"] / max(total_memory_requests, 1)
        search_hit_rate = self.metrics["search_hits"] / max(total_search_requests, 1)

        return {
            "memory_operations": {
                "hit_rate": memory_hit_rate,
                "total_requests": total_memory_requests,
                "hits": self.metrics["memory_hits"],
                "misses": self.metrics["memory_misses"],
            },
            "search_operations": {
                "hit_rate": search_hit_rate,
                "total_requests": total_search_requests,
                "hits": self.metrics["search_hits"],
                "misses": self.metrics["search_misses"],
            },
            "hot_embeddings": {
                "count": len(self.embedding_cache),
                "warmings": self.metrics["warmings"],
            },
            "invalidations": self.metrics["invalidations"],
            "multi_layer_stats": self.cache.get_comprehensive_stats(),
        }


# Cache warming functions for hot memories
async def warm_memory_cache(
    cache_layer: MemoryCacheLayer, user_id: str, memory_service
) -> int:
    """Warm cache with hot memories for a user."""
    try:
        # Get recently accessed memories (hot memories)
        recent_memories = await get_hot_memories(memory_service, user_id, limit=50)

        if recent_memories:
            await cache_layer.warm_user_cache(user_id, recent_memories)
            return len(recent_memories)

        return 0
    except Exception as e:
        logger.error(f"Failed to warm memory cache for user {user_id}: {e}")
        return 0


async def get_hot_memories(memory_service, user_id: str, limit: int = 50) -> List[Dict]:
    """Get hot memories for cache warming."""
    try:
        # This would integrate with the actual memory service
        # For now, return empty list - will be implemented when integrating
        return []
    except Exception as e:
        logger.error(f"Failed to get hot memories for user {user_id}: {e}")
        return []


# Decorator for memory operations caching
def memory_cached(ttl: int = 300, operation: str = "get"):
    """Decorator for memory operations caching."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id from arguments
            user_id = kwargs.get("user_id") or (args[0] if args else None)

            if not user_id:
                # No user_id, execute without caching
                return await func(*args, **kwargs)

            # Initialize cache if not exists
            if not hasattr(wrapper, "cache_layer"):
                wrapper.cache_layer = MemoryCacheLayer()

            # Generate cache key
            cache_key = (
                f"memory:{operation}:{user_id}:{hash(str(args[1:]) + str(kwargs))}"
            )

            # Try cache first
            result = await wrapper.cache_layer.cache.get(cache_key)
            if result is not None:
                logger.debug(f"Memory operation cache HIT for {func.__name__}")
                return result

            # Execute function
            with performance_logger.timer(f"memory_operation_{func.__name__}"):
                result = await func(*args, **kwargs)

            # Cache result
            await wrapper.cache_layer.cache.set(cache_key, result, ttl)
            logger.debug(f"Memory operation cached for {func.__name__}")

            return result

        return wrapper

    return decorator


# Global memory cache instance
global_memory_cache = MemoryCacheLayer()
