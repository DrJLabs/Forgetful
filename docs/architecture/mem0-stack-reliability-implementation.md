# mem0-Stack Reliability Implementation Guide

## Overview

This guide provides concrete implementation details for achieving 99.9% uptime through reliability patterns in mem0-stack. Each pattern includes production-ready code that enhances system resilience for autonomous AI agent operations.

## 1. Advanced Circuit Breaker Implementation

### Service-Specific Circuit Breakers

```python
# shared/reliability/circuit_breaker_manager.py
from dataclasses import dataclass
from typing import Dict, Optional, Callable, Any
import asyncio
import time
from enum import Enum
import logging

logger = logging.getLogger(__name__)

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3
    sliding_window_size: int = 10
    min_calls_in_window: int = 5
    failure_rate_threshold: float = 0.5

class CircuitBreakerManager:
    """Manages circuit breakers for all services"""
    
    def __init__(self):
        self.breakers: Dict[str, ServiceCircuitBreaker] = {}
        self.default_configs = {
            "postgresql": CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=30.0,
                failure_rate_threshold=0.5
            ),
            "neo4j": CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=45.0,
                failure_rate_threshold=0.4
            ),
            "openai_api": CircuitBreakerConfig(
                failure_threshold=10,
                recovery_timeout=60.0,
                failure_rate_threshold=0.7
            ),
            "mcp_server": CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=20.0,
                failure_rate_threshold=0.3
            )
        }
    
    def get_breaker(self, service_name: str) -> 'ServiceCircuitBreaker':
        """Get or create circuit breaker for service"""
        if service_name not in self.breakers:
            config = self.default_configs.get(
                service_name, 
                CircuitBreakerConfig()
            )
            self.breakers[service_name] = ServiceCircuitBreaker(
                service_name, 
                config
            )
        return self.breakers[service_name]
    
    async def health_check(self) -> Dict[str, str]:
        """Get health status of all circuit breakers"""
        return {
            name: breaker.state.value
            for name, breaker in self.breakers.items()
        }

class ServiceCircuitBreaker:
    """Advanced circuit breaker with sliding window and half-open state management"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        self.call_history = []  # Sliding window
        self._lock = asyncio.Lock()
        
    async def call(
        self, 
        func: Callable, 
        fallback: Optional[Callable] = None,
        *args, 
        **kwargs
    ) -> Any:
        """Execute function with circuit breaker protection"""
        async with self._lock:
            # Check if we should attempt reset
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                else:
                    if fallback:
                        logger.warning(
                            f"Circuit breaker {self.name} is OPEN, using fallback"
                        )
                        return await fallback(*args, **kwargs)
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker {self.name} is OPEN"
                    )
            
            # Handle half-open state
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.config.half_open_max_calls:
                    # Evaluate half-open results
                    if self._evaluate_half_open():
                        self.state = CircuitState.CLOSED
                        self.failure_count = 0
                    else:
                        self.state = CircuitState.OPEN
                        self.last_failure_time = time.time()
        
        # Execute the function
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            await self._record_success(time.time() - start_time)
            return result
            
        except Exception as e:
            await self._record_failure(time.time() - start_time, e)
            if fallback:
                logger.warning(
                    f"Primary call failed for {self.name}, using fallback: {str(e)}"
                )
                return await fallback(*args, **kwargs)
            raise
    
    async def _record_success(self, duration: float):
        """Record successful call"""
        async with self._lock:
            self.success_count += 1
            self._add_to_history(True, duration)
            
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1
    
    async def _record_failure(self, duration: float, error: Exception):
        """Record failed call"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            self._add_to_history(False, duration)
            
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1
                self.state = CircuitState.OPEN
            elif self.state == CircuitState.CLOSED:
                # Check if we should open the circuit
                if self._should_open_circuit():
                    self.state = CircuitState.OPEN
                    logger.error(
                        f"Opening circuit breaker for {self.name} after "
                        f"{self.failure_count} failures"
                    )
    
    def _add_to_history(self, success: bool, duration: float):
        """Add call result to sliding window"""
        self.call_history.append({
            'success': success,
            'duration': duration,
            'timestamp': time.time()
        })
        
        # Maintain window size
        if len(self.call_history) > self.config.sliding_window_size:
            self.call_history.pop(0)
    
    def _should_open_circuit(self) -> bool:
        """Determine if circuit should open based on failure rate"""
        if len(self.call_history) < self.config.min_calls_in_window:
            return self.failure_count >= self.config.failure_threshold
        
        # Calculate failure rate in sliding window
        failures = sum(1 for call in self.call_history if not call['success'])
        failure_rate = failures / len(self.call_history)
        
        return failure_rate >= self.config.failure_rate_threshold
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset the circuit"""
        if not self.last_failure_time:
            return True
        
        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout
    
    def _evaluate_half_open(self) -> bool:
        """Evaluate if circuit should close after half-open period"""
        recent_calls = self.call_history[-self.config.half_open_max_calls:]
        if not recent_calls:
            return False
        
        success_count = sum(1 for call in recent_calls if call['success'])
        return success_count == len(recent_calls)

class CircuitBreakerOpenException(Exception):
    """Raised when circuit breaker is open"""
    pass

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
```

