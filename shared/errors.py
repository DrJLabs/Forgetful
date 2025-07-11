"""
Advanced Error Classification System for Agent-4 Operational Excellence

This module provides comprehensive error classification, categorization,
and structured error handling for production systems.
"""

import traceback
from enum import Enum
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
import json


class ErrorSeverity(Enum):
    """Error severity levels for classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""

    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    RATE_LIMIT = "rate_limit"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    NETWORK = "network"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ErrorRecovery(Enum):
    """Error recovery strategies."""

    RETRY = "retry"
    CIRCUIT_BREAKER = "circuit_breaker"
    FALLBACK = "fallback"
    IGNORE = "ignore"
    ESCALATE = "escalate"


class StructuredError(Exception):
    """
    Enhanced exception class with structured error information.

    Features:
    - Error classification and categorization
    - User-friendly messages
    - Technical details for debugging
    - Recovery strategy recommendations
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_message: Optional[str] = None,
        technical_details: Optional[Dict[str, Any]] = None,
        recovery_strategy: Optional[ErrorRecovery] = None,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.category = category
        self.severity = severity
        self.user_message = user_message or self._generate_user_message()
        self.technical_details = technical_details or {}
        self.recovery_strategy = recovery_strategy
        self.correlation_id = correlation_id
        self.context = context or {}
        self.timestamp = datetime.utcnow()
        self.traceback = traceback.format_exc()

    def _generate_user_message(self) -> str:
        """Generate user-friendly error message based on category."""
        user_messages = {
            ErrorCategory.VALIDATION: "The provided data is invalid. Please check your input and try again.",
            ErrorCategory.AUTHENTICATION: "Authentication failed. Please verify your credentials.",
            ErrorCategory.AUTHORIZATION: "You don't have permission to perform this action.",
            ErrorCategory.NOT_FOUND: "The requested resource was not found.",
            ErrorCategory.CONFLICT: "A conflict occurred with existing data. Please resolve and try again.",
            ErrorCategory.RATE_LIMIT: "Too many requests. Please wait before trying again.",
            ErrorCategory.EXTERNAL_SERVICE: "An external service is temporarily unavailable. Please try again later.",
            ErrorCategory.DATABASE: "A database error occurred. Please try again.",
            ErrorCategory.NETWORK: "A network error occurred. Please check your connection and try again.",
            ErrorCategory.SYSTEM: "A system error occurred. Please contact support if the issue persists.",
            ErrorCategory.UNKNOWN: "An unexpected error occurred. Please try again or contact support.",
        }
        return user_messages.get(self.category, "An error occurred. Please try again.")

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "recovery_strategy": (
                self.recovery_strategy.value if self.recovery_strategy else None
            ),
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "technical_details": self.technical_details,
            "context": self.context,
            "traceback": self.traceback,
        }

    def to_json(self) -> str:
        """Convert error to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


# Specific error classes for different scenarios
class ValidationError(StructuredError):
    """Validation error with structured information."""

    def __init__(self, message: str, field: str = None, value: Any = None, **kwargs):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            technical_details={"field": field, "value": value},
            recovery_strategy=ErrorRecovery.IGNORE,
            **kwargs,
        )


class AuthenticationError(StructuredError):
    """Authentication error with structured information."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            recovery_strategy=ErrorRecovery.ESCALATE,
            **kwargs,
        )


class AuthorizationError(StructuredError):
    """Authorization error with structured information."""

    def __init__(self, message: str = "Access denied", resource: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.HIGH,
            technical_details={"resource": resource},
            recovery_strategy=ErrorRecovery.ESCALATE,
            **kwargs,
        )


class NotFoundError(StructuredError):
    """Not found error with structured information."""

    def __init__(
        self, message: str, resource_type: str = None, resource_id: str = None, **kwargs
    ):
        super().__init__(
            message=message,
            error_code="NOT_FOUND_ERROR",
            category=ErrorCategory.NOT_FOUND,
            severity=ErrorSeverity.MEDIUM,
            technical_details={
                "resource_type": resource_type,
                "resource_id": resource_id,
            },
            recovery_strategy=ErrorRecovery.IGNORE,
            **kwargs,
        )


class ConflictError(StructuredError):
    """Conflict error with structured information."""

    def __init__(self, message: str, resource: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="CONFLICT_ERROR",
            category=ErrorCategory.CONFLICT,
            severity=ErrorSeverity.MEDIUM,
            technical_details={"resource": resource},
            recovery_strategy=ErrorRecovery.IGNORE,
            **kwargs,
        )


class RateLimitError(StructuredError):
    """Rate limit error with structured information."""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: int = None, **kwargs
    ):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            technical_details={"retry_after": retry_after},
            recovery_strategy=ErrorRecovery.RETRY,
            **kwargs,
        )


class ExternalServiceError(StructuredError):
    """External service error with structured information."""

    def __init__(self, message: str, service_name: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.HIGH,
            technical_details={"service_name": service_name},
            recovery_strategy=ErrorRecovery.CIRCUIT_BREAKER,
            **kwargs,
        )


