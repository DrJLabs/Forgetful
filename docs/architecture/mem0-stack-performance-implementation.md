# mem0-Stack Performance Implementation Guide

## Overview

This guide provides concrete implementation details for achieving sub-100ms memory operations in mem0-stack. Each optimization includes code samples that can be directly integrated into the existing codebase.

## 1. Multi-Layer Caching Implementation

### Redis Cache Layer Setup

```python
# shared/caching.py - Enhanced caching implementation
import redis
import asyncio
import json
import hashlib
from typing import Optional, Any, Dict
from functools import wraps
import msgpack

class MultiLayerCache:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.Redis.from_url(
            redis_url, 
            decode_responses=False,  # Use msgpack for performance
            socket_keepalive=True,
            socket_keepalive_options={
                1: 1,  # TCP_KEEPIDLE
                2: 3,  # TCP_KEEPINTVL
                3: 5   # TCP_KEEPCNT
            }
        )
        self.local_cache: Dict[str, Any] = {}
        self.local_cache_size = 0
        self.max_local_cache_size = 256 * 1024 * 1024  # 256MB
        
    def _generate_key(self, prefix: str, params: Dict) -> str:
        """Generate cache key from parameters"""
        param_str = json.dumps(params, sort_keys=True)
        hash_val = hashlib.sha256(param_str.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_val}"
    
    async def get_cached(self, key: str) -> Optional[Any]:
        """Try local cache first, then Redis"""
        # L1: Local memory cache
        if key in self.local_cache:
            return self.local_cache[key]
        
        # L2: Redis cache
        try:
            cached = await asyncio.get_event_loop().run_in_executor(
                None, self.redis_client.get, key
            )
            if cached:
                value = msgpack.unpackb(cached, raw=False)
                # Populate L1 cache
                self._add_to_local_cache(key, value)
                return value
        except Exception as e:
            # Log but don't fail on cache errors
            print(f"Redis cache error: {e}")
        
        return None
    
    async def set_cached(self, key: str, value: Any, ttl: int = 300):
        """Set in both cache layers"""
        # L1: Local cache
        self._add_to_local_cache(key, value)
        
        # L2: Redis cache with msgpack serialization
        try:
            packed = msgpack.packb(value, use_bin_type=True)
            await asyncio.get_event_loop().run_in_executor(
                None, self.redis_client.setex, key, ttl, packed
            )
        except Exception as e:
            print(f"Redis set error: {e}")
    
    def _add_to_local_cache(self, key: str, value: Any):
        """LRU-style local cache management"""
        size = len(msgpack.packb(value, use_bin_type=True))
        
        # Evict if necessary
        while self.local_cache_size + size > self.max_local_cache_size:
            if not self.local_cache:
                break
            oldest_key = next(iter(self.local_cache))
            old_value = self.local_cache.pop(oldest_key)
            self.local_cache_size -= len(msgpack.packb(old_value, use_bin_type=True))
        
        self.local_cache[key] = value
        self.local_cache_size += size

# Decorator for caching FastAPI endpoints
def cached_endpoint(prefix: str, ttl: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = kwargs.get('cache')  # Injected dependency
            if not cache:
                return await func(*args, **kwargs)
            
            # Generate cache key from function arguments
            cache_key = cache._generate_key(prefix, {
                'args': str(args),
                'kwargs': str(kwargs)
            })
            
            # Try cache first
            cached_result = await cache.get_cached(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute and cache
            result = await func(*args, **kwargs)
            await cache.set_cached(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator
```

### Memory-Specific Cache Implementation

```python
# mem0/server/cache_layer.py
from typing import List, Dict, Optional
import numpy as np
from shared.caching import MultiLayerCache

class MemoryCacheLayer:
    def __init__(self, cache: MultiLayerCache):
        self.cache = cache
        self.embedding_cache = {}  # Hot embeddings in memory
        
    async def get_memories_cached(
        self, 
        user_id: str, 
        limit: int = 10,
        offset: int = 0
    ) -> Optional[List[Dict]]:
        """Get memories with caching"""
        cache_key = f"memories:{user_id}:{limit}:{offset}"
        return await self.cache.get_cached(cache_key)
    
    async def search_memories_cached(
        self,
        user_id: str,
        query_embedding: np.ndarray,
        limit: int = 10
    ) -> Optional[List[Dict]]:
        """Cached vector similarity search"""
        # Hash the embedding for cache key
        embedding_hash = hashlib.sha256(
            query_embedding.tobytes()
        ).hexdigest()[:16]
        
        cache_key = f"search:{user_id}:{embedding_hash}:{limit}"
        return await self.cache.get_cached(cache_key)
    
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all caches for a user"""
        pattern = f"*:{user_id}:*"
        cursor = 0
        
        while True:
            cursor, keys = await self.cache.redis_client.scan(
                cursor, match=pattern, count=100
            )
            if keys:
                await self.cache.redis_client.delete(*keys)
            if cursor == 0:
                break
```

