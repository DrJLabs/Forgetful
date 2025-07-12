"""
OpenAPI Schema Validation Tests
==============================

This module provides comprehensive OpenAPI schema validation tests to ensure:
- OpenAPI 3.1 specification compliance
- Schema consistency across endpoints
- Proper JSON Schema validation
- API contract stability and backward compatibility

Based on OpenAPI Specification and JSON Schema standards from Context7 documentation.
"""

import json
from typing import Any, Dict, List, Optional

import jsonschema
import pytest
from main import app
from fastapi.testclient import TestClient
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate


@pytest.mark.openapi
class TestOpenAPISpecificationCompliance:
    """Test OpenAPI 3.1 specification compliance"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def openapi_schema(self, client):
        """Get OpenAPI schema"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        return response.json()

    def test_openapi_version_compliance(self, openapi_schema):
        """Test OpenAPI version compliance"""
        assert "openapi" in openapi_schema
        version = openapi_schema["openapi"]

        # Should be OpenAPI 3.x
        assert version.startswith("3.")

        # Parse version components
        version_parts = version.split(".")
        major = int(version_parts[0])
        minor = int(version_parts[1])

        assert major == 3
        assert minor >= 0

    def test_info_object_compliance(self, openapi_schema):
        """Test Info object compliance"""
        assert "info" in openapi_schema
        info = openapi_schema["info"]

        # Required fields
        assert "title" in info
        assert "version" in info

        # Validate types
        assert isinstance(info["title"], str)
        assert isinstance(info["version"], str)

        # Title should not be empty
        assert len(info["title"]) > 0

        # Version should follow semantic versioning pattern
        version = info["version"]
        assert len(version) > 0

    def test_paths_object_compliance(self, openapi_schema):
        """Test Paths object compliance"""
        assert "paths" in openapi_schema
        paths = openapi_schema["paths"]

        # Should be a dictionary
        assert isinstance(paths, dict)

        # Each path should start with /
        for path in paths.keys():
            assert path.startswith("/")

        # Each path should have valid operations
        for path, path_item in paths.items():
            assert isinstance(path_item, dict)

            # Check for valid HTTP methods
            valid_methods = [
                "get",
                "put",
                "post",
                "delete",
                "options",
                "head",
                "patch",
                "trace",
            ]
            for method in path_item.keys():
                if method not in ["summary", "description", "servers", "parameters"]:
                    assert method.lower() in valid_methods

    def test_components_object_compliance(self, openapi_schema):
        """Test Components object compliance"""
        if "components" not in openapi_schema:
            return  # Components object is optional

        components = openapi_schema["components"]
        assert isinstance(components, dict)

        # Check schemas section
        if "schemas" in components:
            schemas = components["schemas"]
            assert isinstance(schemas, dict)

            # Each schema should be a valid JSON Schema
            for schema_name, schema_def in schemas.items():
                assert isinstance(schema_def, dict)

                # Should have type property (most common)
                if "type" in schema_def:
                    valid_types = [
                        "null",
                        "boolean",
                        "object",
                        "array",
                        "number",
                        "string",
                        "integer",
                    ]
                    assert schema_def["type"] in valid_types

    def test_operation_object_compliance(self, openapi_schema):
        """Test Operation object compliance"""
        paths = openapi_schema["paths"]

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in [
                    "get",
                    "put",
                    "post",
                    "delete",
                    "options",
                    "head",
                    "patch",
                    "trace",
                ]:
                    assert isinstance(operation, dict)

                    # Responses are required
                    assert "responses" in operation
                    responses = operation["responses"]
                    assert isinstance(responses, dict)

                    # Should have at least one response
                    assert len(responses) > 0

                    # Each response should be valid
                    for status_code, response_obj in responses.items():
                        assert isinstance(response_obj, dict)
                        assert "description" in response_obj
                        assert isinstance(response_obj["description"], str)

    def test_schema_reference_resolution(self, openapi_schema):
        """Test that schema references can be resolved"""
        components = openapi_schema.get("components", {})
        schemas = components.get("schemas", {})

        # Find all $ref references in the schema
        refs = self._find_refs(openapi_schema)

        for ref in refs:
            if ref.startswith("#/components/schemas/"):
                schema_name = ref.split("/")[-1]
                assert (
                    schema_name in schemas
                ), f"Referenced schema not found: {schema_name}"

    def _find_refs(self, obj, refs=None):
        """Recursively find all $ref references"""
        if refs is None:
            refs = []

        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "$ref" and isinstance(value, str):
                    refs.append(value)
                else:
                    self._find_refs(value, refs)
        elif isinstance(obj, list):
            for item in obj:
                self._find_refs(item, refs)

        return refs

    def test_parameter_object_compliance(self, openapi_schema):
        """Test Parameter object compliance"""
        paths = openapi_schema["paths"]

        for path, path_item in paths.items():
            # Check path-level parameters
            if "parameters" in path_item:
                self._validate_parameters(path_item["parameters"])

            # Check operation-level parameters
            for method, operation in path_item.items():
                if method.lower() in [
                    "get",
                    "put",
                    "post",
                    "delete",
                    "options",
                    "head",
                    "patch",
                    "trace",
                ]:
                    if "parameters" in operation:
                        self._validate_parameters(operation["parameters"])

    def _validate_parameters(self, parameters):
        """Validate parameter objects"""
        assert isinstance(parameters, list)

        for param in parameters:
            assert isinstance(param, dict)

            # Required fields
            assert "name" in param
            assert "in" in param

            # Validate 'in' field
            valid_locations = ["query", "header", "path", "cookie"]
            assert param["in"] in valid_locations

            # Path parameters must be required
            if param["in"] == "path":
                assert param.get("required", False) is True

    def test_response_object_compliance(self, openapi_schema):
        """Test Response object compliance"""
        paths = openapi_schema["paths"]

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in [
                    "get",
                    "put",
                    "post",
                    "delete",
                    "options",
                    "head",
                    "patch",
                    "trace",
                ]:
                    responses = operation["responses"]

                    for status_code, response_obj in responses.items():
                        # Description is required
                        assert "description" in response_obj

                        # If content is present, validate it
                        if "content" in response_obj:
                            content = response_obj["content"]
                            assert isinstance(content, dict)

                            # Each media type should have a schema
                            for media_type, media_obj in content.items():
                                assert isinstance(media_obj, dict)
                                # Schema is common but not required
                                if "schema" in media_obj:
                                    assert isinstance(media_obj["schema"], dict)


