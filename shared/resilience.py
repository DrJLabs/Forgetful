"""
Resilience Patterns for Agent-4 Operational Excellence

This module provides comprehensive resilience patterns including:
- Retry logic with exponential backoff
- Circuit breaker pattern
- Fallback mechanisms
- Recovery strategies
"""

import asyncio
import time
import random
from typing import Callable, Any, Optional, Dict, List
from enum import Enum
from dataclasses import dataclass
from functools import wraps
import threading
from contextlib import contextmanager

from .errors import StructuredError, ErrorCategory, ErrorSeverity, ErrorRecovery
from .logging_system import get_logger

logger = get_logger("resilience")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt."""
        delay = self.initial_delay * (self.backoff_multiplier ** (attempt - 1))
        delay = min(delay, self.max_delay)

        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)

        return delay


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5
    recovery_timeout: int = 60
    expected_exception: type = Exception


class CircuitBreaker:
    """
    Circuit breaker implementation for resilient service calls.

    The circuit breaker prevents cascading failures by:
    - Monitoring failure rates
    - Opening the circuit when failures exceed threshold
    - Allowing limited calls in half-open state
    - Closing the circuit when service recovers
    """

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit breaker entering HALF_OPEN state")
                else:
                    logger.warning(f"Circuit breaker OPEN - call rejected")
                    raise StructuredError(
                        message="Service temporarily unavailable",
                        error_code="CIRCUIT_BREAKER_OPEN",
                        category=ErrorCategory.EXTERNAL_SERVICE,
                        severity=ErrorSeverity.HIGH,
                        recovery_strategy=ErrorRecovery.CIRCUIT_BREAKER,
                    )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset."""
        if self.last_failure_time is None:
            return True

        return time.time() - self.last_failure_time >= self.config.recovery_timeout

    def _on_success(self):
        """Handle successful call."""
        with self.lock:
            self.failure_count = 0
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                logger.info(f"Circuit breaker CLOSED - service recovered")

    def _on_failure(self):
        """Handle failed call."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.error(f"Circuit breaker OPEN - failure threshold exceeded")


class RetryHandler:
    """
    Retry handler with exponential backoff and jitter.

    Features:
    - Configurable retry policies
    - Exponential backoff with jitter
    - Exception filtering
    - Retry metrics tracking
    """

    def __init__(self, policy: RetryPolicy):
        self.policy = policy
        self.retry_stats = {}

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        last_exception = None

        for attempt in range(1, self.policy.max_attempts + 1):
            try:
                logger.debug(f"Executing attempt {attempt}/{self.policy.max_attempts}")
                result = func(*args, **kwargs)

                if attempt > 1:
                    logger.info(f"Function succeeded after {attempt} attempts")

                return result

            except Exception as e:
                last_exception = e

                if attempt == self.policy.max_attempts:
                    logger.error(f"Function failed after {attempt} attempts")
                    break

                delay = self.policy.calculate_delay(attempt)
                logger.warning(
                    f"Attempt {attempt} failed, retrying in {delay:.2f}s: {str(e)}"
                )

                time.sleep(delay)

        # All attempts failed
        raise StructuredError(
            message=f"Operation failed after {self.policy.max_attempts} attempts",
            error_code="RETRY_EXHAUSTED",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            technical_details={
                "attempts": self.policy.max_attempts,
                "last_error": str(last_exception),
            },
            recovery_strategy=ErrorRecovery.ESCALATE,
        )


class FallbackHandler:
    """
    Fallback handler for graceful degradation.

    Provides alternative responses when primary operations fail.
    """

    def __init__(self, fallback_func: Callable):
        self.fallback_func = fallback_func

    def execute(self, primary_func: Callable, *args, **kwargs) -> Any:
        """Execute primary function with fallback."""
        try:
            return primary_func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Primary function failed, using fallback: {str(e)}")

            try:
                return self.fallback_func(*args, **kwargs)
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {str(fallback_error)}")
                raise StructuredError(
                    message="Both primary and fallback operations failed",
                    error_code="FALLBACK_FAILED",
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.CRITICAL,
                    technical_details={
                        "primary_error": str(e),
                        "fallback_error": str(fallback_error),
                    },
                    recovery_strategy=ErrorRecovery.ESCALATE,
                )


class ResilienceManager:
    """
    Comprehensive resilience manager combining multiple patterns.

    Features:
    - Retry with exponential backoff
    - Circuit breaker protection
    - Fallback mechanisms
    - Metrics and monitoring
    """

    def __init__(self):
        self.circuit_breakers = {}
        self.retry_handlers = {}
        self.fallback_handlers = {}
        self.metrics = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "circuit_breaker_trips": 0,
            "retries_executed": 0,
            "fallbacks_used": 0,
        }

    def get_circuit_breaker(
        self, name: str, config: CircuitBreakerConfig = None
    ) -> CircuitBreaker:
        """Get or create circuit breaker."""
        if name not in self.circuit_breakers:
            config = config or CircuitBreakerConfig()
            self.circuit_breakers[name] = CircuitBreaker(config)

        return self.circuit_breakers[name]

    def get_retry_handler(self, name: str, policy: RetryPolicy = None) -> RetryHandler:
        """Get or create retry handler."""
        if name not in self.retry_handlers:
            policy = policy or RetryPolicy()
            self.retry_handlers[name] = RetryHandler(policy)

        return self.retry_handlers[name]

    def get_fallback_handler(
        self, name: str, fallback_func: Callable
    ) -> FallbackHandler:
        """Get or create fallback handler."""
        if name not in self.fallback_handlers:
            self.fallback_handlers[name] = FallbackHandler(fallback_func)

        return self.fallback_handlers[name]

    def execute_with_resilience(
        self, func: Callable, resilience_config: Dict[str, Any], *args, **kwargs
    ) -> Any:
        """
        Execute function with comprehensive resilience patterns.

        Args:
            func: Function to execute
            resilience_config: Configuration for resilience patterns
            *args, **kwargs: Arguments to pass to function

        Returns:
            Result of function execution
        """
        self.metrics["total_calls"] += 1

        # Extract configuration
        retry_policy = resilience_config.get("retry_policy", RetryPolicy())
        circuit_config = resilience_config.get("circuit_config", CircuitBreakerConfig())
        fallback_func = resilience_config.get("fallback_func")
        service_name = resilience_config.get("service_name", "default")

        # Get handlers
        circuit_breaker = self.get_circuit_breaker(service_name, circuit_config)
        retry_handler = self.get_retry_handler(service_name, retry_policy)

        # Execute with patterns
        try:
            if fallback_func:
                fallback_handler = self.get_fallback_handler(
                    service_name, fallback_func
                )
                result = fallback_handler.execute(
                    lambda: circuit_breaker.call(
                        lambda: retry_handler.execute(func, *args, **kwargs)
                    )
                )
            else:
                result = circuit_breaker.call(
                    lambda: retry_handler.execute(func, *args, **kwargs)
                )

            self.metrics["successful_calls"] += 1
            return result

        except Exception as e:
            self.metrics["failed_calls"] += 1
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get resilience metrics."""
        return {
            **self.metrics,
            "success_rate": self.metrics["successful_calls"]
            / max(self.metrics["total_calls"], 1),
            "circuit_breaker_states": {
                name: cb.state.value for name, cb in self.circuit_breakers.items()
            },
        }


