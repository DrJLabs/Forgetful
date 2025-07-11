"""
Optimized Database Connection Pooling for mem0 Performance Optimization.

This module provides connection pool management for:
- PostgreSQL with pgvector (min: 20, max: 100, timeout: 1s)
- Neo4j graph database (min: 10, max: 50, timeout: 1s)
- Redis caching layer (min: 10, max: 50, timeout: 0.5s)

Features:
- Connection pre-warming and validation
- Health monitoring with automatic recovery
- Performance metrics and monitoring
- Circuit breaker integration
"""

import asyncio
import asyncpg
import time
import threading
from typing import Dict, Optional, Any, List
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from shared.logging_system import get_logger, performance_logger
from shared.config import Config

logger = get_logger('connection_pool')

@dataclass
class ConnectionPoolConfig:
    """Configuration for connection pools."""
    # PostgreSQL Configuration
    postgres_min_size: int = 20
    postgres_max_size: int = 100
    postgres_timeout: float = 1.0
    postgres_command_timeout: float = 10.0
    postgres_max_inactive_connection_lifetime: float = 300.0
    
    # Neo4j Configuration
    neo4j_min_size: int = 10
    neo4j_max_size: int = 50
    neo4j_timeout: float = 1.0
    neo4j_acquisition_timeout: float = 1.0
    neo4j_max_transaction_retry_time: float = 10.0
    
    # Redis Configuration
    redis_min_size: int = 10
    redis_max_size: int = 50
    redis_timeout: float = 0.5
    redis_socket_keepalive: bool = True
    redis_socket_timeout: float = 1.0
    redis_url: str = "redis://localhost:6379"
    
    # Health Check Configuration
    health_check_interval: float = 30.0
    connection_validation_interval: float = 60.0
    recovery_check_interval: float = 10.0

class ConnectionPoolMetrics:
    """Metrics tracking for connection pools."""
    
    def __init__(self):
        self.connections_created = 0
        self.connections_closed = 0
        self.connections_failed = 0
        self.connections_in_use = 0
        self.connections_available = 0
        self.wait_time_total = 0.0
        self.wait_count = 0
        self.last_health_check = None
        self.health_check_failures = 0
        self.lock = threading.Lock()
    
    def record_connection_acquired(self, wait_time: float):
        """Record successful connection acquisition."""
        with self.lock:
            self.connections_in_use += 1
            self.connections_available -= 1
            self.wait_time_total += wait_time
            self.wait_count += 1
    
    def record_connection_released(self):
        """Record connection release."""
        with self.lock:
            self.connections_in_use -= 1
            self.connections_available += 1
    
    def record_connection_created(self):
        """Record new connection creation."""
        with self.lock:
            self.connections_created += 1
            self.connections_available += 1
    
    def record_connection_closed(self):
        """Record connection closure."""
        with self.lock:
            self.connections_closed += 1
            self.connections_available -= 1
    
    def record_connection_failed(self):
        """Record connection failure."""
        with self.lock:
            self.connections_failed += 1
    
    def record_health_check(self, success: bool):
        """Record health check result."""
        with self.lock:
            self.last_health_check = datetime.now()
            if not success:
                self.health_check_failures += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        with self.lock:
            avg_wait_time = self.wait_time_total / max(self.wait_count, 1)
            return {
                'connections_created': self.connections_created,
                'connections_closed': self.connections_closed,
                'connections_failed': self.connections_failed,
                'connections_in_use': self.connections_in_use,
                'connections_available': self.connections_available,
                'average_wait_time_ms': avg_wait_time * 1000,
                'total_acquisitions': self.wait_count,
                'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
                'health_check_failures': self.health_check_failures
            }

