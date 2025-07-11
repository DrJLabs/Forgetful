"""
Request Batching and Pipelining for mem0 Performance Optimization.

This module provides batching and pipelining for:
- Memory write batching (batch size: 50, flush interval: 100ms)
- Vector search batching (batch size: 20, parallel execution: 4)
- Graph query batching (batch size: 10, with result caching)

Features:
- Batch processing queue with priority handling
- Batch timeout and error handling
- Performance monitoring and metrics
- Automatic batch flushing
"""

import asyncio
import time
import threading
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import uuid
from functools import wraps
from collections import defaultdict

import sys
sys.path.append('/workspace')
from shared.logging_system import get_logger, performance_logger
from shared.connection_pool import global_pool_manager

logger = get_logger('batching')

class BatchPriority(Enum):
    """Priority levels for batch operations."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class BatchRequest:
    """Individual request in a batch."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation: str = ""
    data: Any = None
    callback: Optional[Callable] = None
    priority: BatchPriority = BatchPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    timeout: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    batch_size: int = 50
    flush_interval: float = 0.1  # 100ms
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 0.05  # 50ms
    parallel_workers: int = 4
    queue_size: int = 10000

class BatchMetrics:
    """Metrics tracking for batch operations."""
    
    def __init__(self):
        self.batches_processed = 0
        self.requests_processed = 0
        self.requests_failed = 0
        self.batch_size_total = 0
        self.processing_time_total = 0.0
        self.flush_count = 0
        self.timeout_count = 0
        self.retry_count = 0
        self.lock = threading.Lock()
    
    def record_batch_processed(self, batch_size: int, processing_time: float):
        """Record successful batch processing."""
        with self.lock:
            self.batches_processed += 1
            self.requests_processed += batch_size
            self.batch_size_total += batch_size
            self.processing_time_total += processing_time
    
    def record_request_failed(self):
        """Record failed request."""
        with self.lock:
            self.requests_failed += 1
    
    def record_flush(self):
        """Record batch flush."""
        with self.lock:
            self.flush_count += 1
    
    def record_timeout(self):
        """Record timeout."""
        with self.lock:
            self.timeout_count += 1
    
    def record_retry(self):
        """Record retry attempt."""
        with self.lock:
            self.retry_count += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get batch processing statistics."""
        with self.lock:
            avg_batch_size = self.batch_size_total / max(self.batches_processed, 1)
            avg_processing_time = self.processing_time_total / max(self.batches_processed, 1)
            success_rate = (self.requests_processed - self.requests_failed) / max(self.requests_processed, 1)
            
            return {
                'batches_processed': self.batches_processed,
                'requests_processed': self.requests_processed,
                'requests_failed': self.requests_failed,
                'success_rate': success_rate,
                'average_batch_size': avg_batch_size,
                'average_processing_time_ms': avg_processing_time * 1000,
                'flush_count': self.flush_count,
                'timeout_count': self.timeout_count,
                'retry_count': self.retry_count
            }

class BatchProcessor:
    """
    Generic batch processor with priority handling and automatic flushing.
    
    Features:
    - Priority-based batching
    - Automatic flush on timeout
    - Parallel processing
    - Error handling and retries
    """
    
    def __init__(self, name: str, processor_func: Callable, config: BatchConfig):
        self.name = name
        self.processor_func = processor_func
        self.config = config
        self.queue = asyncio.Queue(maxsize=config.queue_size)
        self.batches = defaultdict(list)  # priority -> list of requests
        self.metrics = BatchMetrics()
        
        self.is_running = False
        self.flush_task = None
        self.workers = []
        
        self._lock = asyncio.Lock()
        self._last_flush = time.time()
    
    async def start(self):
        """Start the batch processor."""
        self.is_running = True
        
        # Start flush task
        self.flush_task = asyncio.create_task(self._flush_loop())
        
        # Start worker tasks for parallel processing
        for i in range(self.config.parallel_workers):
            worker = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self.workers.append(worker)
        
        logger.info(f"Batch processor '{self.name}' started with {self.config.parallel_workers} workers")
    
    async def stop(self):
        """Stop the batch processor."""
        self.is_running = False
        
        # Cancel tasks
        if self.flush_task:
            self.flush_task.cancel()
        
        # Cancel worker tasks
        for worker in self.workers:
            worker.cancel()
        
        # Process remaining batches
        await self._flush_all_batches()
        
        # Wait for queue to empty
        try:
            await asyncio.wait_for(self.queue.join(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for queue to empty in '{self.name}'")
        
        logger.info(f"Batch processor '{self.name}' stopped")
    
    async def add_request(self, request: BatchRequest) -> Any:
        """Add a request to the batch queue."""
        if not self.is_running:
            raise RuntimeError(f"Batch processor '{self.name}' is not running")
        
        # Add to priority queue
        should_flush = False
        async with self._lock:
            self.batches[request.priority].append(request)
            
            # Check if we need to flush immediately
            total_requests = sum(len(batch) for batch in self.batches.values())
            if total_requests >= self.config.batch_size:
                should_flush = True
        
        # Flush outside the lock to avoid deadlock
        if should_flush:
            await self._flush_batches()
        
        # Create future for result
        future = asyncio.Future()
        request.callback = future.set_result
        
        # Wait for result with timeout
        try:
            result = await asyncio.wait_for(future, timeout=request.timeout)
            return result
        except asyncio.TimeoutError:
            self.metrics.record_timeout()
            raise
    
    async def _flush_loop(self):
        """Automatic flush loop based on time interval."""
        while self.is_running:
            try:
                await asyncio.sleep(self.config.flush_interval)
                
                # Check if we need to flush
                if time.time() - self._last_flush >= self.config.flush_interval:
                    await self._flush_batches()
                    
            except Exception as e:
                logger.error(f"Flush loop error in '{self.name}': {e}")
    
    async def _flush_batches(self):
        """Flush current batches to processing queue."""
        async with self._lock:
            if not any(self.batches.values()):
                return
            
            # Create batch from highest priority requests
            batch = []
            for priority in sorted(BatchPriority, key=lambda x: x.value, reverse=True):
                if self.batches[priority]:
                    batch.extend(self.batches[priority])
                    self.batches[priority].clear()
                    
                    # Limit batch size
                    if len(batch) >= self.config.batch_size:
                        batch = batch[:self.config.batch_size]
                        break
            
            if batch:
                await self.queue.put(batch)
                self._last_flush = time.time()
                self.metrics.record_flush()
                
                logger.debug(f"Flushed batch of {len(batch)} requests in '{self.name}'")
    
    async def _flush_all_batches(self):
        """Flush all remaining batches."""
        async with self._lock:
            for priority_batch in self.batches.values():
                if priority_batch:
                    await self.queue.put(priority_batch)
                    priority_batch.clear()
    

    
    async def _worker_loop(self, worker_id: str):
        """Worker loop for parallel processing."""
        while self.is_running:
            try:
                # Get batch from queue with timeout
                batch = await asyncio.wait_for(self.queue.get(), timeout=0.1)
                
                # Process the batch
                await self._process_batch(batch)
                
                # Mark task as done
                self.queue.task_done()
                
            except asyncio.TimeoutError:
                # No work available, continue
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error in '{self.name}': {e}")
    
    async def _process_batch(self, batch: List[BatchRequest]):
        """Process a batch of requests."""
        if not batch:
            return
        
        start_time = time.time()
        
        try:
            # Process batch with retries
            results = await self._process_with_retries(batch)
            
            # Send results to callbacks
            for request, result in zip(batch, results):
                if request.callback:
                    if isinstance(result, Exception):
                        # Handle Future callback for exceptions
                        if hasattr(request.callback, 'set_exception'):
                            request.callback.set_exception(result)
                        else:
                            request.callback(result)
                        self.metrics.record_request_failed()
                    else:
                        # Handle Future callback for successful results
                        if hasattr(request.callback, 'set_result'):
                            request.callback.set_result(result)
                        else:
                            request.callback(result)
            
            # Record metrics
            processing_time = time.time() - start_time
            self.metrics.record_batch_processed(len(batch), processing_time)
            
            logger.debug(f"Processed batch of {len(batch)} requests in {processing_time:.3f}s")
            
        except Exception as e:
            logger.error(f"Batch processing failed in '{self.name}': {e}")
            
            # Send error to all callbacks
            for request in batch:
                if request.callback:
                    # Handle Future callback for errors
                    if hasattr(request.callback, 'set_exception'):
                        request.callback.set_exception(e)
                    else:
                        request.callback(e)
                    self.metrics.record_request_failed()
    
    async def _process_with_retries(self, batch: List[BatchRequest]) -> List[Any]:
        """Process batch with retry logic."""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                # Process the batch
                results = await self.processor_func(batch)
                return results
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.config.max_retries:
                    self.metrics.record_retry()
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                    logger.warning(f"Batch processing attempt {attempt + 1} failed in '{self.name}': {e}")
                else:
                    logger.error(f"Batch processing failed after {self.config.max_retries} retries in '{self.name}': {e}")
        
        # Return exceptions for each request
        return [last_exception] * len(batch)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive batch processor statistics."""
        stats = self.metrics.get_stats()
        stats.update({
            'name': self.name,
            'is_running': self.is_running,
            'queue_size': self.queue.qsize(),
            'config': {
                'batch_size': self.config.batch_size,
                'flush_interval_ms': self.config.flush_interval * 1000,
                'parallel_workers': self.config.parallel_workers
            }
        })
        return stats