# Global resilience manager instance
resilience_manager = ResilienceManager()


# Decorators for easy usage
def retry(policy: RetryPolicy = None):
    """Decorator for retry functionality."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry_policy = policy or RetryPolicy()
            handler = RetryHandler(retry_policy)
            return handler.execute(func, *args, **kwargs)

        return wrapper

    return decorator


def circuit_breaker(config: CircuitBreakerConfig = None):
    """Decorator for circuit breaker functionality."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cb_config = config or CircuitBreakerConfig()
            cb = CircuitBreaker(cb_config)
            return cb.call(func, *args, **kwargs)

        return wrapper

    return decorator


def fallback(fallback_func: Callable):
    """Decorator for fallback functionality."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = FallbackHandler(fallback_func)
            return handler.execute(func, *args, **kwargs)

        return wrapper

    return decorator


def resilient(resilience_config: Dict[str, Any] = None):
    """Decorator for comprehensive resilience."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = resilience_config or {}
            return resilience_manager.execute_with_resilience(
                func, config, *args, **kwargs
            )

        return wrapper

    return decorator


# Example usage and testing
if __name__ == "__main__":
    # Test retry decorator
    @retry(RetryPolicy(max_attempts=3, initial_delay=0.1))
    def unreliable_function():
        if random.random() < 0.7:
            raise ValueError("Random failure")
        return "Success!"

    # Test circuit breaker decorator
    @circuit_breaker(CircuitBreakerConfig(failure_threshold=3))
    def service_call():
        if random.random() < 0.5:
            raise ConnectionError("Service unavailable")
        return "Service response"

    # Test fallback decorator
    def fallback_response():
        return "Fallback response"

    @fallback(fallback_response)
    def primary_service():
        raise Exception("Primary service failed")

    # Test comprehensive resilience
    @resilient(
        {
            "retry_policy": RetryPolicy(max_attempts=2),
            "circuit_config": CircuitBreakerConfig(failure_threshold=2),
            "service_name": "test_service",
        }
    )
    def resilient_function():
        if random.random() < 0.8:
            raise Exception("Function failed")
        return "Success!"

    print("Testing resilience patterns...")

    # Test retry
    try:
        result = unreliable_function()
        print(f"Retry test: {result}")
    except Exception as e:
        print(f"Retry test failed: {e}")

    # Test fallback
    try:
        result = primary_service()
        print(f"Fallback test: {result}")
    except Exception as e:
        print(f"Fallback test failed: {e}")

    # Test resilient function
    try:
        result = resilient_function()
        print(f"Resilient test: {result}")
    except Exception as e:
        print(f"Resilient test failed: {e}")

    # Print metrics
    print("Resilience metrics:", resilience_manager.get_metrics())
