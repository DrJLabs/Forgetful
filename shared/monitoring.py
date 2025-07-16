"""
Shared monitoring utilities for mem0-stack services.
Provides metrics collection, tracing, and logging instrumentation.
"""

import functools
import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Enum,
    Gauge,
    Histogram,
    Info,
    generate_latest,
    start_http_server,
)

# OpenTelemetry imports
try:
    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.propagators.b3 import B3MultiFormat
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MetricsCollector:
    """Centralized metrics collection for mem0-stack services."""

    def __init__(self, service_name: str, registry: Optional[CollectorRegistry] = None):
        self.service_name = service_name
        self.registry = registry or CollectorRegistry()
        self._init_metrics()

    def _init_metrics(self):
        """Initialize common metrics for all services."""

        # Request metrics
        self.request_count = Counter(
            f"{self.service_name}_requests_total",
            "Total number of requests",
            ["method", "endpoint", "status_code"],
            registry=self.registry,
        )

        self.request_duration = Histogram(
            f"{self.service_name}_request_duration_seconds",
            "Request duration in seconds",
            ["method", "endpoint"],
            buckets=[
                0.005,
                0.01,
                0.025,
                0.05,
                0.075,
                0.1,
                0.25,
                0.5,
                0.75,
                1.0,
                2.5,
                5.0,
                7.5,
                10.0,
            ],
            registry=self.registry,
        )

        # Error metrics
        self.error_count = Counter(
            f"{self.service_name}_errors_total",
            "Total number of errors",
            ["error_type", "error_code"],
            registry=self.registry,
        )

        # Active connections/sessions
        self.active_connections = Gauge(
            f"{self.service_name}_active_connections",
            "Number of active connections",
            registry=self.registry,
        )

        # Memory usage
        self.memory_usage = Gauge(
            f"{self.service_name}_memory_usage_bytes",
            "Memory usage in bytes",
            registry=self.registry,
        )

        # CPU usage
        self.cpu_usage = Gauge(
            f"{self.service_name}_cpu_usage_percent",
            "CPU usage percentage",
            registry=self.registry,
        )

        # Service info
        self.service_info = Info(
            f"{self.service_name}_service_info",
            "Service information",
            registry=self.registry,
        )

        # Service health
        self.service_health = Enum(
            f"{self.service_name}_service_health",
            "Service health status",
            states=["healthy", "unhealthy", "degraded"],
            registry=self.registry,
        )

        # Set initial values
        self.service_health.state("healthy")
        self.service_info.info(
            {
                "version": os.getenv("SERVICE_VERSION", "1.0.0"),
                "environment": os.getenv("ENVIRONMENT", "development"),
                "build_time": os.getenv("BUILD_TIME", "unknown"),
            }
        )

    def track_request(
        self, method: str, endpoint: str, status_code: int, duration: float
    ):
        """Track HTTP request metrics."""
        self.request_count.labels(
            method=method, endpoint=endpoint, status_code=status_code
        ).inc()
        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)

    def track_error(self, error_type: str, error_code: str = ""):
        """Track error metrics."""
        self.error_count.labels(error_type=error_type, error_code=error_code).inc()

    def update_connection_count(self, count: int):
        """Update active connection count."""
        self.active_connections.set(count)

    def update_memory_usage(self, bytes_used: int):
        """Update memory usage."""
        self.memory_usage.set(bytes_used)

    def update_cpu_usage(self, percent: float):
        """Update CPU usage percentage."""
        self.cpu_usage.set(percent)

    def set_health_status(self, status: str):
        """Set service health status."""
        self.service_health.state(status)

    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry)