## 2. Database Query Optimization

### PostgreSQL Query Optimization

```python
# mem0/vector_stores/pgvector_optimized.py
import asyncpg
from typing import List, Dict, Optional
import numpy as np

class OptimizedPgVectorStore:
    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self.pool: Optional[asyncpg.Pool] = None
        
    async def initialize(self):
        """Initialize connection pool with optimizations"""
        self.pool = await asyncpg.create_pool(
            self.connection_url,
            min_size=20,
            max_size=100,
            max_inactive_connection_lifetime=300,
            command_timeout=10,
            server_settings={
                'jit': 'off',  # Disable JIT for consistent performance
                'random_page_cost': '1.1',  # SSD optimization
                'effective_cache_size': '4GB',
                'shared_buffers': '2GB'
            },
            init=self._init_connection
        )
        
        # Create optimized indexes
        async with self.pool.acquire() as conn:
            await conn.execute("""
                -- HNSW index for fast similarity search
                CREATE INDEX IF NOT EXISTS idx_memory_embedding_hnsw 
                ON memories USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
                
                -- Composite index for user-based queries
                CREATE INDEX IF NOT EXISTS idx_memory_user_created 
                ON memories(user_id, created_at DESC);
                
                -- Partial index for active memories
                CREATE INDEX IF NOT EXISTS idx_memory_active 
                ON memories(user_id, created_at DESC) 
                WHERE is_deleted = false;
            """)
    
    async def _init_connection(self, conn):
        """Initialize each connection with prepared statements"""
        # Prepare common queries
        await conn.execute("""
            PREPARE vector_search (text, vector, int) AS
            SELECT 
                id, 
                text, 
                metadata,
                1 - (embedding <=> $2) as similarity
            FROM memories
            WHERE user_id = $1 
                AND is_deleted = false
            ORDER BY embedding <=> $2
            LIMIT $3;
        """)
        
        await conn.execute("""
            PREPARE get_recent_memories (text, int, int) AS
            SELECT id, text, metadata, created_at
            FROM memories
            WHERE user_id = $1 AND is_deleted = false
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3;
        """)
    
    async def search_similar(
        self,
        user_id: str,
        query_embedding: np.ndarray,
        limit: int = 10
    ) -> List[Dict]:
        """Optimized vector similarity search"""
        async with self.pool.acquire() as conn:
            # Use prepared statement for performance
            rows = await conn.fetch(
                "EXECUTE vector_search($1, $2, $3)",
                user_id,
                query_embedding.tolist(),
                limit
            )
            
            return [
                {
                    'id': row['id'],
                    'text': row['text'],
                    'metadata': row['metadata'],
                    'similarity': float(row['similarity'])
                }
                for row in rows
            ]
    
    async def batch_insert_memories(
        self,
        memories: List[Dict]
    ):
        """Batch insert with COPY for performance"""
        async with self.pool.acquire() as conn:
            # Use COPY for bulk inserts
            await conn.copy_records_to_table(
                'memories',
                records=[
                    (
                        m['id'],
                        m['user_id'],
                        m['text'],
                        m['embedding'],
                        m['metadata'],
                        m['created_at']
                    )
                    for m in memories
                ],
                columns=['id', 'user_id', 'text', 'embedding', 'metadata', 'created_at']
            )
```

### Neo4j Query Optimization

