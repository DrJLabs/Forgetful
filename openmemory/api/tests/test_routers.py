"""
Unit tests for API router endpoints
"""

import pytest
from datetime import datetime, UTC
from uuid import uuid4
from unittest.mock import MagicMock

from httpx import AsyncClient
from fastapi import status

from conftest import TestDataFactory


@pytest.mark.unit
class TestMemoriesRouter:
    """Test memories router endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_memories_success(self, test_client: AsyncClient, test_user, mock_memory_client):
        """Test successful memory listing"""
        response = await test_client.get(
            "/api/v1/memories/",
            params={"user_id": test_user.user_id}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert data["total"] >= 0
    
    @pytest.mark.asyncio
    async def test_list_memories_with_search(self, test_client: AsyncClient, test_user, mock_memory_client):
        """Test memory listing with search query"""
        response = await test_client.get(
            "/api/v1/memories/",
            params={
                "user_id": test_user.user_id,
                "search_query": "test"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        
        # Verify search was called on mock client
        mock_memory_client.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_memories_with_pagination(self, test_client: AsyncClient, test_user, mock_memory_client):
        """Test memory listing with pagination"""
        response = await test_client.get(
            "/api/v1/memories/",
            params={
                "user_id": test_user.user_id,
                "page": 1,
                "size": 10
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 10
    
    @pytest.mark.asyncio
    async def test_create_memory_success(self, test_client: AsyncClient, test_user, mock_memory_client):
        """Test successful memory creation"""
        memory_data = TestDataFactory.create_memory_data(user_id=test_user.user_id)
        
        response = await test_client.post(
            "/api/v1/memories/",
            json=memory_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "results" in data
        
        # Verify add was called on mock client
        mock_memory_client.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_memory_with_metadata(self, test_client: AsyncClient, test_user, mock_memory_client):
        """Test memory creation with metadata"""
        memory_data = TestDataFactory.create_memory_data(user_id=test_user.user_id)
        memory_data["metadata"] = {"category": "test", "importance": "high"}
        
        response = await test_client.post(
            "/api/v1/memories/",
            json=memory_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify metadata was included in the call
        args, kwargs = mock_memory_client.add.call_args
        assert kwargs["metadata"]["category"] == "test"
        assert kwargs["metadata"]["importance"] == "high"
    
    @pytest.mark.asyncio
    async def test_create_memory_client_error(self, test_client: AsyncClient, test_user, mock_memory_client):
        """Test memory creation when client has error"""
        # Mock client error
        mock_memory_client.add.side_effect = Exception("Client error")
        
        memory_data = TestDataFactory.create_memory_data(user_id=test_user.user_id)
        
        response = await test_client.post(
            "/api/v1/memories/",
            json=memory_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "error" in data
        assert "Client error" in data["error"]
    
    @pytest.mark.asyncio
    async def test_get_memory_success(self, test_client: AsyncClient, mock_memory_client):
        """Test successful memory retrieval"""
        memory_id = "test_memory_id"
        
        response = await test_client.get(f"/api/v1/memories/{memory_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "id" in data
        assert "content" in data
        assert "text" in data  # Compatibility field
        
        # Verify get was called on mock client
        mock_memory_client.get.assert_called_once_with(memory_id)
    
    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, test_client: AsyncClient, mock_memory_client):
        """Test memory retrieval when not found"""
        mock_memory_client.get.return_value = None
        
        response = await test_client.get("/api/v1/memories/nonexistent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_get_memory_client_error(self, test_client: AsyncClient, mock_memory_client):
        """Test memory retrieval when client has error"""
        mock_memory_client.get.side_effect = Exception("Client error")
        
        response = await test_client.get("/api/v1/memories/test_id")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    @pytest.mark.asyncio
    async def test_search_memories_success(self, test_client: AsyncClient, test_user, mock_memory_client):
        """Test successful memory search"""
        search_data = {
            "user_id": test_user.user_id,
            "query": "test query",
            "limit": 10
        }
        
        response = await test_client.post(
            "/api/v1/memories/search",
            json=search_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "results" in data
        
        # Verify search was called
        mock_memory_client.search.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_categories_empty(self, test_client: AsyncClient, test_user):
        """Test getting categories (returns empty for mem0)"""
        response = await test_client.get(
            "/api/v1/memories/categories",
            params={"user_id": test_user.user_id}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["categories"] == []
        assert data["total"] == 0


@pytest.mark.unit
class TestAppsRouter:
    """Test apps router endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_apps_success(self, test_client: AsyncClient, test_app):
        """Test successful app listing"""
        response = await test_client.get("/api/v1/apps/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "apps" in data
        assert "total" in data
        assert data["total"] >= 0
    
    @pytest.mark.asyncio
    async def test_list_apps_with_filters(self, test_client: AsyncClient, test_app):
        """Test app listing with filters"""
        response = await test_client.get(
            "/api/v1/apps/",
            params={
                "name": "test",
                "is_active": True,
                "sort_by": "name",
                "sort_direction": "asc"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "apps" in data
    
    @pytest.mark.asyncio
    async def test_list_apps_with_pagination(self, test_client: AsyncClient, test_app):
        """Test app listing with pagination"""
        response = await test_client.get(
            "/api/v1/apps/",
            params={
                "page": 1,
                "page_size": 5
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5
    
    @pytest.mark.asyncio
    async def test_get_app_memories_success(self, test_client: AsyncClient, test_app):
        """Test getting memories for an app"""
        response = await test_client.get(f"/api/v1/apps/{test_app.id}/memories")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "memories" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_get_app_memories_not_found(self, test_client: AsyncClient):
        """Test getting memories for non-existent app"""
        fake_app_id = uuid4()
        response = await test_client.get(f"/api/v1/apps/{fake_app_id}/memories")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_get_app_memories_with_pagination(self, test_client: AsyncClient, test_app):
        """Test getting app memories with pagination"""
        response = await test_client.get(
            f"/api/v1/apps/{test_app.id}/memories",
            params={"page": 1, "page_size": 10}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10


@pytest.mark.unit
class TestStatsRouter:
    """Test stats router endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_profile_success(self, test_client: AsyncClient, test_user, mock_memory_client):
        """Test successful profile retrieval"""
        response = await test_client.get(
            "/api/v1/stats/",
            params={"user_id": test_user.user_id}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_memories" in data
        assert "total_apps" in data
        assert "apps" in data
        assert isinstance(data["total_memories"], int)
        assert isinstance(data["total_apps"], int)
    
    @pytest.mark.asyncio
    async def test_get_profile_new_user(self, test_client: AsyncClient, mock_memory_client):
        """Test profile retrieval for new user (should create user)"""
        new_user_id = "new_user_123"
        
        response = await test_client.get(
            "/api/v1/stats/",
            params={"user_id": new_user_id}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_memories" in data
        assert "total_apps" in data
    
    @pytest.mark.asyncio
    async def test_get_profile_memory_client_error(self, test_client: AsyncClient, test_user, mock_memory_client):
        """Test profile retrieval when memory client has error"""
        mock_memory_client.get_all.side_effect = Exception("Client error")
        
        response = await test_client.get(
            "/api/v1/stats/",
            params={"user_id": test_user.user_id}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_memories"] == 0  # Should default to 0 on error


@pytest.mark.unit
class TestConfigRouter:
    """Test config router endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_configuration_success(self, test_client: AsyncClient):
        """Test successful configuration retrieval"""
        response = await test_client.get("/api/v1/config/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Configuration structure depends on implementation
        assert isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_update_configuration_success(self, test_client: AsyncClient):
        """Test successful configuration update"""
        config_data = {
            "llm": {
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 1000
            }
        }
        
        response = await test_client.put(
            "/api/v1/config/",
            json=config_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_get_openmemory_configuration(self, test_client: AsyncClient):
        """Test getting OpenMemory specific configuration"""
        response = await test_client.get("/api/v1/config/openmemory")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_update_openmemory_configuration(self, test_client: AsyncClient):
        """Test updating OpenMemory specific configuration"""
        config_data = {
            "enable_logging": True,
            "max_memory_size": 1000
        }
        
        response = await test_client.put(
            "/api/v1/config/openmemory",
            json=config_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling across all endpoints"""
    
    @pytest.mark.asyncio
    async def test_invalid_json_request(self, test_client: AsyncClient):
        """Test handling of invalid JSON in requests"""
        response = await test_client.post(
            "/api/v1/memories/",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self, test_client: AsyncClient):
        """Test handling of missing required fields"""
        response = await test_client.post(
            "/api/v1/memories/",
            json={"text": "Test"}  # Missing user_id
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_invalid_uuid_format(self, test_client: AsyncClient):
        """Test handling of invalid UUID format"""
        response = await test_client.get("/api/v1/memories/invalid-uuid")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_nonexistent_endpoint(self, test_client: AsyncClient):
        """Test handling of non-existent endpoints"""
        response = await test_client.get("/api/v1/nonexistent")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.unit
class TestValidation:
    """Test input validation"""
    
    @pytest.mark.asyncio
    async def test_memory_creation_validation(self, test_client: AsyncClient):
        """Test memory creation input validation"""
        # Test empty text
        response = await test_client.post(
            "/api/v1/memories/",
            json={"user_id": "test", "text": "", "app": "test"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_pagination_validation(self, test_client: AsyncClient, test_user):
        """Test pagination parameter validation"""
        # Test negative page number
        response = await test_client.get(
            "/api/v1/memories/",
            params={"user_id": test_user.user_id, "page": -1}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test zero page size
        response = await test_client.get(
            "/api/v1/memories/",
            params={"user_id": test_user.user_id, "size": 0}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_search_query_validation(self, test_client: AsyncClient, test_user):
        """Test search query validation"""
        # Test empty search query
        response = await test_client.get(
            "/api/v1/memories/",
            params={"user_id": test_user.user_id, "search_query": ""}
        )
        
        # Should still work but return all results
        assert response.status_code == status.HTTP_200_OK 