class Mem0Metrics(MetricsCollector):
    """Specific metrics for mem0 API service."""

    def _init_metrics(self):
        super()._init_metrics()

        # Memory operation metrics
        self.memory_operations = Counter(
            "mem0_memory_operations_total",
            "Total memory operations",
            ["operation", "status", "user_id"],
            registry=self.registry,
        )

        self.memory_operation_duration = Histogram(
            "mem0_memory_operation_duration_seconds",
            "Memory operation duration in seconds",
            ["operation"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry,
        )

        # Vector search metrics
        self.vector_search_count = Counter(
            "mem0_vector_search_total",
            "Total vector search operations",
            ["search_type", "status"],
            registry=self.registry,
        )

        self.vector_search_duration = Histogram(
            "mem0_vector_search_duration_seconds",
            "Vector search duration in seconds",
            ["search_type"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=self.registry,
        )

        self.vector_search_results = Histogram(
            "mem0_vector_search_results_count",
            "Number of results returned by vector search",
            ["search_type"],
            buckets=[0, 1, 5, 10, 25, 50, 100, 250, 500],
            registry=self.registry,
        )

        # Memory storage metrics
        self.memory_count = Gauge(
            "mem0_memory_count",
            "Total number of memories stored",
            ["user_id"],
            registry=self.registry,
        )

        self.memory_size = Gauge(
            "mem0_memory_size_bytes",
            "Total size of memories in bytes",
            ["user_id"],
            registry=self.registry,
        )

        # Embedding metrics
        self.embedding_operations = Counter(
            "mem0_embedding_operations_total",
            "Total embedding operations",
            ["provider", "status"],
            registry=self.registry,
        )

        self.embedding_duration = Histogram(
            "mem0_embedding_duration_seconds",
            "Embedding operation duration in seconds",
            ["provider"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
            registry=self.registry,
        )

    def track_memory_operation(
        self, operation: str, status: str, user_id: str, duration: float
    ):
        """Track memory operation metrics."""
        self.memory_operations.labels(
            operation=operation, status=status, user_id=user_id
        ).inc()
        self.memory_operation_duration.labels(operation=operation).observe(duration)

    def track_vector_search(
        self, search_type: str, status: str, duration: float, result_count: int
    ):
        """Track vector search metrics."""
        self.vector_search_count.labels(search_type=search_type, status=status).inc()
        self.vector_search_duration.labels(search_type=search_type).observe(duration)
        self.vector_search_results.labels(search_type=search_type).observe(result_count)

    def update_memory_stats(self, user_id: str, count: int, size_bytes: int):
        """Update memory statistics."""
        self.memory_count.labels(user_id=user_id).set(count)
        self.memory_size.labels(user_id=user_id).set(size_bytes)

    def track_embedding_operation(self, provider: str, status: str, duration: float):
        """Track embedding operation metrics."""
        self.embedding_operations.labels(provider=provider, status=status).inc()
        self.embedding_duration.labels(provider=provider).observe(duration)


class DatabaseMetrics(MetricsCollector):
    """Specific metrics for database operations."""

    def _init_metrics(self):
        super()._init_metrics()

        # Query metrics
        self.query_count = Counter(
            "database_queries_total",
            "Total database queries",
            ["query_type", "status", "table"],
            registry=self.registry,
        )

        self.query_duration = Histogram(
            "database_query_duration_seconds",
            "Database query duration in seconds",
            ["query_type", "table"],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0],
            registry=self.registry,
        )

        # Connection pool metrics
        self.connection_pool_size = Gauge(
            "database_connection_pool_size",
            "Database connection pool size",
            registry=self.registry,
        )

        self.connection_pool_used = Gauge(
            "database_connection_pool_used",
            "Database connection pool used connections",
            registry=self.registry,
        )

        # Transaction metrics
        self.transaction_count = Counter(
            "database_transactions_total",
            "Total database transactions",
            ["status"],
            registry=self.registry,
        )

        self.transaction_duration = Histogram(
            "database_transaction_duration_seconds",
            "Database transaction duration in seconds",
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
            registry=self.registry,
        )

    def track_query(self, query_type: str, status: str, table: str, duration: float):
        """Track database query metrics."""
        self.query_count.labels(query_type=query_type, status=status, table=table).inc()
        self.query_duration.labels(query_type=query_type, table=table).observe(duration)

    def update_connection_pool_stats(self, size: int, used: int):
        """Update connection pool statistics."""
        self.connection_pool_size.set(size)
        self.connection_pool_used.set(used)

    def track_transaction(self, status: str, duration: float):
        """Track transaction metrics."""
        self.transaction_count.labels(status=status).inc()
        self.transaction_duration.observe(duration)


class TracingManager:
    """Distributed tracing manager."""

    def __init__(
        self, service_name: str, jaeger_endpoint: str = "http://jaeger-mem0:14268"
    ):
        self.service_name = service_name
        self.jaeger_endpoint = jaeger_endpoint
        self.tracer = None

        if TRACING_AVAILABLE:
            self._setup_tracing()

    def _setup_tracing(self):
        """Setup OpenTelemetry tracing."""
        # Create resource
        resource = Resource.create(
            {
                "service.name": self.service_name,
                "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
                "deployment.environment": os.getenv("ENVIRONMENT", "development"),
            }
        )

        # Setup tracer provider
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)

        # Setup Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name="jaeger-mem0",
            agent_port=6831,
        )

        # Setup OTLP exporter (alternative)
        otlp_exporter = OTLPSpanExporter(
            endpoint="http://jaeger-mem0:4317",
            insecure=True,
        )

        # Add span processors
        tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        # Get tracer
        self.tracer = trace.get_tracer(self.service_name)

        # Setup propagators
        set_global_textmap(B3MultiFormat())

        # Auto-instrument common libraries
        FastAPIInstrumentor().instrument()
        RequestsInstrumentor().instrument()
        Psycopg2Instrumentor().instrument()
        SQLAlchemyInstrumentor().instrument()

    def get_tracer(self):
        """Get the tracer instance."""
        return self.tracer

    @contextmanager
    def trace_span(self, name: str, attributes: Dict[str, Any] = None):
        """Context manager for creating spans."""
        if not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            yield span