```python
# mem0/graphs/neo4j_optimized.py
from neo4j import AsyncGraphDatabase, AsyncSession
from typing import List, Dict
import asyncio

class OptimizedNeo4jStore:
    def __init__(self, uri: str, auth: tuple):
        self.driver = AsyncGraphDatabase.driver(
            uri, 
            auth=auth,
            max_connection_pool_size=50,
            connection_acquisition_timeout=2.0,
            max_transaction_retry_time=10.0,
            keep_alive=True
        )
        
    async def initialize(self):
        """Create indexes and constraints"""
        async with self.driver.session() as session:
            # Create indexes for performance
            await session.run("""
                CREATE INDEX memory_user_idx IF NOT EXISTS
                FOR (m:Memory) ON (m.user_id)
            """)
            
            await session.run("""
                CREATE INDEX memory_timestamp_idx IF NOT EXISTS
                FOR (m:Memory) ON (m.timestamp)
            """)
            
            await session.run("""
                CREATE INDEX memory_composite_idx IF NOT EXISTS
                FOR (m:Memory) ON (m.user_id, m.timestamp)
            """)
    
    async def find_related_memories(
        self,
        user_id: str,
        memory_id: str,
        depth: int = 2,
        limit: int = 10
    ) -> List[Dict]:
        """Optimized graph traversal"""
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (m:Memory {id: $memory_id, user_id: $user_id})
                CALL apoc.path.expandConfig(m, {
                    relationshipFilter: "RELATES_TO",
                    minLevel: 1,
                    maxLevel: $depth,
                    bfs: true,
                    limit: $limit
                }) YIELD path
                WITH nodes(path) as memories
                UNWIND memories as memory
                WITH DISTINCT memory
                WHERE memory.id <> $memory_id
                RETURN memory.id as id, 
                       memory.text as text,
                       memory.metadata as metadata
                ORDER BY memory.timestamp DESC
                LIMIT $limit
            """, 
            memory_id=memory_id,
            user_id=user_id, 
            depth=depth,
            limit=limit
            )
            
            return [dict(record) async for record in result]
    
    async def batch_create_relationships(
        self,
        relationships: List[Dict]
    ):
        """Batch relationship creation"""
        async with self.driver.session() as session:
            await session.run("""
                UNWIND $relationships as rel
                MATCH (m1:Memory {id: rel.from_id})
                MATCH (m2:Memory {id: rel.to_id})
                MERGE (m1)-[r:RELATES_TO]->(m2)
                SET r.weight = rel.weight,
                    r.created_at = timestamp()
            """, relationships=relationships)
```

## 3. Connection Pool Management

```python
# shared/connection_manager.py
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any
import time

class ConnectionPoolManager:
    def __init__(self):
        self.pools: Dict[str, Any] = {}
        self.pool_stats: Dict[str, Dict] = {}
        self._monitor_task = None
        
    async def start_monitoring(self):
        """Monitor pool health and pre-warm connections"""
        self._monitor_task = asyncio.create_task(self._monitor_pools())
    
    async def _monitor_pools(self):
        """Background task to monitor and optimize pools"""
        while True:
            for name, pool in self.pools.items():
                stats = {
                    'active': 0,
                    'idle': 0,
                    'total': 0
                }
                
                if hasattr(pool, 'size'):  # asyncpg
                    stats['active'] = pool._queue.qsize()
                    stats['total'] = pool._size
                    stats['idle'] = stats['total'] - stats['active']
                    
                    # Pre-warm connections if too few idle
                    if stats['idle'] < 5:
                        asyncio.create_task(self._prewarm_pool(pool))
                
                self.pool_stats[name] = stats
            
            await asyncio.sleep(30)  # Check every 30 seconds
    
    async def _prewarm_pool(self, pool):
        """Pre-warm connection pool"""
        try:
            # Acquire and immediately release to create new connection
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1")
        except Exception as e:
            print(f"Pre-warm error: {e}")
    
    @asynccontextmanager
    async def acquire_connection(self, pool_name: str):
        """Acquire connection with timeout and retry"""
        pool = self.pools.get(pool_name)
        if not pool:
            raise ValueError(f"Pool {pool_name} not found")
        
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                start_time = time.time()
                async with asyncio.timeout(1.0):  # 1 second timeout
                    async with pool.acquire() as conn:
                        acquisition_time = time.time() - start_time
                        
                        # Log slow acquisitions
                        if acquisition_time > 0.1:
                            print(f"Slow connection acquisition: {acquisition_time:.3f}s")
                        
                        yield conn
                        return
                        
            except asyncio.TimeoutError:
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(0.1 * retry_count)  # Exponential backoff
                else:
                    raise
```