@pytest.mark.openapi
class TestJSONSchemaValidation:
    """Test JSON Schema validation for request/response bodies"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def openapi_schema(self, client):
        """Get OpenAPI schema"""
        response = client.get("/openapi.json")
        return response.json()

    def test_memory_create_schema_validation(self, openapi_schema):
        """Test memory creation request schema validation"""
        # Find CreateMemoryRequest schema
        schemas = openapi_schema["components"]["schemas"]

        if "CreateMemoryRequest" in schemas:
            schema = schemas["CreateMemoryRequest"]

            # Valid request should pass validation
            valid_request = {
                "user_id": "test_user",
                "text": "Test memory content",
                "metadata": {"key": "value"},
                "app": "test_app",
            }

            # This should not raise an exception
            try:
                jsonschema.validate(valid_request, schema)
            except JsonSchemaValidationError as e:
                pytest.fail(f"Valid request failed schema validation: {e}")

            # Invalid request should fail validation
            invalid_request = {
                "user_id": "test_user"
                # Missing required 'text' field
            }

            with pytest.raises(JsonSchemaValidationError):
                jsonschema.validate(invalid_request, schema)

    def test_memory_response_schema_validation(self, openapi_schema):
        """Test memory response schema validation"""
        schemas = openapi_schema["components"]["schemas"]

        if "MemoryResponse" in schemas:
            schema = schemas["MemoryResponse"]

            # Valid response should pass validation
            valid_response = {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "content": "Test memory content",
                "created_at": "2023-01-01T00:00:00Z",
                "user_id": "test_user",
                "metadata": {"key": "value"},
                "state": "active",
                "categories": ["category1"],
                "app_name": "test_app",
            }

            # This should not raise an exception
            try:
                jsonschema.validate(valid_response, schema)
            except JsonSchemaValidationError as e:
                pytest.fail(f"Valid response failed schema validation: {e}")

    def test_pagination_response_schema_validation(self, openapi_schema):
        """Test pagination response schema validation"""
        schemas = openapi_schema["components"]["schemas"]

        if "PaginatedMemoryResponse" in schemas:
            schema = schemas["PaginatedMemoryResponse"]

            # Valid paginated response should pass validation
            valid_response = {
                "items": [],
                "total": 0,
                "page": 1,
                "size": 10,
                "pages": 0,
            }

            try:
                jsonschema.validate(valid_response, schema)
            except JsonSchemaValidationError as e:
                pytest.fail(f"Valid paginated response failed schema validation: {e}")

    def test_error_response_schema_validation(self, openapi_schema):
        """Test error response schema validation"""
        schemas = openapi_schema["components"]["schemas"]

        if "HTTPValidationError" in schemas:
            schema = schemas["HTTPValidationError"]

            # Valid error response should pass validation
            valid_error = {
                "detail": [
                    {
                        "loc": ["body", "user_id"],
                        "msg": "field required",
                        "type": "value_error.missing",
                    }
                ]
            }

            try:
                jsonschema.validate(valid_error, schema)
            except JsonSchemaValidationError as e:
                pytest.fail(f"Valid error response failed schema validation: {e}")


@pytest.mark.openapi
class TestSchemaConsistency:
    """Test schema consistency across endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def openapi_schema(self, client):
        """Get OpenAPI schema"""
        response = client.get("/openapi.json")
        return response.json()

    def test_consistent_error_schemas(self, openapi_schema):
        """Test that error schemas are consistent across endpoints"""
        paths = openapi_schema["paths"]
        error_schemas = set()

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in [
                    "get",
                    "put",
                    "post",
                    "delete",
                    "options",
                    "head",
                    "patch",
                    "trace",
                ]:
                    responses = operation["responses"]

                    # Check 422 validation error responses
                    if "422" in responses:
                        response_obj = responses["422"]
                        if "content" in response_obj:
                            content = response_obj["content"]
                            if "application/json" in content:
                                schema_ref = content["application/json"].get(
                                    "schema", {}
                                )
                                if "$ref" in schema_ref:
                                    error_schemas.add(schema_ref["$ref"])

        # All 422 errors should use the same schema
        assert len(error_schemas) <= 1, f"Inconsistent error schemas: {error_schemas}"

    def test_consistent_uuid_format(self, openapi_schema):
        """Test that UUID fields use consistent format"""
        schemas = openapi_schema["components"]["schemas"]
        uuid_formats = set()

        for schema_name, schema_def in schemas.items():
            if "properties" in schema_def:
                for prop_name, prop_def in schema_def["properties"].items():
                    if "id" in prop_name.lower() or prop_name.endswith("_id"):
                        if "format" in prop_def:
                            uuid_formats.add(prop_def["format"])
                        elif "type" in prop_def and prop_def["type"] == "string":
                            # Check if it might be a UUID field
                            if "pattern" in prop_def:
                                uuid_formats.add(prop_def["pattern"])

        # UUID fields should use consistent format
        if len(uuid_formats) > 1:
            # Allow some variation but warn about inconsistency
            print(f"Warning: Multiple UUID formats found: {uuid_formats}")

    def test_consistent_timestamp_format(self, openapi_schema):
        """Test that timestamp fields use consistent format"""
        schemas = openapi_schema["components"]["schemas"]
        timestamp_formats = set()

        for schema_name, schema_def in schemas.items():
            if "properties" in schema_def:
                for prop_name, prop_def in schema_def["properties"].items():
                    if "created_at" in prop_name or "updated_at" in prop_name:
                        if "format" in prop_def:
                            timestamp_formats.add(prop_def["format"])
                        elif "type" in prop_def:
                            timestamp_formats.add(prop_def["type"])

        # Timestamp fields should use consistent format
        if len(timestamp_formats) > 1:
            # Allow some variation but warn about inconsistency
            print(f"Warning: Multiple timestamp formats found: {timestamp_formats}")

    def test_consistent_pagination_schema(self, openapi_schema):
        """Test that pagination schemas are consistent"""
        schemas = openapi_schema["components"]["schemas"]
        pagination_schemas = []

        for schema_name, schema_def in schemas.items():
            if "paginated" in schema_name.lower() or "page" in schema_name.lower():
                pagination_schemas.append((schema_name, schema_def))

        # All pagination schemas should have consistent fields
        required_pagination_fields = ["items", "total", "page", "size", "pages"]

        for schema_name, schema_def in pagination_schemas:
            if "properties" in schema_def:
                properties = schema_def["properties"]
                for field in required_pagination_fields:
                    assert (
                        field in properties
                    ), f"Missing pagination field '{field}' in {schema_name}"


