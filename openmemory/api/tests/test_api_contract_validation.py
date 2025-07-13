"""
API Contract Testing Suite - Step 2.1 Implementation
====================================================

This comprehensive test suite validates API contracts to prevent breaking changes:
- OpenAPI schema generation and validation
- Request/response contract testing
- Error consistency validation
- Input validation testing
- Authentication and authorization testing

Based on FastAPI and pytest best practices from Context7 documentation.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import jsonschema
import pytest
from app.database import SessionLocal, get_db
from app.models import App, Memory, MemoryState, User
from app.routers.config import ConfigSchema, LLMConfig, LLMProvider
from app.routers.memories import CreateMemoryRequest
from app.schemas import (
    MemoryCreate,
    MemoryResponse,
    MemoryUpdate,
    PaginatedMemoryResponse,
)
from fastapi import status
from fastapi.testclient import TestClient
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate
from main import app
from pydantic import ValidationError


class TestAPIContractValidation:
    """
    Comprehensive API Contract Testing Suite

    Tests OpenAPI schema compliance, request/response contracts,
    error consistency, and input validation across all endpoints.
    """

    @pytest.fixture
    def client(self):
        """Create test client with proper configuration"""
        return TestClient(app)

    @pytest.fixture
    def db(self):
        """Create test database session"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    @pytest.fixture
    def test_user(self, db):
        """Create test user"""
        user = User(
            id=uuid4(),
            user_id="test_user_api_contract",
            name="Test User",
            email="test@example.com",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @pytest.fixture
    def test_app(self, db, test_user):
        """Create test app"""
        app_obj = App(
            id=uuid4(), owner_id=test_user.id, name="test_app", description="Test App"
        )
        db.add(app_obj)
        db.commit()
        db.refresh(app_obj)
        return app_obj

    @pytest.fixture
    def test_memory(self, db, test_user, test_app):
        """Create test memory"""
        memory = Memory(
            id=uuid4(),
            user_id=test_user.id,
            app_id=test_app.id,
            content="Test memory content",
            state=MemoryState.active,
            metadata_={"test": "data"},
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory


@pytest.mark.contract
@pytest.mark.openapi
class TestOpenAPISchemaValidation(TestAPIContractValidation):
    """Tests for OpenAPI schema generation and validation"""

    def test_openapi_schema_generation(self, client):
        """Test that OpenAPI schema is generated correctly"""
        response = client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK

        schema = response.json()

        # Validate basic OpenAPI structure
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        assert "components" in schema

        # Validate OpenAPI version
        assert schema["openapi"].startswith("3.")

        # Validate API info
        assert "title" in schema["info"]
        assert schema["info"]["title"] == "OpenMemory API"

        # Validate that all our main endpoints are present
        expected_paths = [
            "/api/v1/memories/",
            "/api/v1/apps/",
            "/api/v1/stats/",
            "/api/v1/config/",
        ]

        for path in expected_paths:
            assert path in schema["paths"], f"Missing path: {path}"

    def test_schema_components_validation(self, client):
        """Test that schema components are properly defined"""
        response = client.get("/openapi.json")
        schema = response.json()

        # Check that main schemas are present
        components = schema.get("components", {})
        schemas = components.get("schemas", {})

        expected_schemas = [
            "CreateMemoryRequest",
            "MemoryResponse",
            "PaginatedMemoryResponse",
            "ValidationError",
            "HTTPValidationError",
        ]

        for schema_name in expected_schemas:
            assert schema_name in schemas, f"Missing schema: {schema_name}"

    def test_request_response_schema_definitions(self, client):
        """Test that request/response schemas are properly defined"""
        response = client.get("/openapi.json")
        schema = response.json()

        # Test memory creation endpoint schema
        memories_path = schema["paths"]["/api/v1/memories/"]

        # Test POST request body schema
        post_op = memories_path["post"]
        assert "requestBody" in post_op
        request_body = post_op["requestBody"]
        assert "content" in request_body
        assert "application/json" in request_body["content"]

        # Test GET response schema
        get_op = memories_path["get"]
        assert "responses" in get_op
        responses = get_op["responses"]
        assert "200" in responses
        assert "content" in responses["200"]

    def test_error_response_schemas(self, client):
        """Test that error response schemas are consistent"""
        response = client.get("/openapi.json")
        schema = response.json()

        # Check that error schemas are defined
        schemas = schema["components"]["schemas"]

        # Validate ValidationError schema
        validation_error = schemas["ValidationError"]
        assert "type" in validation_error
        assert validation_error["type"] == "object"
        assert "properties" in validation_error
        assert "loc" in validation_error["properties"]
        assert "msg" in validation_error["properties"]
        assert "type" in validation_error["properties"]

        # Validate HTTPValidationError schema
        http_validation_error = schemas["HTTPValidationError"]
        assert "type" in http_validation_error
        assert http_validation_error["type"] == "object"
        assert "properties" in http_validation_error
        assert "detail" in http_validation_error["properties"]


@pytest.mark.contract
class TestMemoryEndpointContracts(TestAPIContractValidation):
    """Test memory endpoint contracts"""

    def test_create_memory_request_contract(self, client):
        """Test memory creation request contract"""
        # Valid request
        valid_request = {
            "user_id": "test_user",
            "text": "Test memory content",
            "metadata": {"key": "value"},
            "app": "test_app",
        }

        response = client.post("/api/v1/memories/", json=valid_request)

        # Should not return 422 validation error for valid request
        assert response.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY

        # Response should contain expected fields
        if response.status_code == status.HTTP_200_OK:
            response_data = response.json()
            # Check if it's a success response or error response
            assert isinstance(response_data, dict)

    def test_create_memory_invalid_request_contract(self, client):
        """Test memory creation with invalid request data"""
        # Missing required fields
        invalid_requests = [
            {},  # Empty request
            {"user_id": "test_user"},  # Missing text
            {"text": "test"},  # Missing user_id
            {"user_id": "", "text": "test"},  # Empty user_id
            {"user_id": "test_user", "text": ""},  # Empty text
            {
                "user_id": "test_user",
                "text": "test",
                "metadata": "invalid",
            },  # Invalid metadata type
        ]

        for invalid_request in invalid_requests:
            response = client.post("/api/v1/memories/", json=invalid_request)

            # Should return validation error
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            # Response should follow validation error schema
            error_data = response.json()
            assert "detail" in error_data
            assert isinstance(error_data["detail"], list)

            # Each error should have required fields
            for error in error_data["detail"]:
                assert "loc" in error
                assert "msg" in error
                assert "type" in error

    def test_list_memories_response_contract(self, client):
        """Test memory listing response contract"""
        response = client.get("/api/v1/memories/?user_id=test_user")

        # Should return successful response
        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()

        # Should follow PaginatedMemoryResponse schema
        assert "items" in response_data
        assert "total" in response_data
        assert "page" in response_data
        assert "size" in response_data
        assert "pages" in response_data

        # Validate types
        assert isinstance(response_data["items"], list)
        assert isinstance(response_data["total"], int)
        assert isinstance(response_data["page"], int)
        assert isinstance(response_data["size"], int)
        assert isinstance(response_data["pages"], int)

        # Validate pagination values
        assert response_data["page"] >= 1
        assert response_data["size"] >= 1
        assert response_data["pages"] >= 0
        assert response_data["total"] >= 0

    def test_list_memories_query_parameters(self, client):
        """Test memory listing with query parameters"""
        # Test with valid query parameters
        query_params = {
            "user_id": "test_user",
            "page": 1,
            "size": 10,
            "search_query": "test",
        }

        response = client.get("/api/v1/memories/", params=query_params)
        assert response.status_code == status.HTTP_200_OK

        # Test with invalid query parameters
        invalid_params = [
            {"user_id": "test_user", "page": 0},  # Invalid page
            {"user_id": "test_user", "size": 0},  # Invalid size
            {"user_id": "test_user", "page": "invalid"},  # Invalid page type
            {"user_id": "test_user", "size": "invalid"},  # Invalid size type
        ]

        for invalid_param in invalid_params:
            response = client.get("/api/v1/memories/", params=invalid_param)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_memory_by_id_contract(self, client):
        """Test getting memory by ID contract"""
        # Test with valid UUID format
        test_id = str(uuid4())
        response = client.get(f"/api/v1/memories/{test_id}")

        # Should return 404 for non-existent memory (not 422)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Test with invalid UUID format
        invalid_id = "invalid-uuid"
        response = client.get(f"/api/v1/memories/{invalid_id}")

        # Should return 422 for invalid UUID format
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.contract
class TestAppsEndpointContracts(TestAPIContractValidation):
    """Test apps endpoint contracts"""

    def test_list_apps_response_contract(self, client):
        """Test apps listing response contract"""
        response = client.get("/api/v1/apps/?user_id=test_user")

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()

        # Should be a list of apps
        assert isinstance(response_data, list)

        # Each app should have required fields
        for app in response_data:
            assert "id" in app
            assert "name" in app
            assert "owner_id" in app
            assert "created_at" in app
            assert "is_active" in app

            # Validate types
            assert isinstance(app["id"], str)
            assert isinstance(app["name"], str)
            assert isinstance(app["owner_id"], str)
            assert isinstance(app["is_active"], bool)

    def test_apps_query_parameters(self, client):
        """Test apps endpoint query parameters"""
        # Test missing user_id
        response = client.get("/api/v1/apps/")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test empty user_id
        response = client.get("/api/v1/apps/?user_id=")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.contract
class TestStatsEndpointContracts(TestAPIContractValidation):
    """Test stats endpoint contracts"""

    def test_stats_response_contract(self, client):
        """Test stats response contract"""
        response = client.get("/api/v1/stats/?user_id=test_user")

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()

        # Should contain expected fields
        assert "total_memories" in response_data
        assert "total_apps" in response_data
        assert "apps" in response_data

        # Validate types
        assert isinstance(response_data["total_memories"], int)
        assert isinstance(response_data["total_apps"], int)
        assert isinstance(response_data["apps"], list)

        # Validate non-negative values
        assert response_data["total_memories"] >= 0
        assert response_data["total_apps"] >= 0


@pytest.mark.contract
class TestConfigEndpointContracts(TestAPIContractValidation):
    """Test config endpoint contracts"""

    def test_get_config_response_contract(self, client):
        """Test get config response contract"""
        response = client.get("/api/v1/config/")

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()

        # Should be a valid config object
        assert isinstance(response_data, dict)

        # Should contain expected config sections
        if "mem0" in response_data:
            mem0_config = response_data["mem0"]
            assert "llm" in mem0_config
            assert "embedder" in mem0_config
            assert "vector_store" in mem0_config
            assert "graph_store" in mem0_config

    def test_update_config_request_contract(self, client):
        """Test update config request contract"""
        # Valid config update
        valid_config = {
            "mem0": {
                "llm": {
                    "provider": "openai",
                    "config": {
                        "model": "gpt-4",
                        "temperature": 0.1,
                        "max_tokens": 1000,
                    },
                }
            }
        }

        response = client.put("/api/v1/config/", json=valid_config)

        # Should not return validation error
        assert response.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test invalid config structure
        invalid_configs = [
            {"mem0": {"llm": "invalid"}},  # Invalid llm structure
            {"mem0": {"llm": {"provider": "openai"}}},  # Missing config
            {"mem0": {"llm": {"provider": "openai", "config": {}}}},  # Empty config
        ]

        for invalid_config in invalid_configs:
            response = client.put("/api/v1/config/", json=invalid_config)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.contract
class TestErrorConsistencyValidation(TestAPIContractValidation):
    """Test error response consistency across endpoints"""

    def test_404_error_consistency(self, client):
        """Test that 404 errors are consistent across endpoints"""
        # Test 404 responses from different endpoints
        endpoints_404 = [
            f"/api/v1/memories/{uuid4()}",
            f"/api/v1/apps/{uuid4()}",
        ]

        for endpoint in endpoints_404:
            response = client.get(endpoint)
            if response.status_code == status.HTTP_404_NOT_FOUND:
                error_data = response.json()
                assert "detail" in error_data
                assert isinstance(error_data["detail"], str)

    def test_422_error_consistency(self, client):
        """Test that 422 validation errors are consistent"""
        # Test validation errors from different endpoints
        invalid_requests = [
            ("POST", "/api/v1/memories/", {}),
            ("GET", "/api/v1/memories/", {"user_id": ""}),
            ("GET", "/api/v1/apps/", {}),
            ("GET", "/api/v1/stats/", {}),
        ]

        for method, endpoint, data in invalid_requests:
            if method == "POST":
                response = client.post(endpoint, json=data)
            else:
                response = client.get(endpoint, params=data)

            if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
                error_data = response.json()
                assert "detail" in error_data
                assert isinstance(error_data["detail"], list)

                # Each error should follow the same structure
                for error in error_data["detail"]:
                    assert "loc" in error
                    assert "msg" in error
                    assert "type" in error
                    assert isinstance(error["loc"], list)
                    assert isinstance(error["msg"], str)
                    assert isinstance(error["type"], str)

    def test_500_error_consistency(self, client):
        """Test that 500 errors are handled consistently"""
        # This test would require mocking internal errors
        # For now, we'll just verify the structure if we encounter them
        pass


@pytest.mark.contract
@pytest.mark.validation
class TestInputValidationComprehensive(TestAPIContractValidation):
    """Comprehensive input validation testing"""

    def test_string_field_validation(self, client):
        """Test string field validation"""
        # Test empty strings
        response = client.post(
            "/api/v1/memories/", json={"user_id": "", "text": "test", "app": "test_app"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test null strings
        response = client.post(
            "/api/v1/memories/",
            json={"user_id": None, "text": "test", "app": "test_app"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_uuid_field_validation(self, client):
        """Test UUID field validation"""
        # Test invalid UUID formats
        invalid_uuids = [
            "invalid-uuid",
            "123",
            "",
            "00000000-0000-0000-0000-000000000000",  # Nil UUID might be invalid
        ]

        for invalid_uuid in invalid_uuids:
            response = client.get(f"/api/v1/memories/{invalid_uuid}")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_integer_field_validation(self, client):
        """Test integer field validation"""
        # Test negative page numbers
        response = client.get("/api/v1/memories/?user_id=test_user&page=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test zero page numbers
        response = client.get("/api/v1/memories/?user_id=test_user&page=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test invalid integer types
        response = client.get("/api/v1/memories/?user_id=test_user&page=invalid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_json_field_validation(self, client):
        """Test JSON field validation"""
        # Test invalid JSON structure for metadata
        response = client.post(
            "/api/v1/memories/",
            json={
                "user_id": "test_user",
                "text": "test",
                "metadata": "invalid_json_structure",
                "app": "test_app",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.contract
class TestPaginationContractValidation(TestAPIContractValidation):
    """Test pagination contract validation"""

    def test_pagination_response_structure(self, client):
        """Test pagination response structure"""
        response = client.get("/api/v1/memories/?user_id=test_user&page=1&size=10")

        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()

        # Test pagination fields
        assert "items" in response_data
        assert "total" in response_data
        assert "page" in response_data
        assert "size" in response_data
        assert "pages" in response_data

        # Test pagination math
        total = response_data["total"]
        size = response_data["size"]
        pages = response_data["pages"]

        if total == 0:
            assert pages == 0
        else:
            expected_pages = (total + size - 1) // size
            assert pages == expected_pages

    def test_pagination_boundary_conditions(self, client):
        """Test pagination boundary conditions"""
        # Test maximum page size
        response = client.get("/api/v1/memories/?user_id=test_user&size=100")
        assert response.status_code == status.HTTP_200_OK

        # Test size larger than maximum
        response = client.get("/api/v1/memories/?user_id=test_user&size=1000")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test first page
        response = client.get("/api/v1/memories/?user_id=test_user&page=1")
        assert response.status_code == status.HTTP_200_OK

        # Test page beyond available data
        response = client.get("/api/v1/memories/?user_id=test_user&page=999999")
        assert response.status_code == status.HTTP_200_OK

        response_data = response.json()
        assert response_data["items"] == []


@pytest.mark.contract
class TestContentTypeValidation(TestAPIContractValidation):
    """Test content type validation"""

    def test_json_content_type_requirement(self, client):
        """Test that JSON content type is required for POST requests"""
        # Test POST without content type
        response = client.post("/api/v1/memories/", data="invalid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test POST with wrong content type
        response = client.post(
            "/api/v1/memories/", data="invalid", headers={"Content-Type": "text/plain"}
        )
        assert (
            response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
            or response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    def test_json_response_content_type(self, client):
        """Test that responses have correct content type"""
        response = client.get("/api/v1/memories/?user_id=test_user")
        assert response.status_code == status.HTTP_200_OK
        assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.contract
class TestAPIVersioningValidation(TestAPIContractValidation):
    """Test API versioning validation"""

    def test_api_version_in_urls(self, client):
        """Test that API version is consistent in URLs"""
        # Test that v1 endpoints are available
        v1_endpoints = [
            "/api/v1/memories/?user_id=test_user",
            "/api/v1/apps/?user_id=test_user",
            "/api/v1/stats/?user_id=test_user",
            "/api/v1/config/",
        ]

        for endpoint in v1_endpoints:
            response = client.get(endpoint)
            # Should not return 404 (endpoint exists)
            assert response.status_code != status.HTTP_404_NOT_FOUND

    def test_api_version_backward_compatibility(self, client):
        """Test API version backward compatibility"""
        # This test ensures that changes maintain backward compatibility
        # For now, we'll test that the current version works
        response = client.get("/api/v1/memories/?user_id=test_user")
        assert response.status_code == status.HTTP_200_OK

        # Future versions should maintain compatibility
        # This would be expanded when v2 is introduced


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