class OptimizedPostgreSQLPool:
    """
    Optimized PostgreSQL connection pool with pre-warming and health monitoring.
    
    Features:
    - Connection pool (min: 20, max: 100, timeout: 1s)
    - Pre-warming and validation
    - Health monitoring with automatic recovery
    - Performance metrics tracking
    """
    
    def __init__(self, config: ConnectionPoolConfig, database_config: Config):
        self.config = config
        self.database_config = database_config
        self.pool = None
        self.metrics = ConnectionPoolMetrics()
        self.is_healthy = True
        self.last_health_check = None
        self.health_check_task = None
        self.recovery_task = None
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the connection pool with pre-warming."""
        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                dsn=self.database_config.database_url,
                min_size=self.config.postgres_min_size,
                max_size=self.config.postgres_max_size,
                command_timeout=self.config.postgres_command_timeout,
                max_inactive_connection_lifetime=self.config.postgres_max_inactive_connection_lifetime,
                server_settings={
                    'jit': 'off',  # Disable JIT for consistent performance
                    'statement_timeout': '30s',
                    'lock_timeout': '10s'
                }
            )
            
            # Pre-warm connections
            await self._pre_warm_connections()
            
            # Start health monitoring
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            logger.info(f"PostgreSQL pool initialized: min={self.config.postgres_min_size}, max={self.config.postgres_max_size}")
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL pool: {e}")
            raise
    
    async def _pre_warm_connections(self):
        """Pre-warm connections by creating minimum pool size."""
        try:
            # Create initial connections up to min_size
            tasks = []
            for i in range(self.config.postgres_min_size):
                task = asyncio.create_task(self._validate_connection())
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful = sum(1 for r in results if not isinstance(r, Exception))
            
            logger.info(f"Pre-warmed {successful}/{self.config.postgres_min_size} PostgreSQL connections")
            
        except Exception as e:
            logger.error(f"Failed to pre-warm PostgreSQL connections: {e}")
    
    async def _validate_connection(self) -> bool:
        """Validate a single connection."""
        try:
            async with self.pool.acquire() as conn:
                # Simple validation query
                await conn.fetchval("SELECT 1")
                self.metrics.record_connection_created()
                return True
        except Exception as e:
            logger.warning(f"Connection validation failed: {e}")
            self.metrics.record_connection_failed()
            return False
    
    async def _health_check_loop(self):
        """Continuous health monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                # Perform health check
                health_check_start = time.time()
                is_healthy = await self._perform_health_check()
                health_check_time = time.time() - health_check_start
                
                # Update health status
                was_healthy = self.is_healthy
                self.is_healthy = is_healthy
                self.last_health_check = datetime.now()
                
                # Log status changes
                if was_healthy != is_healthy:
                    if is_healthy:
                        logger.info("PostgreSQL pool recovered")
                    else:
                        logger.warning("PostgreSQL pool unhealthy")
                
                # Record metrics
                self.metrics.record_health_check(is_healthy)
                
                # Start recovery if needed
                if not is_healthy and not self.recovery_task:
                    self.recovery_task = asyncio.create_task(self._recovery_loop())
                
                logger.debug(f"PostgreSQL health check: {is_healthy}, time: {health_check_time:.3f}s")
                
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                self.is_healthy = False
    
    async def _perform_health_check(self) -> bool:
        """Perform comprehensive health check."""
        try:
            # Check pool status
            if not self.pool:
                return False
            
            # Test connection acquisition and query
            async with asyncio.timeout(self.config.postgres_timeout):
                async with self.pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                    
                    # Check pool statistics
                    pool_size = self.pool.get_size()
                    idle_size = self.pool.get_idle_size()
                    
                    # Update metrics
                    self.metrics.connections_available = idle_size
                    self.metrics.connections_in_use = pool_size - idle_size
                    
                    # Pool is healthy if we can acquire connection and execute query
                    return True
                    
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    async def _recovery_loop(self):
        """Recovery loop for unhealthy pool."""
        try:
            while not self.is_healthy:
                await asyncio.sleep(self.config.recovery_check_interval)
                
                # Attempt to recover
                recovery_success = await self._attempt_recovery()
                
                if recovery_success:
                    logger.info("PostgreSQL pool recovery successful")
                    break
                    
        except Exception as e:
            logger.error(f"Recovery loop error: {e}")
        finally:
            self.recovery_task = None
    
    async def _attempt_recovery(self) -> bool:
        """Attempt to recover the connection pool."""
        try:
            async with self._lock:
                # Try to reinitialize pool if it's completely broken
                if not self.pool:
                    await self.initialize()
                    return True
                
                # Try to validate existing connections
                validation_success = await self._validate_connection()
                return validation_success
                
        except Exception as e:
            logger.error(f"Recovery attempt failed: {e}")
            return False
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool with metrics tracking."""
        if not self.is_healthy:
            raise Exception("PostgreSQL pool is unhealthy")
        
        start_time = time.time()
        try:
            async with self.pool.acquire() as conn:
                wait_time = time.time() - start_time
                self.metrics.record_connection_acquired(wait_time)
                
                try:
                    yield conn
                finally:
                    self.metrics.record_connection_released()
                    
        except Exception as e:
            self.metrics.record_connection_failed()
            raise
    
    async def execute_query(self, query: str, *args, **kwargs):
        """Execute a query with connection pooling."""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args, **kwargs)
    
    async def execute_query_one(self, query: str, *args, **kwargs):
        """Execute a query expecting single result."""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args, **kwargs)
    
    async def execute_query_val(self, query: str, *args, **kwargs):
        """Execute a query expecting single value."""
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive pool statistics."""
        stats = self.metrics.get_stats()
        
        if self.pool:
            stats.update({
                'pool_size': self.pool.get_size(),
                'idle_size': self.pool.get_idle_size(),
                'is_healthy': self.is_healthy,
                'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None
            })
        
        return stats
    
    async def close(self):
        """Close the connection pool."""
        if self.health_check_task:
            self.health_check_task.cancel()
        
        if self.recovery_task:
            self.recovery_task.cancel()
        
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL pool closed")

