"""
Performance Monitor for MCP Server Optimization

This module provides comprehensive performance monitoring for the MCP server,
tracking response times, throughput, and resource usage for autonomous AI operations.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import threading
from contextlib import asynccontextmanager
import functools
import json
from enum import Enum

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics to track"""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    MEMORY_USAGE = "memory_usage"
    CONNECTION_COUNT = "connection_count"
    QUEUE_LENGTH = "queue_length"


@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    name: str
    value: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationStats:
    """Statistics for a specific operation"""
    total_calls: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    error_count: int = 0
    success_count: int = 0
    recent_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    @property
    def average_time(self) -> float:
        """Calculate average response time"""
        return self.total_time / self.total_calls if self.total_calls > 0 else 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        return self.success_count / self.total_calls if self.total_calls > 0 else 0.0
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate"""
        return self.error_count / self.total_calls if self.total_calls > 0 else 0.0
    
    @property
    def recent_average(self) -> float:
        """Calculate recent average response time"""
        return sum(self.recent_times) / len(self.recent_times) if self.recent_times else 0.0


class PerformanceMonitor:
    """Comprehensive performance monitoring for MCP server"""
    
    def __init__(self, 
                 max_metrics_history: int = 1000,
                 alert_threshold_ms: float = 100.0,
                 error_rate_threshold: float = 0.05):
        self.max_metrics_history = max_metrics_history
        self.alert_threshold_ms = alert_threshold_ms
        self.error_rate_threshold = error_rate_threshold
        
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_metrics_history))
        self._operation_stats: Dict[str, OperationStats] = defaultdict(OperationStats)
        self._lock = threading.Lock()
        self._monitoring_task = None
        self._alert_handlers: List[Callable] = []
        
        # Performance thresholds
        self._thresholds = {
            'response_time_ms': 50.0,  # Target sub-50ms for autonomous operations
            'error_rate': 0.01,        # Target 1% error rate
            'throughput_ops_per_sec': 100.0,  # Target 100 ops/sec
            'memory_usage_mb': 512.0,  # Target memory usage
            'connection_pool_utilization': 0.8  # Target 80% pool utilization
        }
        
        # Start monitoring (will be started when event loop is available)
        self._monitoring_started = False
    
    def record_metric(self, metric_type: MetricType, value: float, metadata: Dict[str, Any] = None):
        """Record a performance metric"""
        metric = PerformanceMetric(
            name=metric_type.value,
            value=value,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        
        with self._lock:
            self._metrics[metric_type.value].append(metric)
        
        # Check for alerts
        self._check_threshold_alerts(metric_type, value)
    
    def record_operation_time(self, operation_name: str, duration_ms: float, success: bool = True):
        """Record operation timing and success/failure"""
        with self._lock:
            stats = self._operation_stats[operation_name]
            stats.total_calls += 1
            
            if success:
                stats.success_count += 1
                stats.total_time += duration_ms
                stats.min_time = min(stats.min_time, duration_ms)
                stats.max_time = max(stats.max_time, duration_ms)
                stats.recent_times.append(duration_ms)
            else:
                stats.error_count += 1
        
        # Record as metric
        self.record_metric(MetricType.RESPONSE_TIME, duration_ms, {
            'operation': operation_name,
            'success': success
        })
    
    def get_operation_stats(self, operation_name: str) -> Optional[OperationStats]:
        """Get statistics for a specific operation"""
        with self._lock:
            return self._operation_stats.get(operation_name)
    
    def get_all_operation_stats(self) -> Dict[str, OperationStats]:
        """Get all operation statistics"""
        with self._lock:
            return dict(self._operation_stats)
    
    def get_recent_metrics(self, metric_type: MetricType, count: int = 10) -> List[PerformanceMetric]:
        """Get recent metrics of a specific type"""
        with self._lock:
            metrics = self._metrics[metric_type.value]
            return list(metrics)[-count:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        with self._lock:
            summary = {
                'timestamp': time.time(),
                'operations': {},
                'metrics': {},
                'alerts': self._check_all_thresholds()
            }
            
            # Operation summaries
            for op_name, stats in self._operation_stats.items():
                summary['operations'][op_name] = {
                    'total_calls': stats.total_calls,
                    'average_time_ms': stats.average_time,
                    'recent_average_ms': stats.recent_average,
                    'min_time_ms': stats.min_time if stats.min_time != float('inf') else 0,
                    'max_time_ms': stats.max_time,
                    'success_rate': stats.success_rate,
                    'error_rate': stats.error_rate
                }
            
            # Metric summaries
            for metric_name, metrics in self._metrics.items():
                if metrics:
                    values = [m.value for m in metrics]
                    summary['metrics'][metric_name] = {
                        'current': values[-1] if values else 0,
                        'average': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values),
                        'count': len(values)
                    }
            
            return summary
    
    def _check_threshold_alerts(self, metric_type: MetricType, value: float):
        """Check if metric exceeds thresholds and trigger alerts"""
        alert_triggered = False
        
        if metric_type == MetricType.RESPONSE_TIME and value > self._thresholds['response_time_ms']:
            alert_triggered = True
            alert_data = {
                'type': 'response_time_threshold',
                'value': value,
                'threshold': self._thresholds['response_time_ms'],
                'message': f"Response time {value:.2f}ms exceeds threshold {self._thresholds['response_time_ms']}ms"
            }
        
        if alert_triggered:
            self._trigger_alert(alert_data)
    
    def _check_all_thresholds(self) -> List[Dict[str, Any]]:
        """Check all current metrics against thresholds"""
        alerts = []
        
        # Check operation averages
        for op_name, stats in self._operation_stats.items():
            if stats.recent_average > self._thresholds['response_time_ms']:
                alerts.append({
                    'type': 'operation_slow',
                    'operation': op_name,
                    'value': stats.recent_average,
                    'threshold': self._thresholds['response_time_ms']
                })
            
            if stats.error_rate > self._thresholds['error_rate']:
                alerts.append({
                    'type': 'high_error_rate',
                    'operation': op_name,
                    'value': stats.error_rate,
                    'threshold': self._thresholds['error_rate']
                })
        
        return alerts
    
    def _trigger_alert(self, alert_data: Dict[str, Any]):
        """Trigger alert handlers"""
        for handler in self._alert_handlers:
            try:
                handler(alert_data)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")
    
    def add_alert_handler(self, handler: Callable):
        """Add an alert handler function"""
        self._alert_handlers.append(handler)
    
    def _start_background_monitoring(self):
        """Start background monitoring task"""
        async def monitoring_loop():
            while True:
                try:
                    await asyncio.sleep(10)  # Monitor every 10 seconds
                    self._collect_system_metrics()
                except Exception as e:
                    logger.error(f"Monitoring loop error: {e}")
        
        self._monitoring_task = asyncio.create_task(monitoring_loop())
    
    def _collect_system_metrics(self):
        """Collect system-level metrics"""
        try:
            import psutil
            
            # Memory usage
            memory_info = psutil.virtual_memory()
            self.record_metric(MetricType.MEMORY_USAGE, memory_info.percent)
            
            # CPU usage would be here if needed
            # cpu_percent = psutil.cpu_percent()
            # self.record_metric(MetricType.CPU_USAGE, cpu_percent)
            
        except ImportError:
            # psutil not available, skip system metrics
            pass
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    async def stop_monitoring(self):
        """Stop background monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
    
    def get_json_summary(self) -> str:
        """Get performance summary as JSON string"""
        try:
            summary = self.get_performance_summary()
            # Convert any non-serializable objects
            return json.dumps(summary, default=str, indent=2)
        except Exception as e:
            logger.error(f"Error generating JSON summary: {e}")
            return "{}"


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def timed_operation(operation_name: str):
    """Decorator to automatically time operations"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                monitor = get_performance_monitor()
                monitor.record_operation_time(operation_name, duration_ms, success)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                monitor = get_performance_monitor()
                monitor.record_operation_time(operation_name, duration_ms, success)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


@asynccontextmanager
async def performance_context(operation_name: str):
    """Context manager for timing operations"""
    start_time = time.time()
    success = True
    try:
        yield
    except Exception as e:
        success = False
        raise
    finally:
        duration_ms = (time.time() - start_time) * 1000
        monitor = get_performance_monitor()
        monitor.record_operation_time(operation_name, duration_ms, success)