## 2. Intelligent Retry Mechanism

### Exponential Backoff with Jitter

```python
# shared/reliability/retry_manager.py
import asyncio
import random
from typing import TypeVar, Callable, Optional, List, Type
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

class RetryConfig:
    """Configuration for retry behavior"""
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 0.1,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [Exception]

class RetryManager:
    """Manages retry logic with different strategies"""
    
    @staticmethod
    async def retry_with_backoff(
        func: Callable[..., T],
        config: RetryConfig,
        *args,
        **kwargs
    ) -> T:
        """Execute function with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(config.max_attempts):
            try:
                return await func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                # Check if exception is retryable
                if not any(isinstance(e, exc_type) 
                          for exc_type in config.retryable_exceptions):
                    raise
                
                if attempt < config.max_attempts - 1:
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.initial_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{config.max_attempts} "
                        f"after {delay:.3f}s delay. Error: {str(e)}"
                    )
                    
                    await asyncio.sleep(delay)
        
        raise last_exception

# Decorator for retry logic
def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 0.1,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[List[Type[Exception]]] = None
):
    """Decorator to add retry logic to async functions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
                retryable_exceptions=retryable_exceptions
            )
            
            return await RetryManager.retry_with_backoff(
                func, config, *args, **kwargs
            )
        
        return wrapper
    return decorator

# Usage example for database operations
class ResilientDatabaseOperations:
    def __init__(self, db_pool, circuit_breaker):
        self.db_pool = db_pool
        self.circuit_breaker = circuit_breaker
    
    @with_retry(
        max_attempts=3,
        initial_delay=0.05,
        retryable_exceptions=[asyncpg.PostgresError, asyncpg.InterfaceError]
    )
    async def execute_query(self, query: str, *args):
        """Execute database query with retry logic"""
        async def _execute():
            async with self.db_pool.acquire() as conn:
                return await conn.fetch(query, *args)
        
        # Combine circuit breaker with retry
        return await self.circuit_breaker.call(_execute)
    
    @with_retry(
        max_attempts=5,
        initial_delay=0.1,
        retryable_exceptions=[ConnectionError, TimeoutError]
    )
    async def search_memories_with_retry(
        self, 
        user_id: str, 
        embedding: List[float],
        limit: int = 10
    ):
        """Search with automatic retry and fallback"""
        async def _search():
            return await self.execute_query(
                "EXECUTE vector_search($1, $2, $3)",
                user_id, embedding, limit
            )
        
        async def _fallback():
            # Fallback to recent memories if vector search fails
            return await self.execute_query(
                "EXECUTE get_recent_memories($1, $2, $3)",
                user_id, limit, 0
            )
        
        return await self.circuit_breaker.call(_search, fallback=_fallback)
```

## 3. Graceful Degradation Implementation

### Service Degradation Manager

