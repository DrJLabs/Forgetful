"""
Performance tests for the batching and pipelining implementation.

This test suite validates:
- Memory write batching performance
- Vector search batching performance  
- Graph query batching performance
- Batch processing queue with priority handling
- Timeout and error handling performance
- Concurrent batch operations
"""

import asyncio
import os
import random

# Add the workspace to the path dynamically
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.batching import (
    BatchConfig,
    BatchingManager,
    BatchMetrics,
    BatchPriority,
    BatchProcessor,
    BatchRequest,
    GraphQueryBatcher,
    MemoryWriteBatcher,
    VectorSearchBatcher,
)


class TestBatchingPerformance:
    """Performance tests for batching and pipelining."""

    @pytest.fixture
    def batch_config(self):
        """Create test batch configuration."""
        return BatchConfig(
            batch_size=10,  # Smaller for testing
            flush_interval=0.1,  # 100ms
            timeout=5.0,
            max_retries=2,
            retry_delay=0.01,  # 10ms
            parallel_workers=2,
            queue_size=100,
        )

    @pytest.fixture
    def mock_processor_func(self):
        """Create mock processor function."""

        async def mock_processor(batch):
            # Simulate processing time
            await asyncio.sleep(0.01)
            return [f"result_{req.id}" for req in batch]

        return mock_processor

    @pytest.fixture
    def batch_processor(self, batch_config, mock_processor_func):
        """Create batch processor instance."""
        return BatchProcessor("test_processor", mock_processor_func, batch_config)

    def generate_batch_requests(
        self, count: int, priority: BatchPriority = BatchPriority.NORMAL
    ):
        """Generate test batch requests."""
        requests = []
        for i in range(count):
            request = BatchRequest(
                operation=f"test_op_{i}",
                data={"value": f"test_data_{i}"},
                priority=priority,
                timeout=2.0,
            )
            requests.append(request)
        return requests

    @pytest.mark.asyncio
    async def test_batch_processor_performance(self, batch_processor):
        """Test batch processor performance under load."""
        # Start the processor
        await batch_processor.start()

        try:
            # Generate test requests
            requests = self.generate_batch_requests(50)

            # Performance test
            start_time = time.time()

            # Submit requests concurrently
            tasks = []
            for request in requests:
                task = asyncio.create_task(batch_processor.add_request(request))
                tasks.append(task)

            # Wait for all requests to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            total_time = time.time() - start_time

            # Performance assertions
            assert total_time < 10.0, f"Batch processing too slow: {total_time:.3f}s"

            # Verify results
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) == len(
                requests
            ), f"Expected {len(requests)} results, got {len(successful_results)}"

            # Check batch processor stats
            stats = batch_processor.get_stats()

            assert stats["batches_processed"] > 0, "Should have processed batches"
            assert stats["requests_processed"] == len(
                requests
            ), f"Expected {len(requests)} requests processed"
            assert (
                stats["success_rate"] > 0.95
            ), f"Success rate too low: {stats['success_rate']:.3f}"

            print(
                f"Batch Processor Performance: Time={total_time:.3f}s, Batches={stats['batches_processed']}, Success Rate={stats['success_rate']:.3f}"
            )

        finally:
            await batch_processor.stop()

    @pytest.mark.asyncio
    async def test_priority_batching_performance(self, batch_processor):
        """Test priority-based batching performance."""
        await batch_processor.start()

        try:
            # Generate requests with different priorities
            urgent_requests = self.generate_batch_requests(5, BatchPriority.URGENT)
            high_requests = self.generate_batch_requests(10, BatchPriority.HIGH)
            normal_requests = self.generate_batch_requests(15, BatchPriority.NORMAL)
            low_requests = self.generate_batch_requests(20, BatchPriority.LOW)

            all_requests = (
                urgent_requests + high_requests + normal_requests + low_requests
            )

            # Submit all requests
            start_time = time.time()

            tasks = []
            for request in all_requests:
                task = asyncio.create_task(batch_processor.add_request(request))
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            total_time = time.time() - start_time

            # Performance assertions
            assert total_time < 15.0, f"Priority batching too slow: {total_time:.3f}s"

            # Verify all requests completed
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) == len(
                all_requests
            ), f"Expected {len(all_requests)} results"

            # Check stats
            stats = batch_processor.get_stats()
            assert stats["requests_processed"] == len(
                all_requests
            ), "Should process all requests"

            print(
                f"Priority Batching Performance: Time={total_time:.3f}s, Requests={len(all_requests)}"
            )

        finally:
            await batch_processor.stop()

    @pytest.mark.asyncio
    async def test_memory_write_batcher_performance(self):
        """Test memory write batcher performance."""
        # Mock the database operations
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = "memory_123"

        # Mock the connection pool
        mock_pool = Mock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_pool.acquire.return_value.__aexit__.return_value = None

        with patch("shared.batching.global_pool_manager") as mock_manager:
            mock_manager.postgres_pool = mock_pool

            # Create memory write batcher
            batcher = MemoryWriteBatcher()
            await batcher.start()

            try:
                # Generate test data
                test_data = []
                for i in range(30):
                    test_data.append(
                        {
                            "user_id": f"user_{i % 5}",  # 5 different users
                            "memory_data": {
                                "content": f"Memory content {i}",
                                "metadata": {"type": "test", "index": i},
                            },
                        }
                    )

                # Performance test
                start_time = time.time()

                # Submit memory writes
                tasks = []
                for data in test_data:
                    task = asyncio.create_task(
                        batcher.add_memory_write(
                            data["user_id"], data["memory_data"], BatchPriority.NORMAL
                        )
                    )
                    tasks.append(task)

                results = await asyncio.gather(*tasks, return_exceptions=True)

                total_time = time.time() - start_time

                # Performance assertions
                assert (
                    total_time < 10.0
                ), f"Memory write batching too slow: {total_time:.3f}s"

                # Verify results
                successful_results = [
                    r for r in results if not isinstance(r, Exception)
                ]
                assert len(successful_results) == len(
                    test_data
                ), f"Expected {len(test_data)} results"

                # Check stats
                stats = batcher.get_stats()
                assert stats["requests_processed"] == len(
                    test_data
                ), "Should process all writes"

                print(
                    f"Memory Write Batcher Performance: Time={total_time:.3f}s, Writes={len(test_data)}, Success Rate={stats['success_rate']:.3f}"
                )

            finally:
                await batcher.stop()

    @pytest.mark.asyncio
    async def test_vector_search_batcher_performance(self):
        """Test vector search batcher performance."""
        # Mock the database operations
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            {"id": 1, "content": "test", "similarity": 0.9},
            {"id": 2, "content": "test2", "similarity": 0.8},
        ]

        # Mock the connection pool
        mock_pool = Mock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_pool.acquire.return_value.__aexit__.return_value = None

        with patch("shared.batching.global_pool_manager") as mock_manager:
            mock_manager.postgres_pool = mock_pool

            # Create vector search batcher
            batcher = VectorSearchBatcher()
            await batcher.start()

            try:
                # Generate test data
                test_searches = []
                for i in range(20):
                    test_searches.append(
                        {
                            "user_id": f"user_{i % 3}",  # 3 different users
                            "query_embedding": [
                                random.random() for _ in range(10)
                            ],  # 10-dim vector
                            "limit": 5,
                            "filters": {"type": "test"},
                        }
                    )

                # Performance test
                start_time = time.time()

                # Submit vector searches
                tasks = []
                for search in test_searches:
                    task = asyncio.create_task(
                        batcher.add_vector_search(
                            search["user_id"],
                            search["query_embedding"],
                            search["limit"],
                            search["filters"],
                            BatchPriority.NORMAL,
                        )
                    )
                    tasks.append(task)

                results = await asyncio.gather(*tasks, return_exceptions=True)

                total_time = time.time() - start_time

                # Performance assertions
                assert (
                    total_time < 8.0
                ), f"Vector search batching too slow: {total_time:.3f}s"

                # Verify results
                successful_results = [
                    r for r in results if not isinstance(r, Exception)
                ]
                assert len(successful_results) == len(
                    test_searches
                ), f"Expected {len(test_searches)} results"

                # Check stats
                stats = batcher.get_stats()
                assert stats["requests_processed"] == len(
                    test_searches
                ), "Should process all searches"

                print(
                    f"Vector Search Batcher Performance: Time={total_time:.3f}s, Searches={len(test_searches)}, Success Rate={stats['success_rate']:.3f}"
                )

            finally:
                await batcher.stop()

    @pytest.mark.asyncio
    async def test_graph_query_batcher_performance(self):
        """Test graph query batcher performance."""
        # Mock Neo4j session and results
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_record = Mock()
        mock_record.data.return_value = {"id": 1, "name": "test"}
        mock_result.data.return_value = [mock_record]
        mock_session.run.return_value = mock_result

        # Mock the connection pool
        mock_pool = Mock()
        mock_pool.session.return_value.__aenter__.return_value = mock_session
        mock_pool.session.return_value.__aexit__.return_value = None

        with patch("shared.batching.global_pool_manager") as mock_manager:
            mock_manager.neo4j_pool = mock_pool

            # Create graph query batcher
            batcher = GraphQueryBatcher()
            await batcher.start()

            try:
                # Generate test queries
                test_queries = []
                for i in range(15):
                    test_queries.append(
                        {
                            "user_id": f"user_{i % 4}",  # 4 different users
                            "query": f"MATCH (n:Memory) WHERE n.user_id = $user_id AND n.id = {i} RETURN n",
                            "parameters": {"user_id": f"user_{i % 4}"},
                        }
                    )

                # Performance test
                start_time = time.time()

                # Submit graph queries
                tasks = []
                for query in test_queries:
                    task = asyncio.create_task(
                        batcher.add_graph_query(
                            query["user_id"],
                            query["query"],
                            query["parameters"],
                            BatchPriority.NORMAL,
                        )
                    )
                    tasks.append(task)

                results = await asyncio.gather(*tasks, return_exceptions=True)

                total_time = time.time() - start_time

                # Performance assertions
                assert (
                    total_time < 8.0
                ), f"Graph query batching too slow: {total_time:.3f}s"

                # Verify results
                successful_results = [
                    r for r in results if not isinstance(r, Exception)
                ]
                assert len(successful_results) == len(
                    test_queries
                ), f"Expected {len(test_queries)} results"

                # Check stats
                stats = batcher.get_stats()
                assert stats["requests_processed"] == len(
                    test_queries
                ), "Should process all queries"

                print(
                    f"Graph Query Batcher Performance: Time={total_time:.3f}s, Queries={len(test_queries)}, Success Rate={stats['success_rate']:.3f}"
                )

            finally:
                await batcher.stop()

    @pytest.mark.asyncio
    async def test_batching_manager_performance(self):
        """Test batching manager coordinating all batchers."""
        # Mock all the database connections
        mock_pg_conn = AsyncMock()
        mock_pg_conn.fetchval.return_value = "memory_123"
        mock_pg_conn.fetch.return_value = [{"id": 1, "similarity": 0.9}]

        mock_neo4j_session = AsyncMock()
        mock_neo4j_result = AsyncMock()
        mock_neo4j_record = Mock()
        mock_neo4j_record.data.return_value = {"id": 1, "name": "test"}
        mock_neo4j_result.data.return_value = [mock_neo4j_record]
        mock_neo4j_session.run.return_value = mock_neo4j_result

        # Mock connection pools
        mock_pg_pool = Mock()
        mock_pg_pool.acquire.return_value.__aenter__.return_value = mock_pg_conn
        mock_pg_pool.acquire.return_value.__aexit__.return_value = None

        mock_neo4j_pool = Mock()
        mock_neo4j_pool.session.return_value.__aenter__.return_value = (
            mock_neo4j_session
        )
        mock_neo4j_pool.session.return_value.__aexit__.return_value = None

        with patch("shared.batching.global_pool_manager") as mock_manager:
            mock_manager.postgres_pool = mock_pg_pool
            mock_manager.neo4j_pool = mock_neo4j_pool

            # Create batching manager
            manager = BatchingManager()
            await manager.start()

            try:
                # Generate mixed operations
                operations = []

                # Memory writes
                for i in range(10):
                    operations.append(
                        {
                            "type": "memory_write",
                            "user_id": f"user_{i % 3}",
                            "data": {"content": f"Memory {i}", "metadata": {}},
                        }
                    )

                # Vector searches
                for i in range(8):
                    operations.append(
                        {
                            "type": "vector_search",
                            "user_id": f"user_{i % 3}",
                            "embedding": [random.random() for _ in range(5)],
                            "limit": 3,
                        }
                    )

                # Graph queries
                for i in range(6):
                    operations.append(
                        {
                            "type": "graph_query",
                            "user_id": f"user_{i % 3}",
                            "query": f"MATCH (n) WHERE n.id = {i} RETURN n",
                            "parameters": {},
                        }
                    )

                # Shuffle operations for realistic mixed load
                random.shuffle(operations)

                # Performance test
                start_time = time.time()

                # Submit all operations
                tasks = []
                for op in operations:
                    if op["type"] == "memory_write":
                        task = asyncio.create_task(
                            manager.memory_write_batcher.add_memory_write(
                                op["user_id"], op["data"]
                            )
                        )
                    elif op["type"] == "vector_search":
                        task = asyncio.create_task(
                            manager.vector_search_batcher.add_vector_search(
                                op["user_id"], op["embedding"], op["limit"]
                            )
                        )
                    elif op["type"] == "graph_query":
                        task = asyncio.create_task(
                            manager.graph_query_batcher.add_graph_query(
                                op["user_id"], op["query"], op["parameters"]
                            )
                        )

                    tasks.append(task)

                results = await asyncio.gather(*tasks, return_exceptions=True)

                total_time = time.time() - start_time

                # Performance assertions
                assert (
                    total_time < 15.0
                ), f"Batching manager too slow: {total_time:.3f}s"

                # Verify results
                successful_results = [
                    r for r in results if not isinstance(r, Exception)
                ]
                assert len(successful_results) == len(
                    operations
                ), f"Expected {len(operations)} results"

                # Check comprehensive stats
                stats = manager.get_comprehensive_stats()

                assert "memory_write_batcher" in stats, "Should have memory write stats"
                assert (
                    "vector_search_batcher" in stats
                ), "Should have vector search stats"
                assert "graph_query_batcher" in stats, "Should have graph query stats"

                print(
                    f"Batching Manager Performance: Time={total_time:.3f}s, Operations={len(operations)}"
                )

            finally:
                await manager.stop()

    @pytest.mark.asyncio
    async def test_batch_timeout_handling(self, batch_processor):
        """Test batch timeout handling performance."""

        # Mock a slow processor function
        async def slow_processor(batch):
            await asyncio.sleep(2.0)  # Simulate slow processing
            return [f"result_{req.id}" for req in batch]

        # Create processor with slow function
        config = BatchConfig(
            batch_size=5,
            flush_interval=0.1,
            timeout=1.0,  # 1 second timeout
            max_retries=1,
            retry_delay=0.1,
            parallel_workers=1,
        )

        slow_processor_instance = BatchProcessor(
            "slow_processor", slow_processor, config
        )
        await slow_processor_instance.start()

        try:
            # Generate requests
            requests = self.generate_batch_requests(5)

            # Performance test
            start_time = time.time()

            # Submit requests (should timeout)
            tasks = []
            for request in requests:
                request.timeout = 0.5  # Short timeout
                task = asyncio.create_task(slow_processor_instance.add_request(request))
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            total_time = time.time() - start_time

            # Performance assertions
            assert total_time < 3.0, f"Timeout handling too slow: {total_time:.3f}s"

            # Verify timeouts occurred
            timeout_results = [
                r for r in results if isinstance(r, asyncio.TimeoutError)
            ]
            assert len(timeout_results) > 0, "Should have some timeout errors"

            # Check stats
            stats = slow_processor_instance.get_stats()
            assert stats["timeout_count"] > 0, "Should have recorded timeouts"

            print(
                f"Timeout Handling Performance: Time={total_time:.3f}s, Timeouts={len(timeout_results)}"
            )

        finally:
            await slow_processor_instance.stop()

    @pytest.mark.asyncio
    async def test_batch_error_recovery(self, batch_processor):
        """Test batch error handling and recovery performance."""
        # Mock a processor function that fails sometimes
        failure_count = 0

        async def failing_processor(batch):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:  # Fail first 2 attempts
                raise Exception("Simulated processing error")
            return [f"result_{req.id}" for req in batch]

        # Create processor with failing function
        config = BatchConfig(
            batch_size=5,
            flush_interval=0.1,
            timeout=2.0,
            max_retries=3,
            retry_delay=0.05,  # 50ms retry delay
            parallel_workers=1,
        )

        failing_processor_instance = BatchProcessor(
            "failing_processor", failing_processor, config
        )
        await failing_processor_instance.start()

        try:
            # Generate requests
            requests = self.generate_batch_requests(5)

            # Performance test
            start_time = time.time()

            # Submit requests (should eventually succeed after retries)
            tasks = []
            for request in requests:
                task = asyncio.create_task(
                    failing_processor_instance.add_request(request)
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            total_time = time.time() - start_time

            # Performance assertions
            assert total_time < 5.0, f"Error recovery too slow: {total_time:.3f}s"

            # Verify eventual success
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) == len(
                requests
            ), f"Expected all requests to eventually succeed"

            # Check stats
            stats = failing_processor_instance.get_stats()
            assert stats["retry_count"] > 0, "Should have recorded retries"

            print(
                f"Error Recovery Performance: Time={total_time:.3f}s, Retries={stats['retry_count']}"
            )

        finally:
            await failing_processor_instance.stop()

    def test_batch_metrics_performance(self):
        """Test batch metrics collection performance."""
        metrics = BatchMetrics()

        # Test metrics recording performance
        start_time = time.time()

        # Record many metrics
        for i in range(1000):
            metrics.record_batch_processed(10, 0.01)  # 10 requests, 10ms processing

            if i % 100 == 0:
                metrics.record_flush()

            if i % 50 == 0:
                metrics.record_timeout()
                metrics.record_retry()

        # Record some failures
        for i in range(100):
            metrics.record_request_failed()

        metrics_time = time.time() - start_time

        # Get stats
        stats_start = time.time()
        stats = metrics.get_stats()
        stats_time = time.time() - stats_start

        # Performance assertions
        assert metrics_time < 0.1, f"Metrics recording too slow: {metrics_time:.3f}s"
        assert stats_time < 0.01, f"Stats collection too slow: {stats_time:.3f}s"

        # Verify stats accuracy
        assert (
            stats["batches_processed"] == 1000
        ), f"Expected 1000 batches, got {stats['batches_processed']}"
        assert (
            stats["requests_processed"] == 10000
        ), f"Expected 10000 requests, got {stats['requests_processed']}"
        assert (
            stats["requests_failed"] == 100
        ), f"Expected 100 failures, got {stats['requests_failed']}"
        assert (
            stats["flush_count"] == 10
        ), f"Expected 10 flushes, got {stats['flush_count']}"
        assert (
            stats["timeout_count"] == 20
        ), f"Expected 20 timeouts, got {stats['timeout_count']}"
        assert (
            stats["retry_count"] == 20
        ), f"Expected 20 retries, got {stats['retry_count']}"

        # Check calculated metrics
        assert (
            stats["success_rate"] > 0.99
        ), f"Success rate too low: {stats['success_rate']:.3f}"
        assert (
            stats["average_batch_size"] == 10.0
        ), f"Average batch size incorrect: {stats['average_batch_size']}"

        print(
            f"Batch Metrics Performance: Recording={metrics_time:.3f}s, Stats={stats_time:.3f}s"
        )

    def test_batch_configuration_validation(self):
        """Test batch configuration validation."""
        # Test valid configuration
        valid_config = BatchConfig(
            batch_size=50,
            flush_interval=0.1,
            timeout=30.0,
            max_retries=3,
            retry_delay=0.05,
            parallel_workers=4,
            queue_size=1000,
        )

        # Should not raise exception
        assert valid_config.batch_size == 50
        assert valid_config.flush_interval == 0.1

        # Test configuration performance
        config_start = time.time()

        # Create many configurations
        for i in range(100):
            config = BatchConfig(
                batch_size=i % 100 + 1,
                flush_interval=0.01 + (i % 10) * 0.01,
                timeout=1.0 + (i % 30),
                max_retries=i % 5 + 1,
                parallel_workers=i % 8 + 1,
            )
            assert config.batch_size > 0
            assert config.parallel_workers > 0

        config_time = time.time() - config_start

        # Performance assertions
        assert config_time < 0.1, f"Configuration creation too slow: {config_time:.3f}s"

        print(f"Configuration Performance: {config_time:.3f}s for 100 configs")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