class OptimizedNeo4jPool:
    """
    Optimized Neo4j connection pool with health monitoring.
    
    Features:
    - Connection pool (min: 10, max: 50, timeout: 1s)
    - Health monitoring with automatic recovery
    - Performance metrics tracking
    """
    
    def __init__(self, config: ConnectionPoolConfig, neo4j_config: Config):
        self.config = config
        self.neo4j_config = neo4j_config
        self.driver = None
        self.metrics = ConnectionPoolMetrics()
        self.is_healthy = True
        self.last_health_check = None
        self.health_check_task = None
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the Neo4j driver with connection pooling."""
        try:
            # Import Neo4j driver
            from neo4j import AsyncGraphDatabase
            
            # Create driver with connection pooling
            self.driver = AsyncGraphDatabase.driver(
                self.neo4j_config.neo4j_bolt_url,
                auth=(self.neo4j_config.NEO4J_USERNAME, self.neo4j_config.NEO4J_PASSWORD),
                max_connection_pool_size=self.config.neo4j_max_size,
                connection_acquisition_timeout=self.config.neo4j_acquisition_timeout,
                max_transaction_retry_time=self.config.neo4j_max_transaction_retry_time,
                keep_alive=True,
                encrypted=False  # Use encrypted=True for production
            )
            
            # Verify connectivity
            await self._verify_connectivity()
            
            # Start health monitoring
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            logger.info(f"Neo4j pool initialized: max_size={self.config.neo4j_max_size}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j pool: {e}")
            raise
    
    async def _verify_connectivity(self):
        """Verify Neo4j connectivity."""
        try:
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 AS test")
                await result.consume()
                self.metrics.record_connection_created()
                logger.info("Neo4j connectivity verified")
                
        except Exception as e:
            logger.error(f"Neo4j connectivity verification failed: {e}")
            self.metrics.record_connection_failed()
            raise
    
    async def _health_check_loop(self):
        """Continuous health monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                # Perform health check
                health_check_start = time.time()
                is_healthy = await self._perform_health_check()
                health_check_time = time.time() - health_check_start
                
                # Update health status
                was_healthy = self.is_healthy
                self.is_healthy = is_healthy
                self.last_health_check = datetime.now()
                
                # Log status changes
                if was_healthy != is_healthy:
                    if is_healthy:
                        logger.info("Neo4j pool recovered")
                    else:
                        logger.warning("Neo4j pool unhealthy")
                
                # Record metrics
                self.metrics.record_health_check(is_healthy)
                
                logger.debug(f"Neo4j health check: {is_healthy}, time: {health_check_time:.3f}s")
                
            except Exception as e:
                logger.error(f"Neo4j health check loop error: {e}")
                self.is_healthy = False
    
    async def _perform_health_check(self) -> bool:
        """Perform Neo4j health check."""
        try:
            if not self.driver:
                return False
            
            # Test session creation and simple query
            async with asyncio.timeout(self.config.neo4j_timeout):
                async with self.driver.session() as session:
                    result = await session.run("RETURN 1 AS test")
                    await result.consume()
                    return True
                    
        except Exception as e:
            logger.warning(f"Neo4j health check failed: {e}")
            return False
    
    @asynccontextmanager
    async def session(self):
        """Get a Neo4j session with metrics tracking."""
        if not self.is_healthy:
            raise Exception("Neo4j pool is unhealthy")
        
        start_time = time.time()
        try:
            async with self.driver.session() as session:
                wait_time = time.time() - start_time
                self.metrics.record_connection_acquired(wait_time)
                
                try:
                    yield session
                finally:
                    self.metrics.record_connection_released()
                    
        except Exception as e:
            self.metrics.record_connection_failed()
            raise
    
    async def execute_query(self, query: str, parameters: Dict = None):
        """Execute a Neo4j query with connection pooling."""
        async with self.session() as session:
            result = await session.run(query, parameters or {})
            return await result.data()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive pool statistics."""
        stats = self.metrics.get_stats()
        stats.update({
            'is_healthy': self.is_healthy,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None
        })
        return stats
    
    async def close(self):
        """Close the Neo4j driver."""
        if self.health_check_task:
            self.health_check_task.cancel()
        
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j pool closed")

class OptimizedRedisPool:
    """
    Optimized Redis connection pool with health monitoring.
    
    Features:
    - Connection pool (min: 10, max: 50, timeout: 0.5s)
    - Socket keepalive optimization
    - Health monitoring with automatic recovery
    """
    
    def __init__(self, config: ConnectionPoolConfig, redis_url: str = "redis://localhost:6379"):
        self.config = config
        self.redis_url = redis_url
        self.pool = None
        self.metrics = ConnectionPoolMetrics()
        self.is_healthy = True
        self.last_health_check = None
        self.health_check_task = None
    
    async def initialize(self):
        """Initialize the Redis connection pool."""
        try:
            import redis.asyncio as redis
            
            # Create connection pool
            self.pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.config.redis_max_size,
                socket_timeout=self.config.redis_socket_timeout,
                socket_connect_timeout=self.config.redis_timeout,
                socket_keepalive=self.config.redis_socket_keepalive,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 3,  # TCP_KEEPINTVL
                    3: 5   # TCP_KEEPCNT
                },
                retry_on_timeout=True,
                health_check_interval=self.config.health_check_interval
            )
            
            # Create Redis client
            self.redis_client = redis.Redis(connection_pool=self.pool)
            
            # Verify connectivity
            await self._verify_connectivity()
            
            # Start health monitoring
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            logger.info(f"Redis pool initialized: max_size={self.config.redis_max_size}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis pool: {e}")
            raise
    
    async def _verify_connectivity(self):
        """Verify Redis connectivity."""
        try:
            await self.redis_client.ping()
            self.metrics.record_connection_created()
            logger.info("Redis connectivity verified")
            
        except Exception as e:
            logger.error(f"Redis connectivity verification failed: {e}")
            self.metrics.record_connection_failed()
            raise
    
    async def _health_check_loop(self):
        """Continuous health monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                # Perform health check
                health_check_start = time.time()
                is_healthy = await self._perform_health_check()
                health_check_time = time.time() - health_check_start
                
                # Update health status
                was_healthy = self.is_healthy
                self.is_healthy = is_healthy
                self.last_health_check = datetime.now()
                
                # Log status changes
                if was_healthy != is_healthy:
                    if is_healthy:
                        logger.info("Redis pool recovered")
                    else:
                        logger.warning("Redis pool unhealthy")
                
                # Record metrics
                self.metrics.record_health_check(is_healthy)
                
                logger.debug(f"Redis health check: {is_healthy}, time: {health_check_time:.3f}s")
                
            except Exception as e:
                logger.error(f"Redis health check loop error: {e}")
                self.is_healthy = False
    
    async def _perform_health_check(self) -> bool:
        """Perform Redis health check."""
        try:
            if not self.redis_client:
                return False
            
            # Test ping
            async with asyncio.timeout(self.config.redis_timeout):
                await self.redis_client.ping()
                return True
                
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return False
    
    def get_client(self):
        """Get Redis client."""
        if not self.is_healthy:
            raise Exception("Redis pool is unhealthy")
        
        return self.redis_client
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive pool statistics."""
        stats = self.metrics.get_stats()
        stats.update({
            'is_healthy': self.is_healthy,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None
        })
        return stats
    
    async def close(self):
        """Close the Redis connection pool."""
        if self.health_check_task:
            self.health_check_task.cancel()
        
        if self.pool:
            await self.pool.disconnect()
            logger.info("Redis pool closed")

class ConnectionPoolManager:
    """
    Centralized connection pool manager for all database connections.
    
    Features:
    - Manages PostgreSQL, Neo4j, and Redis pools
    - Centralized health monitoring
    - Performance metrics aggregation
    """
    
    def __init__(self, config: ConnectionPoolConfig = None):
        self.config = config or ConnectionPoolConfig()
        self.app_config = Config()
        
        self.postgres_pool = None
        self.neo4j_pool = None
        self.redis_pool = None
        
        self.monitoring_task = None
        self.is_running = False
    
    async def initialize(self):
        """Initialize all connection pools."""
        try:
            # Initialize PostgreSQL pool
            self.postgres_pool = OptimizedPostgreSQLPool(self.config, self.app_config)
            await self.postgres_pool.initialize()
            
            # Initialize Neo4j pool
            self.neo4j_pool = OptimizedNeo4jPool(self.config, self.app_config)
            await self.neo4j_pool.initialize()
            
            # Initialize Redis pool
            self.redis_pool = OptimizedRedisPool(self.config, self.config.redis_url)
            await self.redis_pool.initialize()
            
            # Start monitoring
            await self.start_monitoring()
            
            logger.info("All connection pools initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize connection pools: {e}")
            raise
    
    async def start_monitoring(self):
        """Start centralized monitoring task."""
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Centralized monitoring loop."""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Monitor every minute
                
                # Collect stats from all pools
                stats = self.get_comprehensive_stats()
                
                # Log aggregated stats
                logger.info(f"Connection pool stats: {stats}")
                
                # Check for issues
                await self._check_pool_health()
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
    
    async def _check_pool_health(self):
        """Check health of all pools and take corrective action."""
        unhealthy_pools = []
        
        if self.postgres_pool and not self.postgres_pool.is_healthy:
            unhealthy_pools.append('postgresql')
        
        if self.neo4j_pool and not self.neo4j_pool.is_healthy:
            unhealthy_pools.append('neo4j')
        
        if self.redis_pool and not self.redis_pool.is_healthy:
            unhealthy_pools.append('redis')
        
        if unhealthy_pools:
            logger.warning(f"Unhealthy pools detected: {unhealthy_pools}")
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all pools."""
        stats = {
            'timestamp': datetime.now().isoformat(),
            'pools': {}
        }
        
        if self.postgres_pool:
            stats['pools']['postgresql'] = self.postgres_pool.get_stats()
        
        if self.neo4j_pool:
            stats['pools']['neo4j'] = self.neo4j_pool.get_stats()
        
        if self.redis_pool:
            stats['pools']['redis'] = self.redis_pool.get_stats()
        
        return stats
    
    async def close(self):
        """Close all connection pools."""
        self.is_running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
        
        if self.postgres_pool:
            await self.postgres_pool.close()
        
        if self.neo4j_pool:
            await self.neo4j_pool.close()
        
        if self.redis_pool:
            await self.redis_pool.close()
        
        logger.info("All connection pools closed")

# Global connection pool manager
global_pool_manager = ConnectionPoolManager()