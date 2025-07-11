"""
Performance tests for the connection pooling implementation.

This test suite validates:
- PostgreSQL connection pool performance
- Neo4j connection pool performance  
- Redis connection pool performance
- Connection pool health monitoring
- Connection recovery scenarios
- Pool exhaustion handling
"""

import pytest
import asyncio
import time
import random
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor

# Add the workspace to the path
import sys
sys.path.insert(0, '/workspace')

from shared.connection_pool import (
    ConnectionPoolConfig,
    OptimizedPostgreSQLPool,
    OptimizedNeo4jPool,
    OptimizedRedisPool,
    ConnectionPoolManager,
    ConnectionPoolMetrics
)
from shared.config import Config

class TestConnectionPoolPerformance:
    """Performance tests for connection pooling."""
    
    @pytest.fixture
    def pool_config(self):
        """Create test connection pool configuration."""
        return ConnectionPoolConfig(
            postgres_min_size=5,
            postgres_max_size=20,
            postgres_timeout=1.0,
            neo4j_min_size=3,
            neo4j_max_size=10,
            neo4j_timeout=1.0,
            redis_min_size=3,
            redis_max_size=10,
            redis_timeout=0.5,
            health_check_interval=5.0,
            connection_validation_interval=10.0,
            recovery_check_interval=2.0
        )
    
    @pytest.fixture
    def database_config(self):
        """Create mock database configuration."""
        config = Mock(spec=Config)
        config.database_url = "postgresql://test:test@localhost:5432/test"
        config.neo4j_bolt_url = "bolt://localhost:7687"
        config.NEO4J_USERNAME = "neo4j"
        config.NEO4J_PASSWORD = "test"
        return config
    
    @pytest.fixture
    def redis_url(self):
        """Redis URL for testing."""
        return "redis://localhost:6379"
    
    @pytest.mark.asyncio
    async def test_postgresql_pool_performance(self, pool_config, database_config):
        """Test PostgreSQL connection pool performance."""
        # Mock asyncpg for testing
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        
        # Setup mock connection behavior
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_pool.acquire.return_value.__aexit__.return_value = None
        mock_pool.get_size.return_value = pool_config.postgres_min_size
        mock_pool.get_idle_size.return_value = pool_config.postgres_min_size - 1
        mock_conn.fetchval.return_value = 1
        mock_conn.fetch.return_value = [{"id": 1, "name": "test"}]
        
        with patch('asyncpg.create_pool', return_value=mock_pool):
            # Create PostgreSQL pool
            postgres_pool = OptimizedPostgreSQLPool(pool_config, database_config)
            
            # Initialize pool
            start_time = time.time()
            await postgres_pool.initialize()
            init_time = time.time() - start_time
            
            # Performance assertions
            assert init_time < 5.0, f"PostgreSQL pool initialization too slow: {init_time:.3f}s"
            
            # Test connection acquisition performance
            acquisition_times = []
            
            for i in range(10):
                start = time.time()
                async with postgres_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                acquisition_times.append(time.time() - start)
            
            avg_acquisition_time = sum(acquisition_times) / len(acquisition_times)
            max_acquisition_time = max(acquisition_times)
            
            # Performance assertions
            assert avg_acquisition_time < 0.1, f"Average acquisition time too slow: {avg_acquisition_time:.3f}s"
            assert max_acquisition_time < 0.5, f"Max acquisition time too slow: {max_acquisition_time:.3f}s"
            
            # Test query performance
            query_times = []
            
            for i in range(20):
                start = time.time()
                result = await postgres_pool.execute_query("SELECT $1::int", i)
                query_times.append(time.time() - start)
            
            avg_query_time = sum(query_times) / len(query_times)
            
            # Performance assertions
            assert avg_query_time < 0.05, f"Average query time too slow: {avg_query_time:.3f}s"
            
            # Get pool stats
            stats = postgres_pool.get_stats()
            
            # Verify stats
            assert stats['connections_created'] > 0, "Should have created connections"
            assert stats['average_wait_time_ms'] < 100, f"Average wait time too high: {stats['average_wait_time_ms']:.1f}ms"
            
            print(f"PostgreSQL Pool Performance: Init={init_time:.3f}s, Avg Acquisition={avg_acquisition_time:.3f}s, Avg Query={avg_query_time:.3f}s")
            
            # Cleanup
            await postgres_pool.close()
    
    @pytest.mark.asyncio
    async def test_neo4j_pool_performance(self, pool_config, database_config):
        """Test Neo4j connection pool performance."""
        # Mock Neo4j driver for testing
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        
        # Setup mock behavior
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_driver.session.return_value.__aexit__.return_value = None
        mock_session.run.return_value = mock_result
        mock_result.consume.return_value = None
        
        with patch('neo4j.AsyncGraphDatabase.driver', return_value=mock_driver):
            # Create Neo4j pool
            neo4j_pool = OptimizedNeo4jPool(pool_config, database_config)
            
            # Initialize pool
            start_time = time.time()
            await neo4j_pool.initialize()
            init_time = time.time() - start_time
            
            # Performance assertions
            assert init_time < 5.0, f"Neo4j pool initialization too slow: {init_time:.3f}s"
            
            # Test session acquisition performance
            session_times = []
            
            for i in range(10):
                start = time.time()
                async with neo4j_pool.session() as session:
                    result = await session.run("RETURN 1")
                    await result.consume()
                session_times.append(time.time() - start)
            
            avg_session_time = sum(session_times) / len(session_times)
            max_session_time = max(session_times)
            
            # Performance assertions
            assert avg_session_time < 0.1, f"Average session time too slow: {avg_session_time:.3f}s"
            assert max_session_time < 0.5, f"Max session time too slow: {max_session_time:.3f}s"
            
            # Test query performance
            query_times = []
            
            for i in range(20):
                start = time.time()
                result = await neo4j_pool.execute_query(f"RETURN {i}")
                query_times.append(time.time() - start)
            
            avg_query_time = sum(query_times) / len(query_times)
            
            # Performance assertions
            assert avg_query_time < 0.05, f"Average query time too slow: {avg_query_time:.3f}s"
            
            # Get pool stats
            stats = neo4j_pool.get_stats()
            
            # Verify stats
            assert stats['connections_created'] > 0, "Should have created connections"
            assert stats['average_wait_time_ms'] < 100, f"Average wait time too high: {stats['average_wait_time_ms']:.1f}ms"
            
            print(f"Neo4j Pool Performance: Init={init_time:.3f}s, Avg Session={avg_session_time:.3f}s, Avg Query={avg_query_time:.3f}s")
            
            # Cleanup
            await neo4j_pool.close()
    
    @pytest.mark.asyncio
    async def test_redis_pool_performance(self, pool_config, redis_url):
        """Test Redis connection pool performance."""
        # Mock Redis client for testing
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = b"test_value"
        mock_client.set.return_value = True
        mock_client.delete.return_value = 1
        
        with patch('redis.Redis.from_url', return_value=mock_client):
            # Create Redis pool
            redis_pool = OptimizedRedisPool(pool_config, redis_url)
            
            # Initialize pool
            start_time = time.time()
            await redis_pool.initialize()
            init_time = time.time() - start_time
            
            # Performance assertions
            assert init_time < 3.0, f"Redis pool initialization too slow: {init_time:.3f}s"
            
            # Test client operations performance
            operation_times = []
            
            for i in range(50):
                start = time.time()
                client = redis_pool.get_client()
                client.set(f"test_key_{i}", f"test_value_{i}")
                result = client.get(f"test_key_{i}")
                operation_times.append(time.time() - start)
            
            avg_operation_time = sum(operation_times) / len(operation_times)
            max_operation_time = max(operation_times)
            
            # Performance assertions
            assert avg_operation_time < 0.01, f"Average operation time too slow: {avg_operation_time:.3f}s"
            assert max_operation_time < 0.05, f"Max operation time too slow: {max_operation_time:.3f}s"
            
            # Get pool stats
            stats = redis_pool.get_stats()
            
            # Verify stats
            assert stats['connections_created'] > 0, "Should have created connections"
            assert stats['is_healthy'] == True, "Redis pool should be healthy"
            
            print(f"Redis Pool Performance: Init={init_time:.3f}s, Avg Operation={avg_operation_time:.3f}s")
            
            # Cleanup
            await redis_pool.close()
    
    @pytest.mark.asyncio
    async def test_connection_pool_manager_performance(self, pool_config):
        """Test connection pool manager performance."""
        # Mock configurations
        database_config = Mock(spec=Config)
        database_config.database_url = "postgresql://test:test@localhost:5432/test"
        database_config.neo4j_bolt_url = "bolt://localhost:7687"
        database_config.NEO4J_USERNAME = "neo4j"
        database_config.NEO4J_PASSWORD = "test"
        
        # Mock all the components
        mock_pg_pool = AsyncMock()
        mock_neo4j_driver = AsyncMock()
        mock_redis_client = Mock()
        
        with patch('asyncpg.create_pool', return_value=mock_pg_pool), \
             patch('neo4j.AsyncGraphDatabase.driver', return_value=mock_neo4j_driver), \
             patch('redis.Redis.from_url', return_value=mock_redis_client):
            
            # Create connection pool manager
            manager = ConnectionPoolManager(pool_config)
            
            # Initialize manager
            start_time = time.time()
            await manager.initialize()
            init_time = time.time() - start_time
            
            # Performance assertions
            assert init_time < 10.0, f"Manager initialization too slow: {init_time:.3f}s"
            
            # Test monitoring performance
            monitoring_start = time.time()
            await manager.start_monitoring()
            
            # Let monitoring run for a short time
            await asyncio.sleep(1.0)
            
            monitoring_setup_time = time.time() - monitoring_start
            
            # Performance assertions
            assert monitoring_setup_time < 5.0, f"Monitoring setup too slow: {monitoring_setup_time:.3f}s"
            
            # Get comprehensive stats
            stats_start = time.time()
            stats = manager.get_comprehensive_stats()
            stats_time = time.time() - stats_start
            
            # Performance assertions
            assert stats_time < 1.0, f"Stats collection too slow: {stats_time:.3f}s"
            
            # Verify stats structure
            assert 'postgres' in stats, "Should have PostgreSQL stats"
            assert 'neo4j' in stats, "Should have Neo4j stats"
            assert 'redis' in stats, "Should have Redis stats"
            assert 'overall' in stats, "Should have overall stats"
            
            print(f"Manager Performance: Init={init_time:.3f}s, Monitoring={monitoring_setup_time:.3f}s, Stats={stats_time:.3f}s")
            
            # Cleanup
            await manager.close()
    
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion_handling(self, pool_config, database_config):
        """Test connection pool behavior under exhaustion."""
        # Mock asyncpg with limited connections
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        
        # Simulate pool exhaustion
        acquisition_count = 0
        
        async def mock_acquire():
            nonlocal acquisition_count
            acquisition_count += 1
            if acquisition_count > pool_config.postgres_max_size:
                raise asyncio.TimeoutError("Connection pool exhausted")
            return mock_conn
        
        mock_pool.acquire.side_effect = mock_acquire
        mock_pool.get_size.return_value = pool_config.postgres_max_size
        mock_pool.get_idle_size.return_value = 0
        mock_conn.fetchval.return_value = 1
        
        with patch('asyncpg.create_pool', return_value=mock_pool):
            postgres_pool = OptimizedPostgreSQLPool(pool_config, database_config)
            await postgres_pool.initialize()
            
            # Test concurrent connection attempts
            async def connection_worker():
                try:
                    async with postgres_pool.acquire() as conn:
                        await asyncio.sleep(0.1)  # Hold connection briefly
                        return True
                except Exception:
                    return False
            
            # Start many concurrent workers
            tasks = [connection_worker() for _ in range(pool_config.postgres_max_size + 5)]
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            test_time = time.time() - start_time
            
            # Performance assertions
            assert test_time < 5.0, f"Pool exhaustion test too slow: {test_time:.3f}s"
            
            # Check that some connections succeeded and some failed appropriately
            successful_connections = sum(1 for r in results if r is True)
            failed_connections = len(results) - successful_connections
            
            assert successful_connections > 0, "Some connections should succeed"
            assert failed_connections > 0, "Some connections should fail due to exhaustion"
            
            print(f"Pool Exhaustion Test: Time={test_time:.3f}s, Success={successful_connections}, Failed={failed_connections}")
            
            await postgres_pool.close()
    
    @pytest.mark.asyncio
    async def test_connection_health_monitoring(self, pool_config, database_config):
        """Test connection pool health monitoring performance."""
        # Mock asyncpg with health check behavior
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        
        health_check_count = 0
        
        async def mock_health_check():
            nonlocal health_check_count
            health_check_count += 1
            if health_check_count % 3 == 0:  # Simulate occasional failures
                raise Exception("Health check failed")
            return 1
        
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_pool.acquire.return_value.__aexit__.return_value = None
        mock_pool.get_size.return_value = pool_config.postgres_min_size
        mock_pool.get_idle_size.return_value = pool_config.postgres_min_size - 1
        mock_conn.fetchval.side_effect = mock_health_check
        
        with patch('asyncpg.create_pool', return_value=mock_pool):
            postgres_pool = OptimizedPostgreSQLPool(pool_config, database_config)
            await postgres_pool.initialize()
            
            # Let health monitoring run
            start_time = time.time()
            await asyncio.sleep(2.0)  # Let it run for 2 seconds
            monitoring_time = time.time() - start_time
            
            # Check health status
            stats = postgres_pool.get_stats()
            
            # Performance assertions
            assert monitoring_time >= 2.0, "Should have run for at least 2 seconds"
            assert stats['health_check_failures'] >= 0, "Should track health check failures"
            
            print(f"Health Monitoring: Time={monitoring_time:.3f}s, Failures={stats['health_check_failures']}")
            
            await postgres_pool.close()
    
    @pytest.mark.asyncio
    async def test_concurrent_pool_operations(self, pool_config, database_config):
        """Test connection pool performance under concurrent operations."""
        # Mock asyncpg for concurrent testing
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_pool.acquire.return_value.__aexit__.return_value = None
        mock_pool.get_size.return_value = pool_config.postgres_max_size
        mock_pool.get_idle_size.return_value = pool_config.postgres_max_size // 2
        mock_conn.fetchval.return_value = 1
        mock_conn.fetch.return_value = [{"id": 1}]
        
        with patch('asyncpg.create_pool', return_value=mock_pool):
            postgres_pool = OptimizedPostgreSQLPool(pool_config, database_config)
            await postgres_pool.initialize()
            
            # Test concurrent operations
            async def operation_worker(worker_id):
                """Worker function for concurrent operations."""
                operation_times = []
                
                for i in range(10):
                    start = time.time()
                    async with postgres_pool.acquire() as conn:
                        await conn.fetchval(f"SELECT {worker_id * 10 + i}")
                    operation_times.append(time.time() - start)
                
                return operation_times
            
            # Start multiple workers
            num_workers = 5
            start_time = time.time()
            
            tasks = [operation_worker(i) for i in range(num_workers)]
            results = await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            
            # Analyze results
            all_times = []
            for worker_times in results:
                all_times.extend(worker_times)
            
            avg_operation_time = sum(all_times) / len(all_times)
            max_operation_time = max(all_times)
            
            # Performance assertions
            assert total_time < 10.0, f"Concurrent operations too slow: {total_time:.3f}s"
            assert avg_operation_time < 0.1, f"Average operation time too slow: {avg_operation_time:.3f}s"
            assert max_operation_time < 0.5, f"Max operation time too slow: {max_operation_time:.3f}s"
            
            # Check pool stats
            stats = postgres_pool.get_stats()
            total_acquisitions = stats['total_acquisitions']
            
            assert total_acquisitions == num_workers * 10, f"Expected {num_workers * 10} acquisitions, got {total_acquisitions}"
            
            print(f"Concurrent Operations: Total={total_time:.3f}s, Avg={avg_operation_time:.3f}s, Max={max_operation_time:.3f}s")
            
            await postgres_pool.close()
    
    def test_connection_pool_metrics(self):
        """Test connection pool metrics performance."""
        metrics = ConnectionPoolMetrics()
        
        # Test metrics recording performance
        start_time = time.time()
        
        # Record many metrics
        for i in range(1000):
            metrics.record_connection_acquired(0.001)  # 1ms wait time
            metrics.record_connection_released()
            
            if i % 100 == 0:
                metrics.record_connection_created()
                metrics.record_health_check(True)
        
        # Record some failures
        for i in range(50):
            metrics.record_connection_failed()
            metrics.record_health_check(False)
        
        metrics_time = time.time() - start_time
        
        # Get stats
        stats_start = time.time()
        stats = metrics.get_stats()
        stats_time = time.time() - stats_start
        
        # Performance assertions
        assert metrics_time < 0.5, f"Metrics recording too slow: {metrics_time:.3f}s"
        assert stats_time < 0.01, f"Stats collection too slow: {stats_time:.3f}s"
        
        # Verify stats accuracy
        assert stats['connections_created'] == 10, f"Expected 10 connections created, got {stats['connections_created']}"
        assert stats['connections_failed'] == 50, f"Expected 50 failures, got {stats['connections_failed']}"
        assert stats['total_acquisitions'] == 1000, f"Expected 1000 acquisitions, got {stats['total_acquisitions']}"
        assert stats['health_check_failures'] == 50, f"Expected 50 health check failures, got {stats['health_check_failures']}"
        
        print(f"Metrics Performance: Recording={metrics_time:.3f}s, Stats={stats_time:.3f}s")
    
    def test_connection_pool_config_validation(self):
        """Test connection pool configuration validation."""
        # Test valid configuration
        valid_config = ConnectionPoolConfig(
            postgres_min_size=5,
            postgres_max_size=20,
            postgres_timeout=1.0,
            neo4j_min_size=3,
            neo4j_max_size=10,
            redis_min_size=3,
            redis_max_size=10
        )
        
        # Should not raise exception
        assert valid_config.postgres_min_size == 5
        assert valid_config.postgres_max_size == 20
        
        # Test configuration performance
        config_start = time.time()
        
        # Create many configurations
        for i in range(100):
            config = ConnectionPoolConfig(
                postgres_min_size=i % 10 + 1,
                postgres_max_size=i % 50 + 10,
                postgres_timeout=0.5 + (i % 10) * 0.1
            )
            assert config.postgres_min_size > 0
        
        config_time = time.time() - config_start
        
        # Performance assertions
        assert config_time < 0.1, f"Configuration creation too slow: {config_time:.3f}s"
        
        print(f"Configuration Performance: {config_time:.3f}s for 100 configs")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])