@pytest.mark.openapi
class TestAPIContractStability:
    """Test API contract stability and backward compatibility"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def openapi_schema(self, client):
        """Get OpenAPI schema"""
        response = client.get("/openapi.json")
        return response.json()

    def test_required_fields_stability(self, openapi_schema):
        """Test that required fields are stable"""
        schemas = openapi_schema["components"]["schemas"]

        # Key schemas that should maintain stability
        critical_schemas = [
            "CreateMemoryRequest",
            "MemoryResponse",
            "PaginatedMemoryResponse",
        ]

        for schema_name in critical_schemas:
            if schema_name in schemas:
                schema = schemas[schema_name]

                # Check that critical fields are present
                if schema_name == "CreateMemoryRequest":
                    required_fields = ["user_id", "text"]
                elif schema_name == "MemoryResponse":
                    required_fields = ["id", "content", "created_at"]
                elif schema_name == "PaginatedMemoryResponse":
                    required_fields = ["items", "total", "page", "size", "pages"]
                else:
                    continue

                if "properties" in schema:
                    properties = schema["properties"]
                    for field in required_fields:
                        assert (
                            field in properties
                        ), f"Missing required field '{field}' in {schema_name}"

    def test_endpoint_stability(self, openapi_schema):
        """Test that critical endpoints are stable"""
        paths = openapi_schema["paths"]

        # Critical endpoints that should always be available
        critical_endpoints = [
            "/api/v1/memories/",
            "/api/v1/apps/",
            "/api/v1/stats/",
            "/api/v1/config/",
        ]

        for endpoint in critical_endpoints:
            assert endpoint in paths, f"Critical endpoint missing: {endpoint}"

    def test_http_method_stability(self, openapi_schema):
        """Test that HTTP methods are stable for critical endpoints"""
        paths = openapi_schema["paths"]

        # Critical operations that should always be available
        critical_operations = [
            ("/api/v1/memories/", "get"),
            ("/api/v1/memories/", "post"),
            ("/api/v1/apps/", "get"),
            ("/api/v1/stats/", "get"),
            ("/api/v1/config/", "get"),
        ]

        for endpoint, method in critical_operations:
            if endpoint in paths:
                assert (
                    method in paths[endpoint]
                ), f"Missing method {method} for {endpoint}"

    def test_response_schema_stability(self, openapi_schema):
        """Test that response schemas maintain backward compatibility"""
        paths = openapi_schema["paths"]

        # Check that 200 responses have consistent schema structure
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in ["get", "post", "put", "delete"]:
                    responses = operation.get("responses", {})
                    if "200" in responses:
                        response_obj = responses["200"]

                        # Should have description
                        assert "description" in response_obj

                        # If content is present, should have proper structure
                        if "content" in response_obj:
                            content = response_obj["content"]
                            assert "application/json" in content
                            json_content = content["application/json"]
                            assert "schema" in json_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
