"""
API Contract Testing Utilities
=============================

This module provides helper functions and utilities for API contract testing:
- OpenAPI schema validation helpers
- Response format validation
- Error response consistency checking
- Mock data generation
- Test data factories

Based on FastAPI testing patterns from Context7 documentation.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import jsonschema
from jsonschema import ValidationError as JsonSchemaValidationError


class OpenAPIValidator:
    """Validates OpenAPI schemas and responses"""

    def __init__(self, openapi_schema: dict[str, Any]):
        self.openapi_schema = openapi_schema
        self.components = openapi_schema.get("components", {})
        self.schemas = self.components.get("schemas", {})

    def validate_request_schema(
        self, schema_name: str, request_data: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """
        Validate request data against OpenAPI schema

        Args:
            schema_name: Name of the schema in components/schemas
            request_data: Request data to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if schema_name not in self.schemas:
            return False, f"Schema '{schema_name}' not found in OpenAPI specification"

        schema = self.schemas[schema_name]

        try:
            jsonschema.validate(request_data, schema)
            return True, None
        except JsonSchemaValidationError as e:
            return False, str(e)

    def validate_response_schema(
        self, schema_name: str, response_data: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """
        Validate response data against OpenAPI schema

        Args:
            schema_name: Name of the schema in components/schemas
            response_data: Response data to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        return self.validate_request_schema(schema_name, response_data)

    def get_schema_by_name(self, schema_name: str) -> dict[str, Any] | None:
        """Get schema definition by name"""
        return self.schemas.get(schema_name)

    def get_endpoint_schema(
        self, path: str, method: str, response_code: str = "200"
    ) -> dict[str, Any] | None:
        """
        Get response schema for specific endpoint

        Args:
            path: API path (e.g., "/api/v1/memories/")
            method: HTTP method (e.g., "get", "post")
            response_code: HTTP response code (e.g., "200", "422")

        Returns:
            Schema definition or None if not found
        """
        paths = self.openapi_schema.get("paths", {})

        if path not in paths:
            return None

        path_item = paths[path]
        if method.lower() not in path_item:
            return None

        operation = path_item[method.lower()]
        responses = operation.get("responses", {})

        if response_code not in responses:
            return None

        response_obj = responses[response_code]
        content = response_obj.get("content", {})

        if "application/json" not in content:
            return None

        return content["application/json"].get("schema")

    def validate_error_response_format(
        self, error_response: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """
        Validate that error response follows FastAPI error format

        Args:
            error_response: Error response to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for FastAPI validation error format
        if "detail" not in error_response:
            return False, "Error response missing 'detail' field"

        detail = error_response["detail"]

        # Single error message format
        if isinstance(detail, str):
            return True, None

        # Multiple validation errors format
        if isinstance(detail, list):
            for error in detail:
                if not isinstance(error, dict):
                    return False, "Error detail items must be dictionaries"

                required_fields = ["loc", "msg", "type"]
                for field in required_fields:
                    if field not in error:
                        return False, f"Error detail missing required field: {field}"

                # Validate field types
                if not isinstance(error["loc"], list):
                    return False, "Error 'loc' field must be a list"

                if not isinstance(error["msg"], str):
                    return False, "Error 'msg' field must be a string"

                if not isinstance(error["type"], str):
                    return False, "Error 'type' field must be a string"

            return True, None

        return False, "Error 'detail' field must be string or list"


class ResponseValidator:
    """Validates API response formats and content"""

    @staticmethod
    def validate_pagination_response(
        response_data: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """
        Validate pagination response format

        Args:
            response_data: Response data to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ["items", "total", "page", "size", "pages"]

        for field in required_fields:
            if field not in response_data:
                return False, f"Missing required pagination field: {field}"

        # Validate field types
        if not isinstance(response_data["items"], list):
            return False, "Pagination 'items' field must be a list"

        for field in ["total", "page", "size", "pages"]:
            if not isinstance(response_data[field], int):
                return False, f"Pagination '{field}' field must be an integer"

        # Validate pagination logic
        total = response_data["total"]
        page = response_data["page"]
        size = response_data["size"]
        pages = response_data["pages"]

        if total < 0:
            return False, "Total count cannot be negative"

        if page < 1:
            return False, "Page number must be >= 1"

        if size < 1:
            return False, "Page size must be >= 1"

        if pages < 0:
            return False, "Total pages cannot be negative"

        # Check pagination math
        if total == 0:
            if pages != 0:
                return False, "Pages should be 0 when total is 0"
        else:
            expected_pages = (total + size - 1) // size
            if pages != expected_pages:
                return (
                    False,
                    f"Incorrect pages calculation: expected {expected_pages}, got {pages}",
                )

        return True, None

    @staticmethod
    def validate_memory_response(
        response_data: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """
        Validate memory response format

        Args:
            response_data: Response data to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ["id", "content", "created_at"]

        for field in required_fields:
            if field not in response_data:
                return False, f"Missing required memory field: {field}"

        # Validate field types
        if not isinstance(response_data["id"], str):
            return False, "Memory 'id' field must be a string"

        if not isinstance(response_data["content"], str):
            return False, "Memory 'content' field must be a string"

        # Validate optional fields
        if "metadata" in response_data:
            if response_data["metadata"] is not None and not isinstance(
                response_data["metadata"], dict
            ):
                return False, "Memory 'metadata' field must be a dictionary or null"

        if "categories" in response_data:
            if not isinstance(response_data["categories"], list):
                return False, "Memory 'categories' field must be a list"

        return True, None

    @staticmethod
    def validate_uuid_format(uuid_string: str) -> bool:
        """
        Validate UUID format

        Args:
            uuid_string: UUID string to validate

        Returns:
            True if valid UUID format, False otherwise
        """
        try:
            uuid4(uuid_string)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_timestamp_format(timestamp: str | int) -> bool:
        """
        Validate timestamp format

        Args:
            timestamp: Timestamp to validate (ISO string or epoch int)

        Returns:
            True if valid timestamp format, False otherwise
        """
        if isinstance(timestamp, int):
            # Unix timestamp
            try:
                datetime.fromtimestamp(timestamp, tz=UTC)
                return True
            except (ValueError, OSError):
                return False

        elif isinstance(timestamp, str):
            # ISO format string
            try:
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                return True
            except ValueError:
                return False

        return False


class TestDataFactory:
    """Factory for creating test data"""

    @staticmethod
    def create_test_user_data() -> dict[str, Any]:
        """Create test user data"""
        return {
            "user_id": f"test_user_{uuid4().hex[:8]}",
            "name": "Test User",
            "email": f"test{uuid4().hex[:8]}@example.com",
        }

    @staticmethod
    def create_test_app_data() -> dict[str, Any]:
        """Create test app data"""
        return {
            "name": f"test_app_{uuid4().hex[:8]}",
            "description": "Test Application",
        }

    @staticmethod
    def create_test_memory_request() -> dict[str, Any]:
        """Create test memory creation request"""
        return {
            "user_id": f"test_user_{uuid4().hex[:8]}",
            "text": "Test memory content for API contract testing",
            "metadata": {
                "test": True,
                "category": "contract_test",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            "app": f"test_app_{uuid4().hex[:8]}",
        }

    @staticmethod
    def create_memory_data(user_id: str = None) -> dict[str, Any]:
        """Create test memory data for unit tests"""
        return {
            "user_id": user_id or f"test_user_{uuid4().hex[:8]}",
            "text": "Test memory content for unit testing",
            "metadata": {
                "test": True,
                "category": "unit_test",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            "app": f"test_app_{uuid4().hex[:8]}",
        }

    @staticmethod
    def create_test_memory_response() -> dict[str, Any]:
        """Create test memory response"""
        return {
            "id": str(uuid4()),
            "content": "Test memory content",
            "created_at": int(datetime.now(UTC).timestamp()),
            "user_id": f"test_user_{uuid4().hex[:8]}",
            "metadata": {"test": True},
            "state": "active",
            "categories": ["test"],
            "app_name": "test_app",
        }

    @staticmethod
    def create_test_pagination_response(
        items: list[dict[str, Any]] = None,
        total: int = 0,
        page: int = 1,
        size: int = 10,
    ) -> dict[str, Any]:
        """Create test pagination response"""
        if items is None:
            items = []

        pages = (total + size - 1) // size if total > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages,
        }

    @staticmethod
    def create_test_error_response(
        field_errors: list[tuple[str, str]] = None,
    ) -> dict[str, Any]:
        """
        Create test error response

        Args:
            field_errors: List of (field_name, error_message) tuples

        Returns:
            Test error response
        """
        if field_errors is None:
            field_errors = [("field", "error message")]

        detail = []
        for field, message in field_errors:
            detail.append(
                {"loc": ["body", field], "msg": message, "type": "value_error"}
            )

        return {"detail": detail}


class ContractTestAssertions:
    """Custom assertions for contract testing"""

    @staticmethod
    def assert_valid_openapi_schema(
        schema: dict[str, Any], schema_name: str = "OpenAPI Schema"
    ):
        """Assert that schema is valid OpenAPI format"""
        assert isinstance(schema, dict), f"{schema_name} must be a dictionary"
        assert "openapi" in schema, f"{schema_name} missing 'openapi' field"
        assert "info" in schema, f"{schema_name} missing 'info' field"
        assert "paths" in schema, f"{schema_name} missing 'paths' field"

        # Validate OpenAPI version
        version = schema["openapi"]
        assert isinstance(version, str), (
            f"{schema_name} 'openapi' field must be a string"
        )
        assert version.startswith("3."), f"{schema_name} must use OpenAPI 3.x"

    @staticmethod
    def assert_valid_pagination_response(response_data: dict[str, Any]):
        """Assert that response is valid pagination format"""
        is_valid, error_message = ResponseValidator.validate_pagination_response(
            response_data
        )
        assert is_valid, f"Invalid pagination response: {error_message}"

    @staticmethod
    def assert_valid_memory_response(response_data: dict[str, Any]):
        """Assert that response is valid memory format"""
        is_valid, error_message = ResponseValidator.validate_memory_response(
            response_data
        )
        assert is_valid, f"Invalid memory response: {error_message}"

    @staticmethod
    def assert_valid_error_response(response_data: dict[str, Any]):
        """Assert that response is valid error format"""
        validator = OpenAPIValidator({})
        is_valid, error_message = validator.validate_error_response_format(
            response_data
        )
        assert is_valid, f"Invalid error response: {error_message}"

    @staticmethod
    def assert_schema_compliance(
        request_data: dict[str, Any],
        schema: dict[str, Any],
        schema_name: str = "Schema",
    ):
        """Assert that data complies with schema"""
        try:
            jsonschema.validate(request_data, schema)
        except JsonSchemaValidationError as e:
            assert False, f"Data does not comply with {schema_name}: {e}"

    @staticmethod
    def assert_response_status_code(response, expected_status: int, message: str = ""):
        """Assert response status code with helpful message"""
        actual_status = response.status_code
        if actual_status != expected_status:
            try:
                error_detail = response.json()
                message_suffix = f" Response: {error_detail}"
            except Exception:
                message_suffix = f" Response text: {response.text}"

            assert actual_status == expected_status, (
                f"{message} Expected status {expected_status}, got {actual_status}.{message_suffix}"
            )

    @staticmethod
    def assert_content_type_json(response):
        """Assert that response content type is JSON"""
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type, (
            f"Expected JSON content type, got: {content_type}"
        )

    @staticmethod
    def assert_cors_headers_present(response):
        """Assert that CORS headers are present"""
        cors_headers = [
            "access-control-allow-origin",
            "access-control-allow-methods",
            "access-control-allow-headers",
        ]

        response_headers = {k.lower(): v for k, v in response.headers.items()}

        for header in cors_headers:
            assert header in response_headers, f"Missing CORS header: {header}"


class MockDataGenerator:
    """Generate mock data for testing"""

    @staticmethod
    def generate_memory_list(count: int = 5) -> list[dict[str, Any]]:
        """Generate list of mock memory objects"""
        memories = []
        for i in range(count):
            memory = TestDataFactory.create_test_memory_response()
            memory["content"] = f"Test memory content {i + 1}"
            memories.append(memory)
        return memories

    @staticmethod
    def generate_large_dataset(size: int = 1000) -> list[dict[str, Any]]:
        """Generate large dataset for pagination testing"""
        return [
            {
                "id": str(uuid4()),
                "content": f"Memory {i + 1}",
                "created_at": int(datetime.now(UTC).timestamp()) - i,
                "user_id": "test_user",
                "metadata": {"index": i},
                "state": "active",
                "categories": [f"category_{i % 5}"],
                "app_name": "test_app",
            }
            for i in range(size)
        ]

    @staticmethod
    def generate_invalid_requests() -> list[dict[str, Any]]:
        """Generate list of invalid request examples"""
        return [
            {},  # Empty request
            {"user_id": ""},  # Empty user_id
            {"user_id": None},  # Null user_id
            {"user_id": "test", "text": ""},  # Empty text
            {"user_id": "test", "text": None},  # Null text
            {
                "user_id": "test",
                "text": "content",
                "metadata": "invalid",
            },  # Invalid metadata
            {"user_id": "test", "text": "content", "app": ""},  # Empty app
            {"user_id": "test", "text": "content", "app": None},  # Null app
        ]


# Export all classes and functions for easy import
__all__ = [
    "OpenAPIValidator",
    "ResponseValidator",
    "TestDataFactory",
    "ContractTestAssertions",
    "MockDataGenerator",
]
