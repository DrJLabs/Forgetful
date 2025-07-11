"""
Batch Processor for MCP Server Performance Optimization

This module provides batch processing capabilities for MCP operations,
enabling efficient handling of multiple memory operations for autonomous AI agents.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of operations that can be batched"""
    ADD_MEMORY = "add_memory"
    SEARCH_MEMORY = "search_memory"
    GET_MEMORY = "get_memory"
    DELETE_MEMORY = "delete_memory"
    UPDATE_MEMORY = "update_memory"


@dataclass
class BatchRequest:
    """Individual request in a batch"""
    operation_type: OperationType
    parameters: Dict[str, Any]
    request_id: str
    timestamp: float = field(default_factory=time.time)
    user_id: str = ""
    client_name: str = ""


@dataclass
class BatchResponse:
    """Response for a batch request"""
    request_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    processing_time_ms: float = 0.0


class BatchProcessor:
    """Batch processor for MCP operations"""
    
    def __init__(self,
                 max_batch_size: int = 10,
                 max_wait_time_ms: float = 50.0,
                 max_queue_size: int = 1000,
                 enable_adaptive_batching: bool = True):
        self.max_batch_size = max_batch_size
        self.max_wait_time_ms = max_wait_time_ms
        self.max_queue_size = max_queue_size
        self.enable_adaptive_batching = enable_adaptive_batching
        
        self._request_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._processing_task = None
        self._response_futures: Dict[str, asyncio.Future] = {}
        self._lock = threading.Lock()
        
        # Adaptive batching parameters
        self._recent_processing_times: List[float] = []
        self._optimal_batch_size = max_batch_size
        self._load_factor = 0.0
        
        # Statistics
        self._stats = {
            'total_requests': 0,
            'total_batches': 0,
            'average_batch_size': 0.0,
            'average_processing_time_ms': 0.0,
            'queue_overflow_count': 0,
            'timeout_count': 0
        }
        
        # Start processing (will be started when event loop is available)
        self._processing_started = False
    
    async def submit_request(self, request: BatchRequest, timeout_ms: float = 5000.0) -> BatchResponse:
        """Submit a request for batch processing"""
        if self._request_queue.full():
            self._stats['queue_overflow_count'] += 1
            raise Exception("Batch processor queue is full")
        
        # Create future for response
        future = asyncio.Future()
        self._response_futures[request.request_id] = future
        
        try:
            # Add to queue
            await self._request_queue.put(request)
            self._stats['total_requests'] += 1
            
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=timeout_ms / 1000.0)
            return response
            
        except asyncio.TimeoutError:
            self._stats['timeout_count'] += 1
            # Clean up future
            self._response_futures.pop(request.request_id, None)
            raise Exception(f"Request {request.request_id} timed out")
        except Exception as e:
            # Clean up future
            self._response_futures.pop(request.request_id, None)
            raise
    
    def _start_processing(self):
        """Start the batch processing task"""
        async def processing_loop():
            while True:
                try:
                    batch = await self._collect_batch()
                    if batch:
                        await self._process_batch(batch)
                except Exception as e:
                    logger.error(f"Batch processing error: {e}")
                    await asyncio.sleep(0.1)  # Brief pause on error
        
        self._processing_task = asyncio.create_task(processing_loop())
        logger.info("Started batch processing task")
    
    async def _collect_batch(self) -> List[BatchRequest]:
        """Collect requests into a batch with smart sizing"""
        batch = []
        start_time = time.time()
        
        # Get first request (wait for it)
        try:
            first_request = await self._request_queue.get()
            batch.append(first_request)
        except Exception:
            return batch
        
        # Determine optimal batch size based on first request's operation type
        optimal_size = self._get_optimal_batch_size(first_request.operation_type)
        
        # Collect additional requests of the same type up to optimal size or timeout
        while (len(batch) < optimal_size and
               (time.time() - start_time) * 1000 < self.max_wait_time_ms):
            
            try:
                # Try to get more requests without blocking too long
                request = await asyncio.wait_for(
                    self._request_queue.get(), 
                    timeout=max(0.001, (self.max_wait_time_ms - (time.time() - start_time) * 1000) / 1000)
                )
                
                # Only add requests of the same operation type to maintain batch efficiency
                if request.operation_type == first_request.operation_type:
                    batch.append(request)
                else:
                    # Put the request back for the next batch
                    await self._request_queue.put(request)
                    break
                    
            except asyncio.TimeoutError:
                # No more requests available quickly, proceed with current batch
                break
            except Exception:
                break
        
        return batch
    
    async def _process_batch(self, batch: List[BatchRequest]):
        """Process a batch of requests"""
        if not batch:
            return
        
        start_time = time.time()
        responses = []
        
        # Group requests by operation type and user for efficient processing
        grouped_requests = self._group_requests(batch)
        
        # Process each group
        for group_key, group_requests in grouped_requests.items():
            group_responses = await self._process_group(group_requests)
            responses.extend(group_responses)
        
        # Update statistics
        processing_time_ms = (time.time() - start_time) * 1000
        self._update_stats(len(batch), processing_time_ms)
        
        # Send responses to futures
        for response in responses:
            future = self._response_futures.pop(response.request_id, None)
            if future and not future.done():
                future.set_result(response)
        
        logger.debug(f"Processed batch of {len(batch)} requests in {processing_time_ms:.2f}ms")
    
    def _group_requests(self, batch: List[BatchRequest]) -> Dict[str, List[BatchRequest]]:
        """Group requests by operation type and user for efficient processing"""
        grouped = defaultdict(list)
        
        for request in batch:
            # Group by operation type and user
            group_key = f"{request.operation_type.value}:{request.user_id}"
            grouped[group_key].append(request)
        
        return grouped
    
    async def _process_group(self, requests: List[BatchRequest]) -> List[BatchResponse]:
        """Process a group of similar requests"""
        responses = []
        
        if not requests:
            return responses
        
        operation_type = requests[0].operation_type
        
        try:
            if operation_type == OperationType.ADD_MEMORY:
                responses = await self._process_add_memory_batch(requests)
            elif operation_type == OperationType.SEARCH_MEMORY:
                responses = await self._process_search_memory_batch(requests)
            elif operation_type == OperationType.GET_MEMORY:
                responses = await self._process_get_memory_batch(requests)
            elif operation_type == OperationType.DELETE_MEMORY:
                responses = await self._process_delete_memory_batch(requests)
            elif operation_type == OperationType.UPDATE_MEMORY:
                responses = await self._process_update_memory_batch(requests)
            else:
                # Fall back to individual processing
                responses = await self._process_individual_requests(requests)
        
        except Exception as e:
            logger.error(f"Error processing group {operation_type}: {e}")
            # Create error responses for all requests in the group
            for request in requests:
                responses.append(BatchResponse(
                    request_id=request.request_id,
                    success=False,
                    error=str(e)
                ))
        
        return responses
    
    async def _process_add_memory_batch(self, requests: List[BatchRequest]) -> List[BatchResponse]:
        """Process a batch of add memory requests"""
        responses = []
        
        # Get memory client
        from app.utils.connection_pool import get_pooled_client
        
        async with get_pooled_client() as client:
            for request in requests:
                start_time = time.time()
                try:
                    params = request.parameters
                    result = client.add(
                        params.get('text', ''),
                        user_id=request.user_id,
                        metadata=params.get('metadata', {})
                    )
                    
                    responses.append(BatchResponse(
                        request_id=request.request_id,
                        success=True,
                        result=result,
                        processing_time_ms=(time.time() - start_time) * 1000
                    ))
                    
                except Exception as e:
                    responses.append(BatchResponse(
                        request_id=request.request_id,
                        success=False,
                        error=str(e),
                        processing_time_ms=(time.time() - start_time) * 1000
                    ))
        
        return responses
    
    async def _process_search_memory_batch(self, requests: List[BatchRequest]) -> List[BatchResponse]:
        """Process a batch of search memory requests"""
        responses = []
        
        # Get memory client
        from app.utils.connection_pool import get_pooled_client
        
        async with get_pooled_client() as client:
            for request in requests:
                start_time = time.time()
                try:
                    params = request.parameters
                    result = client.search(
                        params.get('query', ''),
                        user_id=request.user_id,
                        limit=params.get('limit', 10)
                    )
                    
                    responses.append(BatchResponse(
                        request_id=request.request_id,
                        success=True,
                        result=result,
                        processing_time_ms=(time.time() - start_time) * 1000
                    ))
                    
                except Exception as e:
                    responses.append(BatchResponse(
                        request_id=request.request_id,
                        success=False,
                        error=str(e),
                        processing_time_ms=(time.time() - start_time) * 1000
                    ))
        
        return responses
    
    async def _process_get_memory_batch(self, requests: List[BatchRequest]) -> List[BatchResponse]:
        """Process a batch of get memory requests"""
        responses = []
        
        # Get memory client
        from app.utils.connection_pool import get_pooled_client
        
        async with get_pooled_client() as client:
            for request in requests:
                start_time = time.time()
                try:
                    params = request.parameters
                    result = client.get_all(user_id=request.user_id)
                    
                    responses.append(BatchResponse(
                        request_id=request.request_id,
                        success=True,
                        result=result,
                        processing_time_ms=(time.time() - start_time) * 1000
                    ))
                    
                except Exception as e:
                    responses.append(BatchResponse(
                        request_id=request.request_id,
                        success=False,
                        error=str(e),
                        processing_time_ms=(time.time() - start_time) * 1000
                    ))
        
        return responses
    
    async def _process_delete_memory_batch(self, requests: List[BatchRequest]) -> List[BatchResponse]:
        """Process a batch of delete memory requests"""
        responses = []
        
        # Get memory client
        from app.utils.connection_pool import get_pooled_client
        
        async with get_pooled_client() as client:
            for request in requests:
                start_time = time.time()
                try:
                    params = request.parameters
                    result = client.delete(params.get('memory_id'))
                    
                    responses.append(BatchResponse(
                        request_id=request.request_id,
                        success=True,
                        result=result,
                        processing_time_ms=(time.time() - start_time) * 1000
                    ))
                    
                except Exception as e:
                    responses.append(BatchResponse(
                        request_id=request.request_id,
                        success=False,
                        error=str(e),
                        processing_time_ms=(time.time() - start_time) * 1000
                    ))
        
        return responses
    
    async def _process_update_memory_batch(self, requests: List[BatchRequest]) -> List[BatchResponse]:
        """Process a batch of update memory requests"""
        responses = []
        
        # Get memory client
        from app.utils.connection_pool import get_pooled_client
        
        async with get_pooled_client() as client:
            for request in requests:
                start_time = time.time()
                try:
                    params = request.parameters
                    result = client.update(
                        params.get('memory_id'),
                        params.get('text', '')
                    )
                    
                    responses.append(BatchResponse(
                        request_id=request.request_id,
                        success=True,
                        result=result,
                        processing_time_ms=(time.time() - start_time) * 1000
                    ))
                    
                except Exception as e:
                    responses.append(BatchResponse(
                        request_id=request.request_id,
                        success=False,
                        error=str(e),
                        processing_time_ms=(time.time() - start_time) * 1000
                    ))
        
        return responses
    
    async def _process_individual_requests(self, requests: List[BatchRequest]) -> List[BatchResponse]:
        """Fall back to individual processing for unsupported batch operations"""
        responses = []
        
        for request in requests:
            responses.append(BatchResponse(
                request_id=request.request_id,
                success=False,
                error="Batch processing not supported for this operation type"
            ))
        
        return responses
    
    def _get_optimal_batch_size(self, operation_type: OperationType) -> int:
        """Get optimal batch size based on operation complexity"""
        # Smart batching based on operation type complexity
        complexity_map = {
            OperationType.SEARCH_MEMORY: 5,      # Higher complexity, smaller batches
            OperationType.ADD_MEMORY: 10,        # Lower complexity, larger batches
            OperationType.GET_MEMORY: 8,         # Medium complexity
            OperationType.DELETE_MEMORY: 12,     # Lower complexity, can batch more
            OperationType.UPDATE_MEMORY: 6,      # Medium-high complexity
        }
        
        base_size = complexity_map.get(operation_type, 8)
        
        if not self.enable_adaptive_batching:
            return min(self.max_batch_size, base_size)
        
        # Adaptive adjustment based on recent performance
        if len(self._recent_processing_times) < 5:
            return min(self.max_batch_size, base_size)
        
        avg_time = sum(self._recent_processing_times) / len(self._recent_processing_times)
        
        # Adjust based on performance
        if avg_time < 10.0:  # Fast processing, can increase
            adjusted_size = min(self.max_batch_size, base_size + 2)
        elif avg_time > 50.0:  # Slow processing, decrease
            adjusted_size = max(1, base_size - 2)
        else:
            adjusted_size = base_size
        
        return adjusted_size
    
    def _get_current_batch_size(self) -> int:
        """Get the current optimal batch size (fallback method)"""
        if not self.enable_adaptive_batching:
            return self.max_batch_size
        
        # Adaptive batching based on recent performance
        if len(self._recent_processing_times) < 5:
            return self.max_batch_size
        
        avg_time = sum(self._recent_processing_times) / len(self._recent_processing_times)
        
        # If processing is fast, increase batch size
        if avg_time < 10.0:  # Less than 10ms average
            self._optimal_batch_size = min(self.max_batch_size, self._optimal_batch_size + 1)
        # If processing is slow, decrease batch size
        elif avg_time > 50.0:  # More than 50ms average
            self._optimal_batch_size = max(1, self._optimal_batch_size - 1)
        
        return self._optimal_batch_size
    
    def _update_stats(self, batch_size: int, processing_time_ms: float):
        """Update processing statistics"""
        self._stats['total_batches'] += 1
        
        # Update average batch size
        total_requests = self._stats['total_requests']
        self._stats['average_batch_size'] = total_requests / self._stats['total_batches']
        
        # Update average processing time
        prev_avg = self._stats['average_processing_time_ms']
        batch_count = self._stats['total_batches']
        self._stats['average_processing_time_ms'] = (
            (prev_avg * (batch_count - 1) + processing_time_ms) / batch_count
        )
        
        # Update recent processing times for adaptive batching
        self._recent_processing_times.append(processing_time_ms)
        if len(self._recent_processing_times) > 50:
            self._recent_processing_times.pop(0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get batch processor statistics"""
        return {
            **self._stats,
            'queue_size': self._request_queue.qsize(),
            'pending_responses': len(self._response_futures),
            'optimal_batch_size': self._optimal_batch_size,
            'max_batch_size': self.max_batch_size,
            'max_wait_time_ms': self.max_wait_time_ms
        }
    
    async def shutdown(self):
        """Shutdown the batch processor"""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
        
        # Cancel any pending futures
        for future in self._response_futures.values():
            if not future.done():
                future.cancel()
        
        logger.info("Batch processor shutdown complete")


# Global batch processor instance
_batch_processor: Optional[BatchProcessor] = None


def get_batch_processor() -> BatchProcessor:
    """Get the global batch processor instance"""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchProcessor()
    return _batch_processor


async def submit_batch_request(operation_type: OperationType, 
                              parameters: Dict[str, Any],
                              user_id: str,
                              client_name: str,
                              timeout_ms: float = 5000.0) -> BatchResponse:
    """Submit a request for batch processing"""
    import uuid
    
    request = BatchRequest(
        operation_type=operation_type,
        parameters=parameters,
        request_id=str(uuid.uuid4()),
        user_id=user_id,
        client_name=client_name
    )
    
    processor = get_batch_processor()
    return await processor.submit_request(request, timeout_ms)