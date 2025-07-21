"""
Structured Logging System for Agent-4 Operational Excellence

This module provides comprehensive structured logging with JSON formatting,
correlation tracking, and performance monitoring integration.
"""

import json
import logging
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Optional, Union

# Thread-local storage for correlation context
_correlation_context = threading.local()


class StructuredLogger:
    """
    Enhanced structured logger with JSON formatting and correlation tracking.

    Features:
    - JSON formatted log output
    - Request correlation ID tracking
    - Performance metrics integration
    - Context-aware logging
    """

    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Create JSON formatter
        formatter = StructuredFormatter()

        # Setup handler if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _get_correlation_id(self) -> str:
        """Get current correlation ID from context."""
        return getattr(_correlation_context, "correlation_id", None)

    def _build_log_entry(self, message: str, **kwargs) -> Dict[str, Any]:
        """Build structured log entry with metadata."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message": message,
            "correlation_id": self._get_correlation_id(),
            "thread_id": threading.current_thread().ident,
            "logger_name": self.logger.name,
        }

        # Add any additional context
        entry.update(kwargs)

        return entry

    def info(self, message: str, **kwargs):
        """Log info level message with structured format."""
        entry = self._build_log_entry(message, level="INFO", **kwargs)
        self.logger.info(json.dumps(entry))

    def warning(self, message: str, **kwargs):
        """Log warning level message with structured format."""
        entry = self._build_log_entry(message, level="WARNING", **kwargs)
        self.logger.warning(json.dumps(entry))

    def error(self, message: str, **kwargs):
        """Log error level message with structured format."""
        entry = self._build_log_entry(message, level="ERROR", **kwargs)
        self.logger.error(json.dumps(entry))

    def debug(self, message: str, **kwargs):
        """Log debug level message with structured format."""
        entry = self._build_log_entry(message, level="DEBUG", **kwargs)
        self.logger.debug(json.dumps(entry))

    def critical(self, message: str, **kwargs):
        """Log critical level message with structured format."""
        entry = self._build_log_entry(message, level="CRITICAL", **kwargs)
        self.logger.critical(json.dumps(entry))

    def exception(self, message: str, **kwargs):
        """Log exception with structured format and traceback."""
        entry = self._build_log_entry(message, level="ERROR", **kwargs)
        self.logger.error(json.dumps(entry), exc_info=True)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""

    def format(self, record):
        # If the message is already JSON, return as-is
        if hasattr(record, "msg") and isinstance(record.msg, str):
            try:
                json.loads(record.msg)
                return record.msg
            except (json.JSONDecodeError, ValueError):
                pass

        # Otherwise, create structured format
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "correlation_id": getattr(_correlation_context, "correlation_id", None),
        }

        return json.dumps(log_entry)


class CorrelationContextManager:
    """Manages correlation context for request tracking."""

    @staticmethod
    def set_correlation_id(correlation_id: str):
        """Set correlation ID for current thread."""
        _correlation_context.correlation_id = correlation_id

    @staticmethod
    def get_correlation_id() -> Optional[str]:
        """Get correlation ID for current thread."""
        return getattr(_correlation_context, "correlation_id", None)

    @staticmethod
    def generate_correlation_id() -> str:
        """Generate new correlation ID."""
        return str(uuid.uuid4())

    @staticmethod
    @contextmanager
    def correlation_context(correlation_id: Optional[str] = None):
        """Context manager for correlation tracking."""
        if correlation_id is None:
            correlation_id = CorrelationContextManager.generate_correlation_id()

        old_id = getattr(_correlation_context, "correlation_id", None)
        _correlation_context.correlation_id = correlation_id

        try:
            yield correlation_id
        finally:
            if old_id is not None:
                _correlation_context.correlation_id = old_id
            else:
                if hasattr(_correlation_context, "correlation_id"):
                    delattr(_correlation_context, "correlation_id")


class PerformanceLogger:
    """Logger for performance metrics and timing."""

    def __init__(self, logger_name: str = "performance"):
        self.logger = StructuredLogger(logger_name)

    @contextmanager
    def timer(self, operation: str, **context):
        """Context manager for timing operations."""
        start_time = time.time()
        correlation_id = CorrelationContextManager.get_correlation_id()

        self.logger.info(
            f"Starting operation: {operation}",
            operation=operation,
            event="operation_start",
            correlation_id=correlation_id,
            **context,
        )

        try:
            yield
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                f"Operation failed: {operation}",
                operation=operation,
                event="operation_failed",
                duration_seconds=duration,
                error=str(e),
                correlation_id=correlation_id,
                **context,
            )
            raise
        else:
            duration = time.time() - start_time
            self.logger.info(
                f"Operation completed: {operation}",
                operation=operation,
                event="operation_completed",
                duration_seconds=duration,
                correlation_id=correlation_id,
                **context,
            )

    def log_metric(self, metric_name: str, value: Union[int, float], **context):
        """Log a performance metric."""
        self.logger.info(
            f"Metric: {metric_name}",
            metric_name=metric_name,
            metric_value=value,
            event="metric",
            **context,
        )


# Global logger instances
app_logger = StructuredLogger("app")
api_logger = StructuredLogger("api")
db_logger = StructuredLogger("database")
performance_logger = PerformanceLogger()


# Convenience functions
def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)


def log_request(endpoint: str, method: str, **kwargs):
    """Log API request with structured format."""
    api_logger.info(
        f"API Request: {method} {endpoint}",
        endpoint=endpoint,
        method=method,
        event="api_request",
        **kwargs,
    )


def log_response(endpoint: str, status_code: int, duration: float, **kwargs):
    """Log API response with structured format."""
    api_logger.info(
        f"API Response: {status_code} for {endpoint}",
        endpoint=endpoint,
        status_code=status_code,
        duration_seconds=duration,
        event="api_response",
        **kwargs,
    )


def log_database_query(query: str, duration: float, **kwargs):
    """Log database query with performance metrics."""
    db_logger.info(
        "Database Query",
        query=query,
        duration_seconds=duration,
        event="database_query",
        **kwargs,
    )


# Example usage and testing
if __name__ == "__main__":
    # Test structured logging
    with CorrelationContextManager.correlation_context() as correlation_id:
        app_logger.info("Application started", version="1.0.0")

        with performance_logger.timer("database_connection"):
            time.sleep(0.1)  # Simulate database connection

        log_request("/api/users", "GET", user_id="123")
        log_response("/api/users", 200, 0.05)

        performance_logger.log_metric("active_users", 42)

        app_logger.info("Test completed successfully")