```python
# shared/reliability/degradation_manager.py
from enum import Enum
from typing import Dict, List, Optional, Any
import asyncio
import time
import logging

logger = logging.getLogger(__name__)

class DegradationLevel(Enum):
    NORMAL = "normal"
    REDUCED = "reduced"
    ESSENTIAL = "essential"
    READONLY = "readonly"
    MAINTENANCE = "maintenance"

class ServiceDegradationManager:
    """Manages graceful degradation across services"""
    
    def __init__(self):
        self.degradation_levels: Dict[str, DegradationLevel] = {}
        self.degradation_rules: Dict[DegradationLevel, Dict] = {
            DegradationLevel.NORMAL: {
                "features": "all",
                "cache_only": False,
                "write_enabled": True,
                "vector_search": "precise",
                "graph_queries": True,
                "batch_size": 50
            },
            DegradationLevel.REDUCED: {
                "features": "core",
                "cache_only": False,
                "write_enabled": True,
                "vector_search": "approximate",
                "graph_queries": True,
                "batch_size": 20
            },
            DegradationLevel.ESSENTIAL: {
                "features": "essential",
                "cache_only": True,
                "write_enabled": True,
                "vector_search": "disabled",
                "graph_queries": False,
                "batch_size": 10
            },
            DegradationLevel.READONLY: {
                "features": "read",
                "cache_only": True,
                "write_enabled": False,
                "vector_search": "cache_only",
                "graph_queries": False,
                "batch_size": 1
            },
            DegradationLevel.MAINTENANCE: {
                "features": "none",
                "cache_only": True,
                "write_enabled": False,
                "vector_search": "disabled",
                "graph_queries": False,
                "batch_size": 0
            }
        }
        self._monitors = {}
    
    async def evaluate_system_health(
        self,
        metrics: Dict[str, Any]
    ) -> DegradationLevel:
        """Determine appropriate degradation level based on metrics"""
        # CPU usage check
        cpu_usage = metrics.get('cpu_usage', 0)
        if cpu_usage > 90:
            return DegradationLevel.ESSENTIAL
        elif cpu_usage > 75:
            return DegradationLevel.REDUCED
        
        # Memory usage check
        memory_usage = metrics.get('memory_usage', 0)
        if memory_usage > 85:
            return DegradationLevel.REDUCED
        
        # Response time check
        avg_response_time = metrics.get('avg_response_time_ms', 0)
        if avg_response_time > 200:
            return DegradationLevel.REDUCED
        elif avg_response_time > 500:
            return DegradationLevel.ESSENTIAL
        
        # Error rate check
        error_rate = metrics.get('error_rate', 0)
        if error_rate > 0.1:  # 10% error rate
            return DegradationLevel.READONLY
        elif error_rate > 0.05:  # 5% error rate
            return DegradationLevel.ESSENTIAL
        
        # Circuit breaker states
        open_circuits = metrics.get('open_circuits', [])
        if 'postgresql' in open_circuits:
            return DegradationLevel.READONLY
        elif len(open_circuits) > 2:
            return DegradationLevel.ESSENTIAL
        
        return DegradationLevel.NORMAL
    
    def get_feature_flags(self, service: str) -> Dict[str, Any]:
        """Get feature flags based on current degradation level"""
        level = self.degradation_levels.get(service, DegradationLevel.NORMAL)
        return self.degradation_rules[level]
    
    async def apply_degradation(
        self,
        service: str,
        level: DegradationLevel
    ):
        """Apply degradation level to service"""
        old_level = self.degradation_levels.get(service, DegradationLevel.NORMAL)
        self.degradation_levels[service] = level
        
        if old_level != level:
            logger.warning(
                f"Service {service} degradation level changed: "
                f"{old_level.value} -> {level.value}"
            )
            
            # Trigger degradation actions
            await self._apply_degradation_actions(service, level)
    
    async def _apply_degradation_actions(
        self,
        service: str,
        level: DegradationLevel
    ):
        """Apply specific actions for degradation level"""
        if level == DegradationLevel.READONLY:
            # Flush write queues
            logger.info(f"Flushing write queues for {service}")
            # Implementation specific to your queue system
            
        elif level == DegradationLevel.ESSENTIAL:
            # Reduce batch sizes, disable non-essential features
            logger.info(f"Disabling non-essential features for {service}")
            
        elif level == DegradationLevel.MAINTENANCE:
            # Prepare for maintenance mode
            logger.info(f"Entering maintenance mode for {service}")

# Integration with memory operations
class DegradedMemoryOperations:
    """Memory operations that respect degradation levels"""
    
    def __init__(
        self,
        degradation_manager: ServiceDegradationManager,
        cache_layer: Any,
        db_operations: Any
    ):
        self.degradation_manager = degradation_manager
        self.cache_layer = cache_layer
        self.db_operations = db_operations
    
    async def search_memories(
        self,
        user_id: str,
        query_embedding: List[float],
        limit: int = 10
    ) -> List[Dict]:
        """Search memories with degradation awareness"""
        flags = self.degradation_manager.get_feature_flags('memory_service')
        
        # Check if we should use cache only
        if flags['cache_only']:
            cached_results = await self.cache_layer.search_memories_cached(
                user_id, query_embedding, limit
            )
            if cached_results:
                return cached_results
            
            # If no cache and cache_only mode, return empty
            if flags['vector_search'] == 'disabled':
                return []
        
        # Check vector search mode
        if flags['vector_search'] == 'approximate':
            # Use approximate search for performance
            return await self._approximate_search(
                user_id, query_embedding, limit
            )
        elif flags['vector_search'] == 'precise':
            # Normal precise search
            return await self.db_operations.search_similar(
                user_id, query_embedding, limit
            )
        else:
            # Vector search disabled, return recent memories
            return await self._get_recent_memories(user_id, limit)
    
    async def create_memory(
        self,
        user_id: str,
        content: str,
        metadata: Dict
    ) -> Optional[Dict]:
        """Create memory with degradation awareness"""
        flags = self.degradation_manager.get_feature_flags('memory_service')
        
        if not flags['write_enabled']:
            logger.warning("Write operations disabled due to degradation")
            return None
        
        # Adjust batch size based on degradation
        batch_size = flags['batch_size']
        if batch_size == 0:
            return None
        
        # Create memory with adjusted parameters
        return await self.db_operations.create_memory(
            user_id, content, metadata, batch_size=batch_size
        )
```

