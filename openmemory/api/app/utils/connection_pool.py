"""
Connection Pool Manager for MCP Server Performance Optimization

This module provides connection pooling and management for the MCP server
to optimize performance for autonomous AI agent operations.
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue
import threading
from app.utils.memory import get_memory_client

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """Connection status enumeration"""
    IDLE = "idle"
    ACTIVE = "active"
    FAILED = "failed"
    CLOSED = "closed"


@dataclass
class ConnectionInfo:
    """Connection information tracking"""
    client: Any
    status: ConnectionStatus
    created_at: float
    last_used: float
    use_count: int = 0
    error_count: int = 0


class MemoryClientPool:
    """Connection pool for memory clients with performance monitoring"""
    
    def __init__(self, 
                 max_connections: int = 10,
                 min_connections: int = 2,
                 connection_timeout: float = 30.0,
                 max_idle_time: float = 300.0,
                 health_check_interval: float = 60.0):
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.connection_timeout = connection_timeout
        self.max_idle_time = max_idle_time
        self.health_check_interval = health_check_interval
        
        self._connections: Dict[str, ConnectionInfo] = {}
        self._pool = Queue(maxsize=max_connections)
        self._lock = threading.Lock()
        self._health_check_task = None
        self._metrics = {
            'total_created': 0,
            'total_destroyed': 0,
            'current_active': 0,
            'total_requests': 0,
            'average_response_time': 0.0,
            'error_rate': 0.0
        }
        
        # Initialize minimum connections
        try:
            self._initialize_pool()
        except Exception as e:
            logger.warning(f"Failed to initialize connection pool: {e}")
            # Will be initialized later when dependencies are available
        
    def _initialize_pool(self):
        """Initialize the connection pool with minimum connections"""
        for _ in range(self.min_connections):
            try:
                client = get_memory_client()
                if client:
                    conn_id = f"conn_{time.time()}_{id(client)}"
                    conn_info = ConnectionInfo(
                        client=client,
                        status=ConnectionStatus.IDLE,
                        created_at=time.time(),
                        last_used=time.time()
                    )
                    self._connections[conn_id] = conn_info
                    self._pool.put(conn_id)
                    self._metrics['total_created'] += 1
                    logger.info(f"Created connection {conn_id}")
            except Exception as e:
                logger.error(f"Failed to create initial connection: {e}")
                
    async def get_connection(self) -> Optional[Any]:
        """Get a connection from the pool"""
        start_time = time.time()
        self._metrics['total_requests'] += 1
        
        try:
            with self._lock:
                # Try to get an existing connection
                if not self._pool.empty():
                    conn_id = self._pool.get()
                    conn_info = self._connections.get(conn_id)
                    
                    if conn_info and conn_info.status == ConnectionStatus.IDLE:
                        # Health check the connection
                        if self._is_connection_healthy(conn_info):
                            conn_info.status = ConnectionStatus.ACTIVE
                            conn_info.last_used = time.time()
                            conn_info.use_count += 1
                            self._metrics['current_active'] += 1
                            
                            response_time = time.time() - start_time
                            self._update_average_response_time(response_time)
                            
                            return conn_info.client
                        else:
                            # Connection is unhealthy, remove it
                            self._remove_connection(conn_id)
                
                # Create new connection if pool has capacity
                if len(self._connections) < self.max_connections:
                    return await self._create_connection()
                
                # Pool is full, wait for a connection to be returned
                logger.warning("Connection pool is full, waiting for available connection")
                return None
                
        except Exception as e:
            logger.error(f"Error getting connection: {e}")
            self._metrics['error_rate'] = (self._metrics['error_rate'] + 1) / self._metrics['total_requests']
            return None
    
    async def _create_connection(self) -> Optional[Any]:
        """Create a new connection"""
        try:
            client = get_memory_client()
            if client:
                conn_id = f"conn_{time.time()}_{id(client)}"
                conn_info = ConnectionInfo(
                    client=client,
                    status=ConnectionStatus.ACTIVE,
                    created_at=time.time(),
                    last_used=time.time()
                )
                self._connections[conn_id] = conn_info
                self._metrics['total_created'] += 1
                self._metrics['current_active'] += 1
                logger.info(f"Created new connection {conn_id}")
                return client
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            return None
    
    def return_connection(self, client: Any):
        """Return a connection to the pool"""
        try:
            with self._lock:
                # Find the connection by client object
                conn_id = None
                for cid, conn_info in self._connections.items():
                    if conn_info.client is client:
                        conn_id = cid
                        break
                
                if conn_id:
                    conn_info = self._connections[conn_id]
                    conn_info.status = ConnectionStatus.IDLE
                    conn_info.last_used = time.time()
                    self._metrics['current_active'] -= 1
                    
                    # Return to pool if space available
                    if not self._pool.full():
                        self._pool.put(conn_id)
                        logger.debug(f"Returned connection {conn_id} to pool")
                    else:
                        # Pool is full, close this connection
                        self._remove_connection(conn_id)
                        
        except Exception as e:
            logger.error(f"Error returning connection: {e}")
    
    def _is_connection_healthy(self, conn_info: ConnectionInfo) -> bool:
        """Check if a connection is healthy"""
        try:
            # Check if connection is too old
            if time.time() - conn_info.last_used > self.max_idle_time:
                logger.debug("Connection idle time exceeded")
                return False
            
            # Check if connection has too many errors
            if conn_info.error_count > 5:
                logger.debug("Connection error count exceeded")
                return False
            
            # Basic health check - try to access the client
            if hasattr(conn_info.client, 'get_all'):
                return True
            
            return False
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def _remove_connection(self, conn_id: str):
        """Remove a connection from the pool"""
        try:
            if conn_id in self._connections:
                conn_info = self._connections[conn_id]
                if conn_info.status == ConnectionStatus.ACTIVE:
                    self._metrics['current_active'] -= 1
                del self._connections[conn_id]
                self._metrics['total_destroyed'] += 1
                logger.info(f"Removed connection {conn_id}")
        except Exception as e:
            logger.error(f"Error removing connection: {e}")
    
    def _update_average_response_time(self, response_time: float):
        """Update average response time metric"""
        current_avg = self._metrics['average_response_time']
        total_requests = self._metrics['total_requests']
        
        # Calculate running average
        new_avg = ((current_avg * (total_requests - 1)) + response_time) / total_requests
        self._metrics['average_response_time'] = new_avg
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get connection pool metrics"""
        return {
            **self._metrics,
            'pool_size': len(self._connections),
            'idle_connections': sum(1 for conn in self._connections.values() 
                                  if conn.status == ConnectionStatus.IDLE),
            'active_connections': self._metrics['current_active'],
            'failed_connections': sum(1 for conn in self._connections.values() 
                                    if conn.status == ConnectionStatus.FAILED)
        }
    
    async def cleanup_idle_connections(self):
        """Clean up idle connections that exceed max idle time"""
        current_time = time.time()
        to_remove = []
        
        with self._lock:
            for conn_id, conn_info in self._connections.items():
                if (conn_info.status == ConnectionStatus.IDLE and 
                    current_time - conn_info.last_used > self.max_idle_time):
                    to_remove.append(conn_id)
            
            for conn_id in to_remove:
                self._remove_connection(conn_id)
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} idle connections")
    
    async def start_health_monitoring(self):
        """Start periodic health monitoring"""
        if self._health_check_task:
            return
            
        async def health_check_loop():
            while True:
                try:
                    await asyncio.sleep(self.health_check_interval)
                    await self.cleanup_idle_connections()
                except Exception as e:
                    logger.error(f"Health check error: {e}")
        
        self._health_check_task = asyncio.create_task(health_check_loop())
        logger.info("Started connection pool health monitoring")
    
    async def stop_health_monitoring(self):
        """Stop health monitoring"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("Stopped connection pool health monitoring")
    
    def close_all_connections(self):
        """Close all connections in the pool"""
        with self._lock:
            for conn_id in list(self._connections.keys()):
                self._remove_connection(conn_id)
            
            # Clear the pool queue
            while not self._pool.empty():
                self._pool.get()
        
        logger.info("Closed all connections in pool")


# Global connection pool instance
_connection_pool: Optional[MemoryClientPool] = None


def get_connection_pool() -> MemoryClientPool:
    """Get the global connection pool instance"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = MemoryClientPool()
    return _connection_pool


@asynccontextmanager
async def get_pooled_client():
    """Context manager for getting a pooled memory client"""
    pool = get_connection_pool()
    client = await pool.get_connection()
    
    if client is None:
        raise Exception("Failed to get connection from pool")
    
    try:
        yield client
    finally:
        pool.return_connection(client)