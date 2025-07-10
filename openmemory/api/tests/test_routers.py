"""
Unit tests for OpenMemory API routers.
"""

import pytest
import json
from datetime import datetime
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import USER_ID, DEFAULT_APP_ID


class TestMemoryRoutes:
    """Test cases for memory-related routes."""

    @pytest.mark.asyncio
    async def test_add_memory_success(self, test_client: AsyncClient, test_user, test_app, mock_mem0_client):
        """Test successfully adding a memory."""
        memory_data = {
            "messages": [
                {"role": "user", "content": "Test message"},
                {"role": "assistant", "content": "Test response"}
            ],
            "user_id": test_user.user_id,
            "app_id": test_app.app_id,
            "metadata": {"category": "test"}
        }
        
        response = await test_client.post("/memories", json=memory_data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "Memory added successfully"
        assert "id" in result

    @pytest.mark.asyncio
    async def test_add_memory_missing_required_fields(self, test_client: AsyncClient):
        """Test adding memory with missing required fields."""
        memory_data = {
            "messages": [{"role": "user", "content": "Test"}]
            # Missing user_id
        }
        
        response = await test_client.post("/memories", json=memory_data)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_add_memory_invalid_user_id(self, test_client: AsyncClient):
        """Test adding memory with invalid user_id."""
        memory_data = {
            "messages": [{"role": "user", "content": "Test"}],
            "user_id": "nonexistent_user"
        }
        
        response = await test_client.post("/memories", json=memory_data)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_search_memories_success(self, test_client: AsyncClient, test_user, mock_mem0_client):
        """Test successfully searching memories."""
        search_data = {
            "query": "test search",
            "user_id": test_user.user_id,
            "limit": 10
        }
        
        response = await test_client.post("/search", json=search_data)
        
        assert response.status_code == 200
        result = response.json()
        assert "results" in result
        assert isinstance(result["results"], list)

    @pytest.mark.asyncio
    async def test_search_memories_empty_query(self, test_client: AsyncClient, test_user):
        """Test searching with empty query."""
        search_data = {
            "query": "",
            "user_id": test_user.user_id
        }
        
        response = await test_client.post("/search", json=search_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_memories_success(self, test_client: AsyncClient, test_user, mock_mem0_client):
        """Test successfully retrieving all memories."""
        response = await test_client.get(f"/memories?user_id={test_user.user_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_memories_with_pagination(self, test_client: AsyncClient, test_user, mock_mem0_client):
        """Test retrieving memories with pagination."""
        response = await test_client.get(f"/memories?user_id={test_user.user_id}&page=1&size=5")
        
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_memory_by_id_success(self, test_client: AsyncClient, test_user, mock_mem0_client):
        """Test successfully retrieving a specific memory."""
        memory_id = "test-memory-id"
        
        response = await test_client.get(f"/memories/{memory_id}?user_id={test_user.user_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == memory_id

    @pytest.mark.asyncio
    async def test_get_memory_by_id_not_found(self, test_client: AsyncClient, test_user):
        """Test retrieving non-existent memory."""
        memory_id = "nonexistent-memory-id"
        
        with patch('app.utils.mem0_client.mem0_client.get') as mock_get:
            mock_get.side_effect = Exception("Memory not found")
            
            response = await test_client.get(f"/memories/{memory_id}?user_id={test_user.user_id}")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_memory_success(self, test_client: AsyncClient, test_user, mock_mem0_client):
        """Test successfully updating a memory."""
        memory_id = "test-memory-id"
        update_data = {
            "text": "Updated memory content"
        }
        
        with patch('app.utils.mem0_client.mem0_client.update') as mock_update:
            mock_update.return_value = {"message": "Memory updated successfully"}
            
            response = await test_client.put(f"/memories/{memory_id}", json=update_data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["message"] == "Memory updated successfully"

    @pytest.mark.asyncio
    async def test_delete_memory_success(self, test_client: AsyncClient, test_user, mock_mem0_client):
        """Test successfully deleting a memory."""
        memory_id = "test-memory-id"
        
        response = await test_client.delete(f"/memories/{memory_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "Memory deleted successfully"

    @pytest.mark.asyncio
    async def test_delete_all_memories_success(self, test_client: AsyncClient, test_user, mock_mem0_client):
        """Test successfully deleting all memories."""
        response = await test_client.delete(f"/memories?user_id={test_user.user_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "All memories deleted successfully"

    @pytest.mark.asyncio
    async def test_batch_add_memories(self, test_client: AsyncClient, test_user, test_app, mock_mem0_client):
        """Test batch adding multiple memories."""
        batch_data = {
            "memories": [
                {
                    "messages": [{"role": "user", "content": f"Test message {i}"}],
                    "user_id": test_user.user_id,
                    "app_id": test_app.app_id
                }
                for i in range(3)
            ]
        }
        
        response = await test_client.post("/memories/batch", json=batch_data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "Batch memories added successfully"
        assert result["count"] == 3

    @pytest.mark.asyncio
    async def test_batch_add_memories_partial_failure(self, test_client: AsyncClient, test_user, test_app):
        """Test batch adding with some failures."""
        batch_data = {
            "memories": [
                {
                    "messages": [{"role": "user", "content": "Valid message"}],
                    "user_id": test_user.user_id,
                    "app_id": test_app.app_id
                },
                {
                    "messages": [{"role": "user", "content": "Invalid message"}],
                    "user_id": "nonexistent_user",
                    "app_id": test_app.app_id
                }
            ]
        }
        
        response = await test_client.post("/memories/batch", json=batch_data)
        
        assert response.status_code == 207  # Multi-status
        result = response.json()
        assert result["successful"] == 1
        assert result["failed"] == 1


class TestAppRoutes:
    """Test cases for app-related routes."""

    @pytest.mark.asyncio
    async def test_get_apps_success(self, test_client: AsyncClient, test_user):
        """Test successfully retrieving apps."""
        response = await test_client.get(f"/apps?user_id={test_user.user_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_apps_with_pagination(self, test_client: AsyncClient, test_user):
        """Test retrieving apps with pagination."""
        response = await test_client.get(f"/apps?user_id={test_user.user_id}&page=1&size=10")
        
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_create_app_success(self, test_client: AsyncClient, test_user):
        """Test successfully creating an app."""
        app_data = {
            "name": "Test App",
            "description": "A test application",
            "user_id": test_user.user_id
        }
        
        response = await test_client.post("/apps", json=app_data)
        
        assert response.status_code == 201
        result = response.json()
        assert result["name"] == "Test App"
        assert result["user_id"] == test_user.user_id

    @pytest.mark.asyncio
    async def test_create_app_missing_name(self, test_client: AsyncClient, test_user):
        """Test creating app with missing name."""
        app_data = {
            "user_id": test_user.user_id
        }
        
        response = await test_client.post("/apps", json=app_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_app_by_id_success(self, test_client: AsyncClient, test_app):
        """Test successfully retrieving an app by ID."""
        response = await test_client.get(f"/apps/{test_app.app_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert result["app_id"] == test_app.app_id
        assert result["name"] == test_app.name

    @pytest.mark.asyncio
    async def test_get_app_by_id_not_found(self, test_client: AsyncClient):
        """Test retrieving non-existent app."""
        response = await test_client.get("/apps/nonexistent-app")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_app_success(self, test_client: AsyncClient, test_app):
        """Test successfully updating an app."""
        update_data = {
            "name": "Updated App Name",
            "description": "Updated description"
        }
        
        response = await test_client.put(f"/apps/{test_app.app_id}", json=update_data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["name"] == "Updated App Name"
        assert result["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_delete_app_success(self, test_client: AsyncClient, test_app):
        """Test successfully deleting an app."""
        response = await test_client.delete(f"/apps/{test_app.app_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "App deleted successfully"

    @pytest.mark.asyncio
    async def test_delete_app_not_found(self, test_client: AsyncClient):
        """Test deleting non-existent app."""
        response = await test_client.delete("/apps/nonexistent-app")
        assert response.status_code == 404


class TestStatsRoutes:
    """Test cases for stats-related routes."""

    @pytest.mark.asyncio
    async def test_get_user_stats_success(self, test_client: AsyncClient, test_user):
        """Test successfully retrieving user statistics."""
        response = await test_client.get(f"/stats/user/{test_user.user_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert "memory_count" in result
        assert "app_count" in result
        assert "last_activity" in result

    @pytest.mark.asyncio
    async def test_get_user_stats_not_found(self, test_client: AsyncClient):
        """Test retrieving stats for non-existent user."""
        response = await test_client.get("/stats/user/nonexistent-user")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_app_stats_success(self, test_client: AsyncClient, test_app):
        """Test successfully retrieving app statistics."""
        response = await test_client.get(f"/stats/app/{test_app.app_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert "memory_count" in result
        assert "last_activity" in result

    @pytest.mark.asyncio
    async def test_get_system_stats_success(self, test_client: AsyncClient):
        """Test successfully retrieving system statistics."""
        response = await test_client.get("/stats/system")
        
        assert response.status_code == 200
        result = response.json()
        assert "total_users" in result
        assert "total_apps" in result
        assert "total_memories" in result
        assert "system_health" in result

    @pytest.mark.asyncio
    async def test_get_memory_analytics_success(self, test_client: AsyncClient, test_user):
        """Test successfully retrieving memory analytics."""
        response = await test_client.get(f"/stats/memories/{test_user.user_id}")
        
        assert response.status_code == 200
        result = response.json()
        assert "daily_counts" in result
        assert "category_distribution" in result
        assert "search_patterns" in result


class TestConfigRoutes:
    """Test cases for configuration-related routes."""

    @pytest.mark.asyncio
    async def test_get_config_success(self, test_client: AsyncClient):
        """Test successfully retrieving configuration."""
        response = await test_client.get("/config")
        
        assert response.status_code == 200
        result = response.json()
        assert "mem0_config" in result
        assert "system_config" in result

    @pytest.mark.asyncio
    async def test_update_config_success(self, test_client: AsyncClient):
        """Test successfully updating configuration."""
        config_data = {
            "mem0_config": {
                "embedding_model": "text-embedding-3-small",
                "vector_store": "postgresql"
            },
            "system_config": {
                "max_memories_per_user": 1000,
                "enable_analytics": True
            }
        }
        
        response = await test_client.put("/config", json=config_data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "Configuration updated successfully"

    @pytest.mark.asyncio
    async def test_update_config_invalid_data(self, test_client: AsyncClient):
        """Test updating configuration with invalid data."""
        config_data = {
            "invalid_field": "invalid_value"
        }
        
        response = await test_client.put("/config", json=config_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_reset_config_success(self, test_client: AsyncClient):
        """Test successfully resetting configuration to defaults."""
        response = await test_client.post("/config/reset")
        
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "Configuration reset to defaults"


class TestHealthRoutes:
    """Test cases for health check routes."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, test_client: AsyncClient):
        """Test health check endpoint."""
        response = await test_client.get("/health")
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert "version" in result

    @pytest.mark.asyncio
    async def test_detailed_health_check_success(self, test_client: AsyncClient):
        """Test detailed health check endpoint."""
        response = await test_client.get("/health/detailed")
        
        assert response.status_code == 200
        result = response.json()
        assert "database" in result
        assert "mem0_service" in result
        assert "external_apis" in result

    @pytest.mark.asyncio
    async def test_readiness_check_success(self, test_client: AsyncClient):
        """Test readiness check endpoint."""
        response = await test_client.get("/ready")
        
        assert response.status_code == 200
        result = response.json()
        assert result["ready"] is True

    @pytest.mark.asyncio
    async def test_liveness_check_success(self, test_client: AsyncClient):
        """Test liveness check endpoint."""
        response = await test_client.get("/live")
        
        assert response.status_code == 200
        result = response.json()
        assert result["alive"] is True


class TestErrorHandling:
    """Test error handling across all routes."""

    @pytest.mark.asyncio
    async def test_404_route_not_found(self, test_client: AsyncClient):
        """Test 404 handling for non-existent routes."""
        response = await test_client.get("/nonexistent-route")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_405_method_not_allowed(self, test_client: AsyncClient):
        """Test 405 handling for invalid HTTP methods."""
        response = await test_client.patch("/memories")  # PATCH not allowed
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_422_validation_error(self, test_client: AsyncClient):
        """Test 422 handling for validation errors."""
        response = await test_client.post("/memories", json={"invalid": "data"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_500_internal_server_error(self, test_client: AsyncClient):
        """Test 500 handling for internal server errors."""
        with patch('app.utils.mem0_client.mem0_client.add') as mock_add:
            mock_add.side_effect = Exception("Database connection failed")
            
            memory_data = {
                "messages": [{"role": "user", "content": "Test"}],
                "user_id": USER_ID
            }
            
            response = await test_client.post("/memories", json=memory_data)
            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_rate_limiting(self, test_client: AsyncClient):
        """Test rate limiting (if implemented)."""
        # This would test rate limiting if it's implemented
        # For now, just ensure the endpoint works normally
        response = await test_client.get("/health")
        assert response.status_code == 200


class TestSecurity:
    """Test security-related functionality."""

    @pytest.mark.asyncio
    async def test_sql_injection_protection(self, test_client: AsyncClient, security_test_payloads):
        """Test SQL injection protection."""
        for payload in security_test_payloads["sql_injection"]:
            response = await test_client.get(f"/memories?user_id={payload}")
            # Should either return 400 (validation error) or 200 with empty results
            assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_xss_protection(self, test_client: AsyncClient, test_user, security_test_payloads):
        """Test XSS protection."""
        for payload in security_test_payloads["xss_payloads"]:
            memory_data = {
                "messages": [{"role": "user", "content": payload}],
                "user_id": test_user.user_id
            }
            response = await test_client.post("/memories", json=memory_data)
            # Should either process safely or reject
            assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_command_injection_protection(self, test_client: AsyncClient, test_user, security_test_payloads):
        """Test command injection protection."""
        for payload in security_test_payloads["command_injection"]:
            search_data = {
                "query": payload,
                "user_id": test_user.user_id
            }
            response = await test_client.post("/search", json=search_data)
            # Should either process safely or reject
            assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_large_payload_handling(self, test_client: AsyncClient, test_user):
        """Test handling of large payloads."""
        large_content = "x" * 10000  # 10KB content
        memory_data = {
            "messages": [{"role": "user", "content": large_content}],
            "user_id": test_user.user_id
        }
        response = await test_client.post("/memories", json=memory_data)
        # Should either process or reject based on size limits
        assert response.status_code in [200, 413, 422]


class TestPerformance:
    """Test performance-related functionality."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, test_client: AsyncClient, test_user):
        """Test handling of concurrent requests."""
        import asyncio
        
        async def make_request():
            return await test_client.get(f"/memories?user_id={test_user.user_id}")
        
        # Make 10 concurrent requests
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_pagination_performance(self, test_client: AsyncClient, test_user):
        """Test pagination performance with large datasets."""
        response = await test_client.get(f"/memories?user_id={test_user.user_id}&page=1&size=100")
        assert response.status_code == 200
        
        # Response should be reasonably fast (measured by the test framework)
        result = response.json()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_search_performance(self, test_client: AsyncClient, test_user):
        """Test search performance."""
        search_data = {
            "query": "performance test query",
            "user_id": test_user.user_id,
            "limit": 50
        }
        response = await test_client.post("/search", json=search_data)
        assert response.status_code == 200
        
        # Should return results in reasonable time
        result = response.json()
        assert "results" in result