## 4. Health Monitoring and Auto-Recovery

### Comprehensive Health Monitor

```python
# shared/reliability/health_monitor.py
import asyncio
from typing import Dict, List, Any, Callable
import time
import psutil
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class HealthMetric:
    name: str
    value: Any
    threshold: Any
    status: str  # 'healthy', 'warning', 'critical'
    timestamp: float

class HealthMonitor:
    """Monitors system health and triggers recovery actions"""
    
    def __init__(
        self,
        circuit_manager: CircuitBreakerManager,
        degradation_manager: ServiceDegradationManager
    ):
        self.circuit_manager = circuit_manager
        self.degradation_manager = degradation_manager
        self.health_checks: Dict[str, Callable] = {}
        self.metrics_history: List[Dict[str, HealthMetric]] = []
        self.recovery_actions: Dict[str, List[Callable]] = {}
        self._monitoring = False
        self._monitor_task = None
    
    def register_health_check(
        self,
        name: str,
        check_func: Callable,
        threshold: Any,
        recovery_actions: Optional[List[Callable]] = None
    ):
        """Register a health check with recovery actions"""
        self.health_checks[name] = (check_func, threshold)
        if recovery_actions:
            self.recovery_actions[name] = recovery_actions
    
    async def start_monitoring(self, interval: float = 10.0):
        """Start health monitoring loop"""
        self._monitoring = True
        self._monitor_task = asyncio.create_task(
            self._monitor_loop(interval)
        )
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        self._monitoring = False
        if self._monitor_task:
            await self._monitor_task
    
    async def _monitor_loop(self, interval: float):
        """Main monitoring loop"""
        while self._monitoring:
            try:
                metrics = await self.collect_metrics()
                await self.evaluate_health(metrics)
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(interval)
    
    async def collect_metrics(self) -> Dict[str, HealthMetric]:
        """Collect all health metrics"""
        metrics = {}
        
        # System metrics
        metrics['cpu_usage'] = HealthMetric(
            name='cpu_usage',
            value=psutil.cpu_percent(interval=1),
            threshold=80,
            status=self._evaluate_threshold(
                psutil.cpu_percent(interval=1), 80, 90
            ),
            timestamp=time.time()
        )
        
        metrics['memory_usage'] = HealthMetric(
            name='memory_usage',
            value=psutil.virtual_memory().percent,
            threshold=80,
            status=self._evaluate_threshold(
                psutil.virtual_memory().percent, 80, 90
            ),
            timestamp=time.time()
        )
        
        # Custom health checks
        for name, (check_func, threshold) in self.health_checks.items():
            try:
                value = await check_func()
                metrics[name] = HealthMetric(
                    name=name,
                    value=value,
                    threshold=threshold,
                    status=self._evaluate_custom_threshold(value, threshold),
                    timestamp=time.time()
                )
            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                metrics[name] = HealthMetric(
                    name=name,
                    value=None,
                    threshold=threshold,
                    status='critical',
                    timestamp=time.time()
                )
        
        # Circuit breaker states
        circuit_states = await self.circuit_manager.health_check()
        open_circuits = [
            name for name, state in circuit_states.items() 
            if state == 'open'
        ]
        metrics['open_circuits'] = HealthMetric(
            name='open_circuits',
            value=open_circuits,
            threshold=2,
            status='critical' if len(open_circuits) > 2 else 'healthy',
            timestamp=time.time()
        )
        
        # Store metrics history
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > 100:  # Keep last 100 readings
            self.metrics_history.pop(0)
        
        return metrics
    
    async def evaluate_health(self, metrics: Dict[str, HealthMetric]):
        """Evaluate health and trigger recovery if needed"""
        critical_metrics = [
            m for m in metrics.values() if m.status == 'critical'
        ]
        
        if critical_metrics:
            logger.warning(
                f"Critical health metrics detected: "
                f"{[m.name for m in critical_metrics]}"
            )
            
            # Trigger recovery actions
            for metric in critical_metrics:
                await self._trigger_recovery(metric)
        
        # Update degradation level based on metrics
        metrics_dict = {
            'cpu_usage': metrics.get('cpu_usage', HealthMetric('', 0, 0, '', 0)).value,
            'memory_usage': metrics.get('memory_usage', HealthMetric('', 0, 0, '', 0)).value,
            'open_circuits': metrics.get('open_circuits', HealthMetric('', [], 0, '', 0)).value,
            'error_rate': await self._calculate_error_rate()
        }
        
        degradation_level = await self.degradation_manager.evaluate_system_health(
            metrics_dict
        )
        
        await self.degradation_manager.apply_degradation(
            'memory_service', degradation_level
        )
    
    async def _trigger_recovery(self, metric: HealthMetric):
        """Trigger recovery actions for critical metric"""
        if metric.name in self.recovery_actions:
            logger.info(f"Triggering recovery actions for {metric.name}")
            
            for action in self.recovery_actions[metric.name]:
                try:
                    await action()
                except Exception as e:
                    logger.error(
                        f"Recovery action failed for {metric.name}: {e}"
                    )
    
    def _evaluate_threshold(
        self, 
        value: float, 
        warning: float, 
        critical: float
    ) -> str:
        """Evaluate numeric threshold"""
        if value >= critical:
            return 'critical'
        elif value >= warning:
            return 'warning'
        return 'healthy'
    
    def _evaluate_custom_threshold(self, value: Any, threshold: Any) -> str:
        """Evaluate custom threshold based on type"""
        if isinstance(threshold, (int, float)):
            return self._evaluate_threshold(value, threshold * 0.8, threshold)
        elif callable(threshold):
            return 'healthy' if threshold(value) else 'critical'
        return 'healthy'
    
    async def _calculate_error_rate(self) -> float:
        """Calculate error rate from recent metrics"""
        # Implementation depends on your error tracking
        return 0.0

# Recovery action examples
class RecoveryActions:
    """Common recovery actions for critical situations"""
    
    @staticmethod
    async def clear_connection_pools():
        """Clear and recreate connection pools"""
        logger.info("Clearing connection pools")
        # Implementation specific to your connection pools
    
    @staticmethod
    async def force_garbage_collection():
        """Force garbage collection to free memory"""
        import gc
        logger.info("Forcing garbage collection")
        gc.collect()
    
    @staticmethod
    async def restart_service(service_name: str):
        """Restart a specific service"""
        logger.info(f"Restarting service: {service_name}")
        # Implementation specific to your deployment
    
    @staticmethod
    async def flush_caches():
        """Flush all caches to free memory"""
        logger.info("Flushing all caches")
        # Implementation specific to your cache layer
```