class DatabaseError(StructuredError):
    """Database error with structured information."""

    def __init__(self, message: str, query: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            technical_details={"query": query},
            recovery_strategy=ErrorRecovery.RETRY,
            **kwargs,
        )


class NetworkError(StructuredError):
    """Network error with structured information."""

    def __init__(self, message: str, endpoint: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="NETWORK_ERROR",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH,
            technical_details={"endpoint": endpoint},
            recovery_strategy=ErrorRecovery.RETRY,
            **kwargs,
        )


class SystemError(StructuredError):
    """System error with structured information."""

    def __init__(self, message: str, component: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="SYSTEM_ERROR",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            technical_details={"component": component},
            recovery_strategy=ErrorRecovery.ESCALATE,
            **kwargs,
        )


class ErrorClassifier:
    """
    Utility class for classifying and analyzing errors.
    """

    @staticmethod
    def classify_exception(exception: Exception) -> StructuredError:
        """
        Classify a generic exception into a structured error.

        Args:
            exception: The exception to classify

        Returns:
            StructuredError: Classified structured error
        """
        error_message = str(exception)

        # Classification rules based on exception type and message
        if isinstance(exception, ValueError):
            return ValidationError(error_message)
        elif isinstance(exception, KeyError):
            return NotFoundError(error_message)
        elif isinstance(exception, ConnectionError):
            return NetworkError(error_message)
        elif "authentication" in error_message.lower():
            return AuthenticationError(error_message)
        elif (
            "authorization" in error_message.lower()
            or "permission" in error_message.lower()
        ):
            return AuthorizationError(error_message)
        elif "not found" in error_message.lower():
            return NotFoundError(error_message)
        elif "conflict" in error_message.lower():
            return ConflictError(error_message)
        elif "rate limit" in error_message.lower():
            return RateLimitError(error_message)
        elif "database" in error_message.lower() or "sql" in error_message.lower():
            return DatabaseError(error_message)
        elif (
            "network" in error_message.lower() or "connection" in error_message.lower()
        ):
            return NetworkError(error_message)
        else:
            return StructuredError(
                message=error_message,
                error_code="UNKNOWN_ERROR",
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.MEDIUM,
            )

    @staticmethod
    def analyze_error_patterns(errors: List[StructuredError]) -> Dict[str, Any]:
        """
        Analyze patterns in error data.

        Args:
            errors: List of structured errors

        Returns:
            Dict containing error analysis
        """
        if not errors:
            return {"total_errors": 0}

        analysis = {
            "total_errors": len(errors),
            "by_category": {},
            "by_severity": {},
            "by_recovery_strategy": {},
            "most_common_errors": {},
            "error_rate_by_hour": {},
        }

        # Analyze by category
        for error in errors:
            category = error.category.value
            analysis["by_category"][category] = (
                analysis["by_category"].get(category, 0) + 1
            )

        # Analyze by severity
        for error in errors:
            severity = error.severity.value
            analysis["by_severity"][severity] = (
                analysis["by_severity"].get(severity, 0) + 1
            )

        # Analyze by recovery strategy
        for error in errors:
            if error.recovery_strategy:
                strategy = error.recovery_strategy.value
                analysis["by_recovery_strategy"][strategy] = (
                    analysis["by_recovery_strategy"].get(strategy, 0) + 1
                )

        # Most common error codes
        for error in errors:
            code = error.error_code
            analysis["most_common_errors"][code] = (
                analysis["most_common_errors"].get(code, 0) + 1
            )

        return analysis


# Error handling utilities
def handle_error(error: Exception, context: Dict[str, Any] = None) -> StructuredError:
    """
    Handle and classify an error with context.

    Args:
        error: The error to handle
        context: Additional context for the error

    Returns:
        StructuredError: Classified and contextualized error
    """
    if isinstance(error, StructuredError):
        if context:
            error.context.update(context)
        return error

    structured_error = ErrorClassifier.classify_exception(error)
    if context:
        structured_error.context.update(context)

    return structured_error


def create_error_response(error: StructuredError) -> Dict[str, Any]:
    """
    Create a standardized error response for APIs.

    Args:
        error: The structured error

    Returns:
        Dict containing error response
    """
    return {
        "error": {
            "code": error.error_code,
            "message": error.user_message,
            "correlation_id": error.correlation_id,
            "timestamp": error.timestamp.isoformat(),
            "severity": error.severity.value,
        },
        "success": False,
    }


# Example usage and testing
if __name__ == "__main__":
    # Test error classification
    try:
        raise ValueError("Invalid input value")
    except Exception as e:
        structured_error = ErrorClassifier.classify_exception(e)
        print("Classified error:", structured_error.to_json())

    # Test custom error
    auth_error = AuthenticationError(
        message="Invalid credentials",
        correlation_id="123-456-789",
        context={"user_id": "user123"},
    )
    print("Custom error:", auth_error.to_json())

    # Test error response
    response = create_error_response(auth_error)
    print("Error response:", json.dumps(response, indent=2))
