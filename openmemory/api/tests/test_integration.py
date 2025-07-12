"""
Integration tests for OpenMemory API
Tests the integration between API, database, and external services
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from app.models import App, Memory, MemoryState, User
from conftest import TestDataFactory
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import text


@pytest.mark.integration
class TestMemoryLifecycle:
    """Test complete memory lifecycle integration"""

    @pytest.mark.asyncio
    async def test_complete_memory_workflow(
        self, test_client: AsyncClient, test_db_session, mock_memory_client
    ):
        """Test complete memory workflow from creation to deletion"""
        # Step 1: Create user and app through API
        user_data = TestDataFactory.create_user_data("workflow_user")
        app_data = TestDataFactory.create_app_data("workflow_app")

        # Create memory via API
        memory_data = TestDataFactory.create_memory_data(
            user_id=user_data["user_id"], app=app_data["name"]
        )

        # Create memory
        response = await test_client.post("/api/v1/memories/", json=memory_data)
        assert response.status_code == status.HTTP_200_OK
        memory_result = response.json()

        # Verify memory was created in mem0
        mock_memory_client.add.assert_called_once()

        # Step 2: List memories
        response = await test_client.get(
            "/api/v1/memories/", params={"user_id": user_data["user_id"]}
        )
        assert response.status_code == status.HTTP_200_OK
        memories = response.json()
        assert memories["total"] >= 0

        # Step 3: Search memories
        response = await test_client.get(
            "/api/v1/memories/",
            params={"user_id": user_data["user_id"], "search_query": "test"},
        )
        assert response.status_code == status.HTTP_200_OK
        search_results = response.json()
        assert "items" in search_results

        # Step 4: Get memory by ID
        mock_memory_client.get.return_value = {
            "id": "test_memory_id",
            "memory": memory_data["text"],
            "created_at": datetime.now(UTC).isoformat(),
            "user_id": user_data["user_id"],
            "metadata": memory_data["metadata"],
        }

        response = await test_client.get("/api/v1/memories/test_memory_id")
        assert response.status_code == status.HTTP_200_OK
        memory_detail = response.json()
        assert memory_detail["text"] == memory_data["text"]

        # Step 5: Get user statistics
        response = await test_client.get(
            "/api/v1/stats/", params={"user_id": user_data["user_id"]}
        )
        assert response.status_code == status.HTTP_200_OK
        stats = response.json()
        assert "total_memories" in stats
        assert "total_apps" in stats

    @pytest.mark.asyncio
    async def test_memory_with_categories_integration(
        self, test_client: AsyncClient, test_db_session, mock_memory_client
    ):
        """Test memory integration with categories"""
        # Create memory with specific metadata that would generate categories
        memory_data = TestDataFactory.create_memory_data("category_user")
        memory_data["metadata"] = {
            "category": "work",
            "priority": "high",
            "tags": ["project", "deadline"],
        }

        response = await test_client.post("/api/v1/memories/", json=memory_data)
        assert response.status_code == status.HTTP_200_OK

        # Verify add was called with correct metadata
        args, kwargs = mock_memory_client.add.call_args
        assert "metadata" in kwargs
        assert kwargs["metadata"]["category"] == "work"
        assert kwargs["metadata"]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_app_memory_relationship_integration(
        self, test_client: AsyncClient, test_db_session, mock_memory_client
    ):
        """Test integration between apps and memories"""
        # Create memories for different apps
        memory_data_1 = TestDataFactory.create_memory_data("app_test_user", "app_1")
        memory_data_2 = TestDataFactory.create_memory_data("app_test_user", "app_2")

        # Create memories
        await test_client.post("/api/v1/memories/", json=memory_data_1)
        await test_client.post("/api/v1/memories/", json=memory_data_2)

        # Get apps list
        response = await test_client.get("/api/v1/apps/")
        assert response.status_code == status.HTTP_200_OK
        apps = response.json()
        assert "apps" in apps

        # Find the created apps
        app_names = [app["name"] for app in apps["apps"]]
        assert "app_1" in app_names
        assert "app_2" in app_names


@pytest.mark.integration
class TestDatabaseIntegration:
    """Test database integration scenarios"""

    @pytest.mark.asyncio
    async def test_database_transaction_rollback(
        self, test_client: AsyncClient, test_db_session
    ):
        """Test database transaction rollback on error"""
        # Create a scenario that would cause a database error
        user = User(
            id=uuid4(),
            user_id="transaction_user",
            name="Test User",
            created_at=datetime.now(UTC),
        )
        test_db_session.add(user)
        test_db_session.commit()

        # Try to create another user with same user_id (should fail)
        duplicate_user = User(
            id=uuid4(),
            user_id="transaction_user",  # Duplicate
            name="Duplicate User",
            created_at=datetime.now(UTC),
        )
        test_db_session.add(duplicate_user)

        with pytest.raises(Exception):
            test_db_session.commit()

        # Session should be rolled back
        test_db_session.rollback()

        # Verify original user still exists
        existing_user = (
            test_db_session.query(User)
            .filter(User.user_id == "transaction_user")
            .first()
        )
        assert existing_user is not None
        assert existing_user.name == "Test User"

    @pytest.mark.asyncio
    async def test_database_connection_handling(
        self, test_client: AsyncClient, test_db_session
    ):
        """Test database connection handling"""
        # Execute a complex query to test connection
        result = test_db_session.execute(
            text("SELECT COUNT(*) as count FROM users")
        ).fetchone()

        assert result is not None
        assert result[0] >= 0  # Should have at least 0 users

    @pytest.mark.asyncio
    async def test_database_constraints(
        self, test_client: AsyncClient, test_db_session
    ):
        """Test database constraints are enforced"""
        # Create user
        user = User(
            id=uuid4(),
            user_id="constraint_user",
            name="Test User",
            created_at=datetime.now(UTC),
        )
        test_db_session.add(user)
        test_db_session.commit()

        # Create app
        app = App(
            id=uuid4(),
            name="constraint_app",
            owner_id=user.id,
            created_at=datetime.now(UTC),
        )
        test_db_session.add(app)
        test_db_session.commit()

        # Try to create memory with invalid foreign key
        invalid_memory = Memory(
            id=uuid4(),
            content="Test content",
            user_id=uuid4(),  # Non-existent user
            app_id=app.id,
            state=MemoryState.active,
            created_at=datetime.now(UTC),
        )
        test_db_session.add(invalid_memory)

        with pytest.raises(Exception):
            test_db_session.commit()


@pytest.mark.integration
class TestMemoryClientIntegration:
    """Test integration with memory client"""

    @pytest.mark.asyncio
    async def test_memory_client_error_handling(
        self, test_client: AsyncClient, test_db_session
    ):
        """Test handling of memory client errors"""
        with patch("app.utils.memory.get_memory_client") as mock_get_client:
            # Mock client that raises exception
            mock_client = MagicMock()
            mock_client.add.side_effect = Exception("Memory service unavailable")
            mock_get_client.return_value = mock_client

            memory_data = TestDataFactory.create_memory_data("error_user")

            response = await test_client.post("/api/v1/memories/", json=memory_data)

            # Should return error but not crash
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "error" in data
            assert "Memory service unavailable" in data["error"]

    @pytest.mark.asyncio
    async def test_memory_client_timeout_handling(
        self, test_client: AsyncClient, test_db_session
    ):
        """Test handling of memory client timeouts"""
        with patch("app.utils.memory.get_memory_client") as mock_get_client:
            # Mock client that times out
            mock_client = MagicMock()
            mock_client.add.side_effect = asyncio.TimeoutError("Request timeout")
            mock_get_client.return_value = mock_client

            memory_data = TestDataFactory.create_memory_data("timeout_user")

            response = await test_client.post("/api/v1/memories/", json=memory_data)

            # Should handle timeout gracefully
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "error" in data

    @pytest.mark.asyncio
    async def test_memory_client_reconnection(
        self, test_client: AsyncClient, test_db_session
    ):
        """Test memory client reconnection after failure"""
        with patch("app.utils.memory.get_memory_client") as mock_get_client:
            # First call fails, second succeeds
            mock_client = MagicMock()
            mock_client.add.side_effect = [
                Exception("Connection lost"),
                {"results": [{"id": "test_id", "memory": "Test memory"}]},
            ]
            mock_get_client.return_value = mock_client

            memory_data = TestDataFactory.create_memory_data("reconnect_user")

            # First request should fail
            response1 = await test_client.post("/api/v1/memories/", json=memory_data)
            assert response1.status_code == status.HTTP_200_OK
            data1 = response1.json()
            assert "error" in data1

            # Second request should succeed
            response2 = await test_client.post("/api/v1/memories/", json=memory_data)
            assert response2.status_code == status.HTTP_200_OK
            data2 = response2.json()
            assert "results" in data2


@pytest.mark.integration
class TestConfigurationIntegration:
    """Test configuration integration"""

    @pytest.mark.asyncio
    async def test_configuration_persistence(
        self, test_client: AsyncClient, test_db_session
    ):
        """Test configuration persistence across requests"""
        # Set configuration
        config_data = {
            "llm": {"model": "gpt-4", "temperature": 0.7, "max_tokens": 1000},
            "openmemory": {"enable_logging": True, "max_memory_size": 1000},
        }

        response = await test_client.put("/api/v1/config/", json=config_data)
        assert response.status_code == status.HTTP_200_OK

        # Get configuration
        response = await test_client.get("/api/v1/config/")
        assert response.status_code == status.HTTP_200_OK
        retrieved_config = response.json()

        # Verify configuration was persisted
        assert "llm" in retrieved_config
        assert retrieved_config["llm"]["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_openmemory_config_isolation(
        self, test_client: AsyncClient, test_db_session
    ):
        """Test OpenMemory configuration isolation"""
        # Set OpenMemory specific configuration
        openmemory_config = {
            "enable_logging": True,
            "max_memory_size": 2000,
            "debug_mode": True,
        }

        response = await test_client.put(
            "/api/v1/config/openmemory", json=openmemory_config
        )
        assert response.status_code == status.HTTP_200_OK

        # Get OpenMemory configuration
        response = await test_client.get("/api/v1/config/openmemory")
        assert response.status_code == status.HTTP_200_OK
        retrieved_config = response.json()

        # Verify configuration was set correctly
        assert retrieved_config["enable_logging"] is True
        assert retrieved_config["max_memory_size"] == 2000
        assert retrieved_config["debug_mode"] is True


@pytest.mark.integration
class TestPaginationIntegration:
    """Test pagination integration across endpoints"""

    @pytest.mark.asyncio
    async def test_memory_pagination_consistency(
        self, test_client: AsyncClient, test_db_session, mock_memory_client
    ):
        """Test pagination consistency across memory endpoints"""
        # Mock large dataset
        mock_memories = [
            {
                "id": f"mem_{i}",
                "memory": f"Memory {i}",
                "created_at": datetime.now(UTC).isoformat(),
            }
            for i in range(25)
        ]
        mock_memory_client.get_all.return_value = {"results": mock_memories}

        # Test different page sizes
        for page_size in [5, 10, 20]:
            response = await test_client.get(
                "/api/v1/memories/",
                params={"user_id": "pagination_user", "size": page_size},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["size"] == page_size
            assert len(data["items"]) <= page_size

    @pytest.mark.asyncio
    async def test_app_pagination_consistency(
        self, test_client: AsyncClient, test_db_session
    ):
        """Test pagination consistency for apps endpoint"""
        # Create multiple apps for testing
        user = User(
            id=uuid4(),
            user_id="app_pagination_user",
            name="Test User",
            created_at=datetime.now(UTC),
        )
        test_db_session.add(user)
        test_db_session.commit()

        # Create multiple apps
        for i in range(15):
            app = App(
                id=uuid4(),
                name=f"test_app_{i}",
                owner_id=user.id,
                created_at=datetime.now(UTC),
            )
            test_db_session.add(app)
        test_db_session.commit()

        # Test pagination
        response = await test_client.get(
            "/api/v1/apps/", params={"page": 1, "page_size": 10}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert len(data["apps"]) <= 10


@pytest.mark.integration
class TestErrorPropagation:
    """Test error propagation across service layers"""

    @pytest.mark.asyncio
    async def test_database_error_propagation(
        self, test_client: AsyncClient, test_db_session
    ):
        """Test database error propagation to API"""
        # Force a database error by closing the connection
        test_db_session.close()

        # Try to make a request that requires database
        response = await test_client.get("/api/v1/apps/")

        # Should handle the error gracefully
        # The exact status code depends on implementation
        assert response.status_code in [500, 503]

    @pytest.mark.asyncio
    async def test_validation_error_propagation(self, test_client: AsyncClient):
        """Test validation error propagation"""
        # Send invalid data
        invalid_data = {
            "user_id": "",  # Empty user_id
            "text": "",  # Empty text
            "app": "",  # Empty app
        }

        response = await test_client.post("/api/v1/memories/", json=invalid_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        error_data = response.json()
        assert "detail" in error_data
        # Should contain validation errors
        assert isinstance(error_data["detail"], list)


@pytest.mark.integration
class TestConcurrencyIntegration:
    """Test concurrent operations"""

    @pytest.mark.asyncio
    async def test_concurrent_memory_creation(
        self, test_client: AsyncClient, test_db_session, mock_memory_client
    ):
        """Test concurrent memory creation"""
        # Create multiple memories concurrently
        memory_data = TestDataFactory.create_memory_data("concurrent_user")

        # Create multiple concurrent requests
        tasks = []
        for i in range(5):
            task = test_client.post("/api/v1/memories/", json=memory_data)
            tasks.append(task)

        # Execute all requests concurrently
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK

        # Verify all calls were made to mock client
        assert mock_memory_client.add.call_count == 5

    @pytest.mark.asyncio
    async def test_concurrent_app_creation(
        self, test_client: AsyncClient, test_db_session, mock_memory_client
    ):
        """Test concurrent app creation through memory creation"""
        # Create memories with different apps concurrently
        tasks = []
        for i in range(3):
            memory_data = TestDataFactory.create_memory_data(
                "concurrent_user", f"concurrent_app_{i}"
            )
            task = test_client.post("/api/v1/memories/", json=memory_data)
            tasks.append(task)

        # Execute all requests concurrently
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK

        # Verify apps were created
        response = await test_client.get("/api/v1/apps/")
        assert response.status_code == status.HTTP_200_OK
        apps = response.json()

        app_names = [app["name"] for app in apps["apps"]]
        assert "concurrent_app_0" in app_names
        assert "concurrent_app_1" in app_names
        assert "concurrent_app_2" in app_names