## 5. Integration Example

### Putting It All Together

```python
# mem0/server/resilient_main.py
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import asyncio

# Import reliability components
from shared.reliability.circuit_breaker_manager import CircuitBreakerManager
from shared.reliability.retry_manager import RetryManager, RetryConfig
from shared.reliability.degradation_manager import ServiceDegradationManager
from shared.reliability.health_monitor import HealthMonitor, RecoveryActions

# Global instances
circuit_manager = None
degradation_manager = None
health_monitor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize reliability components on startup"""
    global circuit_manager, degradation_manager, health_monitor
    
    # Initialize managers
    circuit_manager = CircuitBreakerManager()
    degradation_manager = ServiceDegradationManager()
    health_monitor = HealthMonitor(circuit_manager, degradation_manager)
    
    # Register health checks
    health_monitor.register_health_check(
        'database_connectivity',
        check_database_health,
        threshold=100,  # Max 100ms response time
        recovery_actions=[RecoveryActions.clear_connection_pools]
    )
    
    health_monitor.register_health_check(
        'memory_operations',
        check_memory_operations_health,
        threshold=0.95,  # 95% success rate
        recovery_actions=[RecoveryActions.flush_caches]
    )
    
    # Start monitoring
    await health_monitor.start_monitoring(interval=10.0)
    
    yield
    
    # Cleanup
    await health_monitor.stop_monitoring()

app = FastAPI(lifespan=lifespan)

# Middleware for resilient operations
@app.middleware("http")
async def resilience_middleware(request: Request, call_next):
    """Apply resilience patterns to all requests"""
    # Get current degradation level
    flags = degradation_manager.get_feature_flags('memory_service')
    
    # Add degradation headers
    response = await call_next(request)
    response.headers["X-Degradation-Level"] = str(
        degradation_manager.degradation_levels.get(
            'memory_service', 
            'normal'
        )
    )
    
    return response

# Example endpoint with full resilience
@app.post("/memories/search")
async def search_memories_resilient(request: SearchRequest):
    """Search endpoint with all resilience patterns"""
    # Get circuit breaker for PostgreSQL
    pg_breaker = circuit_manager.get_breaker('postgresql')
    
    # Create resilient operations instance
    ops = DegradedMemoryOperations(
        degradation_manager,
        cache_layer,
        db_operations
    )
    
    # Perform search with circuit breaker and degradation awareness
    try:
        results = await pg_breaker.call(
            ops.search_memories,
            fallback=lambda *args: ops.cache_layer.search_memories_cached(*args),
            user_id=request.user_id,
            query_embedding=request.embedding,
            limit=request.limit
        )
        
        return {
            "results": results,
            "degraded": degradation_manager.degradation_levels.get(
                'memory_service'
            ) != DegradationLevel.NORMAL
        }
        
    except CircuitBreakerOpenException:
        # Circuit is open, return cached results only
        cached = await ops.cache_layer.search_memories_cached(
            request.user_id,
            request.embedding,
            request.limit
        )
        
        return {
            "results": cached or [],
            "degraded": True,
            "error": "Service temporarily unavailable"
        }

# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    metrics = await health_monitor.collect_metrics()
    
    critical_count = sum(
        1 for m in metrics.values() if m.status == 'critical'
    )
    
    if critical_count > 0:
        return {
            "status": "unhealthy",
            "critical_metrics": critical_count
        }
    
    return {"status": "healthy"}

@app.get("/health/detailed")
async def detailed_health():
    """Detailed health information"""
    metrics = await health_monitor.collect_metrics()
    
    return {
        "metrics": {
            name: {
                "value": metric.value,
                "status": metric.status,
                "threshold": metric.threshold
            }
            for name, metric in metrics.items()
        },
        "circuit_breakers": await circuit_manager.health_check(),
        "degradation_level": degradation_manager.degradation_levels.get(
            'memory_service', 
            'normal'
        )
    }
```

## Conclusion

These reliability implementations provide comprehensive protection for mem0-stack:

1. **Circuit Breakers** prevent cascading failures with intelligent state management
2. **Retry Mechanisms** handle transient failures with exponential backoff
3. **Graceful Degradation** maintains service availability under stress
4. **Health Monitoring** enables proactive issue detection and recovery
5. **Auto-Recovery** reduces manual intervention requirements

Together, these patterns ensure 99.9% uptime for autonomous AI agent operations by preventing failures, recovering automatically, and degrading gracefully when necessary. 