def setup_monitoring(service_name: str, port: int = 8080) -> tuple:
    """Setup monitoring for a service."""

    # Initialize metrics collector
    if service_name == "mem0":
        metrics = Mem0Metrics(service_name)
    else:
        metrics = MetricsCollector(service_name)

    # Initialize tracing
    tracing = TracingManager(service_name)

    # Start metrics server
    try:
        start_http_server(port, registry=metrics.registry)
        logger.info(f"Metrics server started on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")

    return metrics, tracing


def track_request_metrics(metrics: MetricsCollector):
    """Decorator to track request metrics."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            method = kwargs.get("method", "GET")
            endpoint = func.__name__
            status_code = 200

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = 500
                metrics.track_error(type(e).__name__, str(e))
                raise
            finally:
                duration = time.time() - start_time
                metrics.track_request(method, endpoint, status_code, duration)

        return wrapper

    return decorator


def track_database_metrics(metrics: DatabaseMetrics):
    """Decorator to track database metrics."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            query_type = func.__name__
            status = "success"
            table = kwargs.get("table", "unknown")

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                metrics.track_error(type(e).__name__, str(e))
                raise
            finally:
                duration = time.time() - start_time
                metrics.track_query(query_type, status, table, duration)

        return wrapper

    return decorator


# Global metrics instances
_metrics_instances = {}


def get_metrics(service_name: str) -> MetricsCollector:
    """Get or create metrics instance for a service."""
    if service_name not in _metrics_instances:
        if service_name == "mem0":
            _metrics_instances[service_name] = Mem0Metrics(service_name)
        else:
            _metrics_instances[service_name] = MetricsCollector(service_name)

    return _metrics_instances[service_name]


def get_tracing(service_name: str) -> TracingManager:
    """Get or create tracing instance for a service."""
    tracing_key = f"{service_name}_tracing"
    if tracing_key not in _metrics_instances:
        _metrics_instances[tracing_key] = TracingManager(service_name)

    return _metrics_instances[tracing_key]


# Health check utilities
def check_service_health(service_name: str) -> Dict[str, Any]:
    """Check and return service health status."""
    health_status = {
        "service": service_name,
        "status": "healthy",
        "timestamp": time.time(),
        "checks": {},
    }

    # Add specific health checks based on service
    if service_name == "mem0":
        # Check database connectivity
        try:
            # This would be implemented with actual database checks
            health_status["checks"]["database"] = "healthy"
        except Exception as e:
            health_status["checks"]["database"] = f"unhealthy: {str(e)}"
            health_status["status"] = "unhealthy"

    return health_status


# Logging utilities
def setup_structured_logging(service_name: str, log_level: str = "INFO"):
    """Setup structured logging for a service."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s - service:%(service)s - request_id:%(request_id)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f"/var/log/{service_name}.log"),
        ],
    )

    # Add service-specific logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))

    return logger


# Export main functions and classes
__all__ = [
    "MetricsCollector",
    "Mem0Metrics",
    "DatabaseMetrics",
    "TracingManager",
    "setup_monitoring",
    "track_request_metrics",
    "track_database_metrics",
    "get_metrics",
    "get_tracing",
    "check_service_health",
    "setup_structured_logging",
]
