"""
Performance tests for the caching layer implementation.

This test suite validates:
- L1 cache performance (in-memory)
- L2 cache performance (Redis)
- L3 cache performance (query cache)
- Multi-layer cache coordination
- Cache hit/miss ratios under load
- Memory usage and cleanup
"""

import asyncio
import os
import random
import string

# Add the workspace to the path dynamically
import sys
import time

import psutil
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.caching import (
    MultiLayerCache,
    MultiLayerCacheConfig,
    OptimizedL1Cache,
    OptimizedL2RedisCache,
    OptimizedL3QueryCache,
)


class TestCachePerformance:
    """Performance tests for caching layer."""

    @pytest.fixture
    def cache_config(self):
        """Create test cache configuration."""
        return MultiLayerCacheConfig(
            l1_max_size=64 * 1024 * 1024,  # 64MB for testing
            l1_ttl=300,
            l2_max_size=256 * 1024 * 1024,  # 256MB for testing
            l2_ttl=3600,
            l3_ttl=1800,
            l3_max_prepared_statements=500,
        )

    @pytest.fixture
    def l1_cache(self, cache_config):
        """Create L1 cache instance."""
        return OptimizedL1Cache(cache_config)

    @pytest.fixture
    def l2_cache(self, cache_config):
        """Create L2 cache instance."""
        return OptimizedL2RedisCache(cache_config)

    @pytest.fixture
    def l3_cache(self, cache_config):
        """Create L3 cache instance."""
        return OptimizedL3QueryCache(cache_config)

    @pytest.fixture
    def multi_layer_cache(self, cache_config):
        """Create multi-layer cache instance."""
        return MultiLayerCache(cache_config)

    def generate_test_data(self, size: int = 100) -> list:
        """Generate test data for performance tests."""
        return [
            {
                "key": f"test_key_{i}",
                "value": "".join(
                    random.choices(string.ascii_letters, k=1024)
                ),  # 1KB values
                "user_id": f"user_{i % 10}",  # 10 different users
                "query": f"SELECT * FROM memories WHERE user_id = '{i % 10}' AND id = {i}",
            }
            for i in range(size)
        ]

    @pytest.mark.asyncio
    async def test_l1_cache_performance(self, l1_cache):
        """Test L1 cache performance under load."""
        test_data = self.generate_test_data(1000)

        # Performance metrics
        start_time = time.time()

        # Write performance test
        write_start = time.time()
        for item in test_data:
            await l1_cache.set(item["key"], item["value"])
        write_time = time.time() - write_start

        # Read performance test
        read_start = time.time()
        hit_count = 0
        for item in test_data:
            result = await l1_cache.get(item["key"])
            if result is not None:
                hit_count += 1
        read_time = time.time() - read_start

        total_time = time.time() - start_time

        # Get cache stats
        stats = l1_cache.get_stats()

        # Performance assertions
        assert write_time < 5.0, f"L1 cache write time too slow: {write_time:.3f}s"
        assert read_time < 2.0, f"L1 cache read time too slow: {read_time:.3f}s"
        assert total_time < 10.0, f"L1 cache total time too slow: {total_time:.3f}s"

        # Hit rate assertions
        assert hit_count == len(test_data), (
            f"L1 cache hit count mismatch: {hit_count}/{len(test_data)}"
        )
        assert stats["hit_rate"] > 0.98, (
            f"L1 cache hit rate too low: {stats['hit_rate']:.3f}"
        )

        # Memory usage assertions
        assert stats["memory_usage_mb"] < 100, (
            f"L1 cache memory usage too high: {stats['memory_usage_mb']:.1f}MB"
        )

        print(
            f"L1 Cache Performance: Write={write_time:.3f}s, Read={read_time:.3f}s, Hit Rate={stats['hit_rate']:.3f}"
        )

    @pytest.mark.asyncio
    async def test_l2_cache_performance(self, l2_cache):
        """Test L2 cache performance with Redis fallback."""
        test_data = self.generate_test_data(500)

        # Performance metrics
        start_time = time.time()

        # Write performance test
        write_start = time.time()
        for item in test_data:
            await l2_cache.set(item["key"], item["value"])
        write_time = time.time() - write_start

        # Read performance test
        read_start = time.time()
        hit_count = 0
        for item in test_data:
            result = await l2_cache.get(item["key"])
            if result is not None:
                hit_count += 1
        read_time = time.time() - read_start

        total_time = time.time() - start_time

        # Get cache stats
        stats = l2_cache.get_stats()

        # Performance assertions (more lenient for Redis/fallback)
        assert write_time < 10.0, f"L2 cache write time too slow: {write_time:.3f}s"
        assert read_time < 5.0, f"L2 cache read time too slow: {read_time:.3f}s"
        assert total_time < 20.0, f"L2 cache total time too slow: {total_time:.3f}s"

        # Hit rate assertions (account for Redis connectivity issues)
        assert hit_count >= len(test_data) * 0.8, (
            f"L2 cache hit count too low: {hit_count}/{len(test_data)}"
        )

        print(
            f"L2 Cache Performance: Write={write_time:.3f}s, Read={read_time:.3f}s, Hits={hit_count}/{len(test_data)}"
        )

    @pytest.mark.asyncio
    async def test_l3_cache_performance(self, l3_cache):
        """Test L3 query cache performance."""
        test_data = self.generate_test_data(200)

        # Performance metrics
        start_time = time.time()

        # Write performance test
        write_start = time.time()
        for item in test_data:
            await l3_cache.cache_query_result(item["query"], (), item["value"])
        write_time = time.time() - write_start

        # Read performance test
        read_start = time.time()
        hit_count = 0
        for item in test_data:
            result = await l3_cache.get_query_result(item["query"], ())
            if result is not None:
                hit_count += 1
        read_time = time.time() - read_start

        total_time = time.time() - start_time

        # Get cache stats
        stats = l3_cache.get_stats()

        # Performance assertions
        assert write_time < 5.0, f"L3 cache write time too slow: {write_time:.3f}s"
        assert read_time < 2.0, f"L3 cache read time too slow: {read_time:.3f}s"
        assert total_time < 10.0, f"L3 cache total time too slow: {total_time:.3f}s"

        # Hit rate assertions
        assert hit_count == len(test_data), (
            f"L3 cache hit count mismatch: {hit_count}/{len(test_data)}"
        )
        assert stats["hit_rate"] > 0.98, (
            f"L3 cache hit rate too low: {stats['hit_rate']:.3f}"
        )

        print(
            f"L3 Cache Performance: Write={write_time:.3f}s, Read={read_time:.3f}s, Hit Rate={stats['hit_rate']:.3f}"
        )

    @pytest.mark.asyncio
    async def test_multi_layer_cache_performance(self, multi_layer_cache):
        """Test multi-layer cache coordination and performance."""
        test_data = self.generate_test_data(300)

        # Performance metrics
        start_time = time.time()

        # Write performance test
        write_start = time.time()
        for item in test_data:
            await multi_layer_cache.set(item["key"], item["value"])
        write_time = time.time() - write_start

        # Read performance test (should hit L1 cache)
        read_start = time.time()
        hit_count = 0
        for item in test_data:
            result = await multi_layer_cache.get(item["key"])
            if result is not None:
                hit_count += 1
        read_time = time.time() - read_start

        total_time = time.time() - start_time

        # Get comprehensive stats
        stats = multi_layer_cache.get_comprehensive_stats()

        # Performance assertions
        assert write_time < 10.0, (
            f"Multi-layer cache write time too slow: {write_time:.3f}s"
        )
        assert read_time < 3.0, (
            f"Multi-layer cache read time too slow: {read_time:.3f}s"
        )
        assert total_time < 15.0, (
            f"Multi-layer cache total time too slow: {total_time:.3f}s"
        )

        # Hit rate assertions
        assert hit_count >= len(test_data) * 0.9, (
            f"Multi-layer cache hit count too low: {hit_count}/{len(test_data)}"
        )
        assert stats["overall_hit_rate"] > 0.85, (
            f"Multi-layer cache hit rate too low: {stats['overall_hit_rate']:.3f}"
        )

        print(
            f"Multi-layer Cache Performance: Write={write_time:.3f}s, Read={read_time:.3f}s, Hit Rate={stats['overall_hit_rate']:.3f}"
        )

    @pytest.mark.asyncio
    async def test_cache_hit_miss_ratios_under_load(self, l1_cache):
        """Test cache hit/miss ratios under high load."""
        test_data = self.generate_test_data(2000)

        # Phase 1: Populate cache
        for item in test_data[:1000]:
            await l1_cache.set(item["key"], item["value"])

        # Phase 2: Mixed read/write load
        hit_count = 0
        miss_count = 0

        for i in range(1000):
            # 70% reads, 30% writes
            if i % 10 < 7:
                # Read existing key
                key = test_data[i % 1000]["key"]
                result = await l1_cache.get(key)
                if result is not None:
                    hit_count += 1
                else:
                    miss_count += 1
            else:
                # Write new key
                new_item = test_data[1000 + (i % 1000)]
                await l1_cache.set(new_item["key"], new_item["value"])

        # Get final stats
        stats = l1_cache.get_stats()

        # Hit rate assertions
        total_reads = hit_count + miss_count
        read_hit_rate = hit_count / max(total_reads, 1)

        assert read_hit_rate > 0.8, (
            f"Cache hit rate too low under load: {read_hit_rate:.3f}"
        )
        assert stats["hit_rate"] > 0.7, (
            f"Overall hit rate too low: {stats['hit_rate']:.3f}"
        )

        print(
            f"Load Test: Read Hit Rate={read_hit_rate:.3f}, Overall Hit Rate={stats['hit_rate']:.3f}"
        )

    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self, multi_layer_cache):
        """Test cache performance under concurrent operations."""
        test_data = self.generate_test_data(500)

        async def write_worker(data_slice):
            """Worker function for concurrent writes."""
            for item in data_slice:
                await multi_layer_cache.set(item["key"], item["value"])

        async def read_worker(data_slice):
            """Worker function for concurrent reads."""
            hit_count = 0
            for item in data_slice:
                result = await multi_layer_cache.get(item["key"])
                if result is not None:
                    hit_count += 1
            return hit_count

        # Concurrent write test
        write_start = time.time()
        chunk_size = len(test_data) // 4
        write_tasks = []

        for i in range(4):
            start_idx = i * chunk_size
            end_idx = start_idx + chunk_size if i < 3 else len(test_data)
            data_slice = test_data[start_idx:end_idx]
            write_tasks.append(write_worker(data_slice))

        await asyncio.gather(*write_tasks)
        write_time = time.time() - write_start

        # Concurrent read test
        read_start = time.time()
        read_tasks = []

        for i in range(4):
            start_idx = i * chunk_size
            end_idx = start_idx + chunk_size if i < 3 else len(test_data)
            data_slice = test_data[start_idx:end_idx]
            read_tasks.append(read_worker(data_slice))

        read_results = await asyncio.gather(*read_tasks)
        read_time = time.time() - read_start

        total_hits = sum(read_results)

        # Performance assertions
        assert write_time < 15.0, f"Concurrent write time too slow: {write_time:.3f}s"
        assert read_time < 5.0, f"Concurrent read time too slow: {read_time:.3f}s"

        # Hit rate assertions
        hit_rate = total_hits / len(test_data)
        assert hit_rate > 0.85, f"Concurrent hit rate too low: {hit_rate:.3f}"

        print(
            f"Concurrent Performance: Write={write_time:.3f}s, Read={read_time:.3f}s, Hit Rate={hit_rate:.3f}"
        )

    @pytest.mark.asyncio
    async def test_memory_usage_and_cleanup(self, l1_cache):
        """Test memory usage and cleanup performance."""
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Fill cache to near capacity
        large_data = []
        for i in range(100):
            large_value = "".join(
                random.choices(string.ascii_letters, k=10240)
            )  # 10KB values
            large_data.append({"key": f"large_key_{i}", "value": large_value})

        # Write large data
        write_start = time.time()
        for item in large_data:
            await l1_cache.set(item["key"], item["value"])
        write_time = time.time() - write_start

        # Check memory usage
        mid_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = mid_memory - initial_memory

        # Get cache stats
        stats = l1_cache.get_stats()

        # Trigger cleanup by adding more data
        for i in range(100, 200):
            large_value = "".join(
                random.choices(string.ascii_letters, k=10240)
            )  # 10KB values
            await l1_cache.set(f"cleanup_key_{i}", large_value)

        # Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Performance assertions
        assert write_time < 5.0, f"Large data write time too slow: {write_time:.3f}s"
        assert memory_increase < 200, (
            f"Memory increase too high: {memory_increase:.1f}MB"
        )
        assert stats["memory_usage_mb"] > 0, "Cache should report memory usage"

        # Cleanup should prevent unlimited growth
        memory_growth = final_memory - mid_memory
        assert memory_growth < 100, (
            f"Memory growth after cleanup too high: {memory_growth:.1f}MB"
        )

        print(
            f"Memory Test: Write={write_time:.3f}s, Memory Increase={memory_increase:.1f}MB, Growth={memory_growth:.1f}MB"
        )

    @pytest.mark.asyncio
    async def test_cache_invalidation_performance(self, multi_layer_cache):
        """Test cache invalidation performance."""
        test_data = self.generate_test_data(500)

        # Populate cache with user-specific data
        for item in test_data:
            user_key = f"memory:user:{item['user_id']}:{item['key']}"
            await multi_layer_cache.set(user_key, item["value"])

        # Test user-specific invalidation
        invalidation_start = time.time()
        await multi_layer_cache.invalidate_user_cache("user_5")
        invalidation_time = time.time() - invalidation_start

        # Verify invalidation worked
        invalidated_count = 0
        remaining_count = 0

        for item in test_data:
            user_key = f"memory:user:{item['user_id']}:{item['key']}"
            result = await multi_layer_cache.get(user_key)

            if item["user_id"] == "user_5":
                if result is None:
                    invalidated_count += 1
            else:
                if result is not None:
                    remaining_count += 1

        # Performance assertions
        assert invalidation_time < 2.0, (
            f"Invalidation time too slow: {invalidation_time:.3f}s"
        )

        # Correctness assertions
        user_5_items = len([item for item in test_data if item["user_id"] == "user_5"])
        assert invalidated_count >= user_5_items * 0.8, (
            f"Invalidation incomplete: {invalidated_count}/{user_5_items}"
        )

        print(
            f"Invalidation Performance: Time={invalidation_time:.3f}s, Invalidated={invalidated_count}/{user_5_items}"
        )

    def test_configuration_validation(self):
        """Test configuration validation performance and correctness."""
        # Test valid configuration
        valid_config = MultiLayerCacheConfig(
            l1_max_size=64 * 1024 * 1024,
            l1_ttl=300,
            l2_max_size=256 * 1024 * 1024,
            l2_ttl=1800,
            l3_ttl=900,
            l3_max_prepared_statements=500,
        )

        # Should not raise exception
        assert valid_config.l1_max_size == 64 * 1024 * 1024

        # Test invalid configurations
        with pytest.raises(ValueError, match="L1 cache must be at least 1MB"):
            MultiLayerCacheConfig(l1_max_size=512 * 1024)  # 512KB

        with pytest.raises(
            ValueError, match="L1 TTL must be between 60 and 86400 seconds"
        ):
            MultiLayerCacheConfig(l1_ttl=30)  # 30 seconds

        with pytest.raises(ValueError, match="L2 Redis URL must start with"):
            MultiLayerCacheConfig(l2_redis_url="http://localhost:6379")

        with pytest.raises(
            ValueError, match="L3 max prepared statements must be between"
        ):
            MultiLayerCacheConfig(l3_max_prepared_statements=50)

        print("Configuration validation tests passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