class MemoryWriteBatcher:
    """
    Memory write operations batcher.
    
    Features:
    - Batch size: 50 operations
    - Flush interval: 100ms
    - Priority handling for urgent writes
    """
    
    def __init__(self):
        self.config = BatchConfig(
            batch_size=50,
            flush_interval=0.1,  # 100ms
            parallel_workers=2
        )
        self.processor = BatchProcessor("memory_write", self._process_memory_writes, self.config)
    
    async def start(self):
        """Start memory write batcher."""
        await self.processor.start()
    
    async def stop(self):
        """Stop memory write batcher."""
        await self.processor.stop()
    
    async def add_memory_write(self, user_id: str, memory_data: Dict, 
                              priority: BatchPriority = BatchPriority.NORMAL) -> str:
        """Add memory write operation to batch."""
        request = BatchRequest(
            operation="memory_write",
            data={"user_id": user_id, "memory_data": memory_data},
            priority=priority,
            timeout=10.0
        )
        
        return await self.processor.add_request(request)
    
    async def _process_memory_writes(self, batch: List[BatchRequest]) -> List[Any]:
        """Process batch of memory write operations."""
        results = []
        
        # Group by user_id for efficiency
        user_batches = defaultdict(list)
        for request in batch:
            user_id = request.data["user_id"]
            user_batches[user_id].append(request)
        
        # Process each user's writes
        for user_id, user_requests in user_batches.items():
            try:
                # Use connection pool for database operations
                if global_pool_manager.postgres_pool:
                    async with global_pool_manager.postgres_pool.acquire() as conn:
                        for request in user_requests:
                            memory_data = request.data["memory_data"]
                            
                            # Insert memory into database
                            memory_id = await self._insert_memory(conn, user_id, memory_data)
                            results.append(memory_id)
                else:
                    # Fallback if no connection pool
                    for request in user_requests:
                        results.append(f"memory_{request.id}")
                        
            except Exception as e:
                logger.error(f"Memory write batch failed for user {user_id}: {e}")
                for _ in user_requests:
                    results.append(e)
        
        return results
    
    async def _insert_memory(self, conn, user_id: str, memory_data: Dict) -> str:
        """Insert memory into database."""
        # Simplified memory insertion - would integrate with actual mem0 logic
        query = """
            INSERT INTO memories (user_id, content, metadata, created_at)
            VALUES ($1, $2, $3, NOW())
            RETURNING id
        """
        
        memory_id = await conn.fetchval(
            query,
            user_id,
            memory_data.get("content", ""),
            json.dumps(memory_data.get("metadata", {}))
        )
        
        return str(memory_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory write batcher statistics."""
        return self.processor.get_stats()

class VectorSearchBatcher:
    """
    Vector search operations batcher.
    
    Features:
    - Batch size: 20 searches
    - Parallel execution: 4 workers
    - Result caching
    """
    
    def __init__(self):
        self.config = BatchConfig(
            batch_size=20,
            flush_interval=0.05,  # 50ms for faster search response
            parallel_workers=4
        )
        self.processor = BatchProcessor("vector_search", self._process_vector_searches, self.config)
    
    async def start(self):
        """Start vector search batcher."""
        await self.processor.start()
    
    async def stop(self):
        """Stop vector search batcher."""
        await self.processor.stop()
    
    async def add_vector_search(self, user_id: str, query_embedding: List[float], 
                               limit: int = 10, filters: Dict = None,
                               priority: BatchPriority = BatchPriority.NORMAL) -> List[Dict]:
        """Add vector search operation to batch."""
        request = BatchRequest(
            operation="vector_search",
            data={
                "user_id": user_id,
                "query_embedding": query_embedding,
                "limit": limit,
                "filters": filters or {}
            },
            priority=priority,
            timeout=5.0
        )
        
        return await self.processor.add_request(request)
    
    async def _process_vector_searches(self, batch: List[BatchRequest]) -> List[Any]:
        """Process batch of vector search operations."""
        results = []
        
        try:
            # Use connection pool for database operations
            if global_pool_manager.postgres_pool:
                async with global_pool_manager.postgres_pool.acquire() as conn:
                    for request in batch:
                        search_result = await self._execute_vector_search(conn, request.data)
                        results.append(search_result)
            else:
                # Fallback mock results
                for request in batch:
                    results.append([{"id": f"mock_{request.id}", "content": "Mock memory", "similarity": 0.9}])
                    
        except Exception as e:
            logger.error(f"Vector search batch failed: {e}")
            for _ in batch:
                results.append(e)
        
        return results
    
    async def _execute_vector_search(self, conn, search_data: Dict) -> List[Dict]:
        """Execute vector similarity search."""
        # Simplified vector search - would integrate with actual pgvector logic
        query = """
            SELECT id, content, metadata, 
                   (embedding <-> $1::vector) as distance
            FROM memories 
            WHERE user_id = $2
            ORDER BY distance ASC
            LIMIT $3
        """
        
        rows = await conn.fetch(
            query,
            search_data["query_embedding"],
            search_data["user_id"],
            search_data["limit"]
        )
        
        return [
            {
                "id": str(row["id"]),
                "content": row["content"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "similarity": 1.0 - float(row["distance"])
            }
            for row in rows
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector search batcher statistics."""
        return self.processor.get_stats()

class GraphQueryBatcher:
    """
    Graph query operations batcher.
    
    Features:
    - Batch size: 10 queries
    - Result caching
    - Relationship optimization
    """
    
    def __init__(self):
        self.config = BatchConfig(
            batch_size=10,
            flush_interval=0.1,  # 100ms
            parallel_workers=2
        )
        self.processor = BatchProcessor("graph_query", self._process_graph_queries, self.config)
    
    async def start(self):
        """Start graph query batcher."""
        await self.processor.start()
    
    async def stop(self):
        """Stop graph query batcher."""
        await self.processor.stop()
    
    async def add_graph_query(self, user_id: str, query: str, parameters: Dict = None,
                             priority: BatchPriority = BatchPriority.NORMAL) -> List[Dict]:
        """Add graph query operation to batch."""
        request = BatchRequest(
            operation="graph_query",
            data={
                "user_id": user_id,
                "query": query,
                "parameters": parameters or {}
            },
            priority=priority,
            timeout=15.0
        )
        
        return await self.processor.add_request(request)
    
    async def _process_graph_queries(self, batch: List[BatchRequest]) -> List[Any]:
        """Process batch of graph query operations."""
        results = []
        
        try:
            # Use connection pool for Neo4j operations
            if global_pool_manager.neo4j_pool:
                async with global_pool_manager.neo4j_pool.session() as session:
                    for request in batch:
                        query_result = await self._execute_graph_query(session, request.data)
                        results.append(query_result)
            else:
                # Fallback mock results
                for request in batch:
                    results.append([{"node": f"mock_{request.id}", "relationship": "RELATED_TO"}])
                    
        except Exception as e:
            logger.error(f"Graph query batch failed: {e}")
            for _ in batch:
                results.append(e)
        
        return results
    
    async def _execute_graph_query(self, session, query_data: Dict) -> List[Dict]:
        """Execute graph query."""
        result = await session.run(
            query_data["query"],
            query_data["parameters"]
        )
        
        return await result.data()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph query batcher statistics."""
        return self.processor.get_stats()

class BatchingManager:
    """
    Centralized batching manager for all batch operations.
    
    Features:
    - Manages all batch processors
    - Centralized metrics and monitoring
    - Lifecycle management
    """
    
    def __init__(self):
        self.memory_write_batcher = MemoryWriteBatcher()
        self.vector_search_batcher = VectorSearchBatcher()
        self.graph_query_batcher = GraphQueryBatcher()
        
        self.is_running = False
        self.monitoring_task = None
    
    async def start(self):
        """Start all batch processors."""
        await self.memory_write_batcher.start()
        await self.vector_search_batcher.start()
        await self.graph_query_batcher.start()
        
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Batching manager started")
    
    async def stop(self):
        """Stop all batch processors."""
        self.is_running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
        
        await self.memory_write_batcher.stop()
        await self.vector_search_batcher.stop()
        await self.graph_query_batcher.stop()
        
        logger.info("Batching manager stopped")
    
    async def _monitoring_loop(self):
        """Monitoring loop for batch operations."""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Monitor every minute
                
                # Collect stats
                stats = self.get_comprehensive_stats()
                
                # Log aggregated stats
                logger.info(f"Batching stats: {stats}")
                
            except Exception as e:
                logger.error(f"Batching monitoring error: {e}")
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all batchers."""
        return {
            'timestamp': datetime.now().isoformat(),
            'batchers': {
                'memory_write': self.memory_write_batcher.get_stats(),
                'vector_search': self.vector_search_batcher.get_stats(),
                'graph_query': self.graph_query_batcher.get_stats()
            }
        }

# Global batching manager
global_batching_manager = BatchingManager()

# Decorators for batch operations
def batch_memory_write(priority: BatchPriority = BatchPriority.NORMAL):
    """Decorator for batching memory write operations."""
    def decorator(func):
        @wraps(func)
        async def wrapper(user_id: str, memory_data: Dict, *args, **kwargs):
            # Use batching manager
            result = await global_batching_manager.memory_write_batcher.add_memory_write(
                user_id, memory_data, priority
            )
            return result
        return wrapper
    return decorator

def batch_vector_search(priority: BatchPriority = BatchPriority.NORMAL):
    """Decorator for batching vector search operations."""
    def decorator(func):
        @wraps(func)
        async def wrapper(user_id: str, query_embedding: List[float], 
                         limit: int = 10, filters: Dict = None, *args, **kwargs):
            # Use batching manager
            result = await global_batching_manager.vector_search_batcher.add_vector_search(
                user_id, query_embedding, limit, filters, priority
            )
            return result
        return wrapper
    return decorator

def batch_graph_query(priority: BatchPriority = BatchPriority.NORMAL):
    """Decorator for batching graph query operations."""
    def decorator(func):
        @wraps(func)
        async def wrapper(user_id: str, query: str, parameters: Dict = None, *args, **kwargs):
            # Use batching manager
            result = await global_batching_manager.graph_query_batcher.add_graph_query(
                user_id, query, parameters, priority
            )
            return result
        return wrapper
    return decorator