## 4. FastAPI Integration

```python
# mem0/server/main_optimized.py
from fastapi import FastAPI, Depends, Request
from contextlib import asynccontextmanager
import uvloop
import asyncio

# Use uvloop for better async performance
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Global instances
cache_layer = None
memory_cache = None
pgvector_store = None
neo4j_store = None
pool_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all optimized components on startup"""
    global cache_layer, memory_cache, pgvector_store, neo4j_store, pool_manager
    
    # Initialize cache layer
    cache_layer = MultiLayerCache()
    memory_cache = MemoryCacheLayer(cache_layer)
    
    # Initialize optimized stores
    pgvector_store = OptimizedPgVectorStore(DATABASE_URL)
    await pgvector_store.initialize()
    
    neo4j_store = OptimizedNeo4jStore(NEO4J_URI, NEO4J_AUTH)
    await neo4j_store.initialize()
    
    # Initialize pool manager
    pool_manager = ConnectionPoolManager()
    pool_manager.pools['postgres'] = pgvector_store.pool
    pool_manager.pools['neo4j'] = neo4j_store.driver
    await pool_manager.start_monitoring()
    
    yield
    
    # Cleanup
    await pgvector_store.pool.close()
    await neo4j_store.driver.close()

app = FastAPI(lifespan=lifespan)

# Dependency injection for cache
async def get_cache():
    return cache_layer

async def get_memory_cache():
    return memory_cache

@app.post("/memories")
@cached_endpoint("create_memory", ttl=60)
async def create_memory(
    request: MemoryCreateRequest,
    cache: MemoryCacheLayer = Depends(get_memory_cache)
):
    """Optimized memory creation endpoint"""
    # Process memory creation
    memory = await process_memory_creation(request)
    
    # Invalidate relevant caches
    await cache.invalidate_user_cache(request.user_id)
    
    return memory

@app.post("/search")
async def search_memories(
    request: SearchRequest,
    cache: MemoryCacheLayer = Depends(get_memory_cache)
):
    """Optimized search endpoint with caching"""
    # Check cache first
    cached_results = await cache.search_memories_cached(
        request.user_id,
        request.query_embedding,
        request.limit
    )
    
    if cached_results is not None:
        return {"results": cached_results, "cached": True}
    
    # Perform search
    results = await pgvector_store.search_similar(
        request.user_id,
        request.query_embedding,
        request.limit
    )
    
    # Cache results
    await cache.cache.set_cached(
        f"search:{request.user_id}:{request.query_hash}:{request.limit}",
        results,
        ttl=300  # 5 minutes
    )
    
    return {"results": results, "cached": False}

# Middleware for request timing
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log slow requests
    if process_time > 0.1:  # 100ms
        print(f"Slow request: {request.url.path} took {process_time:.3f}s")
    
    return response
```

## 5. Circuit Breaker Implementation

```python
# shared/circuit_breaker.py
import asyncio
from enum import Enum
from typing import Callable, Any, Optional
import time

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception(f"Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset the circuit"""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Reset circuit breaker on success"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None
    
    def _on_failure(self):
        """Handle failure and potentially open circuit"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# Usage example for database operations
class ProtectedDatabaseOperations:
    def __init__(self):
        self.pg_circuit = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30.0,
            expected_exception=asyncpg.PostgresError
        )
        
        self.neo4j_circuit = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=45.0,
            expected_exception=Exception
        )
    
    async def search_memories(self, *args, **kwargs):
        """Protected memory search with fallback"""
        try:
            # Try primary database
            return await self.pg_circuit.call(
                self._search_postgres, *args, **kwargs
            )
        except Exception as e:
            # Fallback to cache-only mode
            print(f"Primary search failed: {e}, falling back to cache")
            return await self._search_cache_only(*args, **kwargs)
```

## Conclusion

These implementations provide the foundation for achieving sub-100ms memory operations in mem0-stack. The key optimizations include:

1. **Multi-layer caching** with local memory and Redis
2. **Optimized database queries** with prepared statements and proper indexing
3. **Connection pooling** with pre-warming and monitoring
4. **Circuit breakers** for resilience and graceful degradation
5. **Request batching** and async processing

Each component is designed to work together, providing multiple layers of performance optimization while maintaining reliability for autonomous AI agent operations. 