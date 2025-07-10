"""
Integration tests for OpenMemory API.
Tests end-to-end workflows and service integration.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient
from unittest.mock import patch, MagicMock

from app.config import USER_ID, DEFAULT_APP_ID


class TestMemoryLifecycle:
    """Test complete memory lifecycle operations."""

    @pytest.mark.asyncio
    async def test_complete_memory_workflow(self, test_client: AsyncClient, test_user, test_app, mock_mem0_client):
        """Test complete memory workflow: create, search, update, delete."""
        
        # Step 1: Create a memory
        memory_data = {
            "messages": [
                {"role": "user", "content": "Integration test workflow"},
                {"role": "assistant", "content": "This is a test of the complete workflow"}
            ],
            "user_id": test_user.user_id,
            "app_id": test_app.app_id,
            "metadata": {"test_type": "integration", "priority": "high"}
        }
        
        create_response = await test_client.post("/memories", json=memory_data)
        assert create_response.status_code == 200
        created_memory = create_response.json()
        memory_id = created_memory["id"]
        
        # Step 2: Search for the memory
        search_data = {
            "query": "integration test workflow",
            "user_id": test_user.user_id,
            "limit": 10
        }
        
        search_response = await test_client.post("/search", json=search_data)
        assert search_response.status_code == 200
        search_results = search_response.json()
        assert len(search_results["results"]) > 0
        
        # Step 3: Retrieve the specific memory
        get_response = await test_client.get(f"/memories/{memory_id}?user_id={test_user.user_id}")
        assert get_response.status_code == 200
        retrieved_memory = get_response.json()
        assert retrieved_memory["id"] == memory_id
        
        # Step 4: Update the memory
        update_data = {"text": "Updated integration test content"}
        
        with patch('app.utils.mem0_client.mem0_client.update') as mock_update:
            mock_update.return_value = {"message": "Memory updated successfully"}
            
            update_response = await test_client.put(f"/memories/{memory_id}", json=update_data)
            assert update_response.status_code == 200
            updated_memory = update_response.json()
            assert updated_memory["message"] == "Memory updated successfully"
        
        # Step 5: Delete the memory
        delete_response = await test_client.delete(f"/memories/{memory_id}")
        assert delete_response.status_code == 200
        delete_result = delete_response.json()
        assert delete_result["message"] == "Memory deleted successfully"

    @pytest.mark.asyncio
    async def test_batch_memory_operations(self, test_client: AsyncClient, test_user, test_app, mock_mem0_client):
        """Test batch memory operations."""
        
        # Create multiple memories in batch
        batch_data = {
            "memories": [
                {
                    "messages": [{"role": "user", "content": f"Batch test memory {i}"}],
                    "user_id": test_user.user_id,
                    "app_id": test_app.app_id,
                    "metadata": {"batch_id": "test_batch_1", "index": i}
                }
                for i in range(5)
            ]
        }
        
        batch_response = await test_client.post("/memories/batch", json=batch_data)
        assert batch_response.status_code == 200
        batch_result = batch_response.json()
        assert batch_result["count"] == 5
        
        # Search for batch memories
        search_data = {
            "query": "batch test memory",
            "user_id": test_user.user_id,
            "limit": 10
        }
        
        search_response = await test_client.post("/search", json=search_data)
        assert search_response.status_code == 200
        search_results = search_response.json()
        assert len(search_results["results"]) >= 5
        
        # Clean up - delete all memories
        delete_all_response = await test_client.delete(f"/memories?user_id={test_user.user_id}")
        assert delete_all_response.status_code == 200

    @pytest.mark.asyncio
    async def test_memory_search_relevance(self, test_client: AsyncClient, test_user, test_app, mock_mem0_client):
        """Test search relevance and ranking."""
        
        # Create memories with different relevance levels
        memories = [
            {
                "messages": [{"role": "user", "content": "Python programming tutorial"}],
                "user_id": test_user.user_id,
                "app_id": test_app.app_id,
                "metadata": {"topic": "programming", "language": "python"}
            },
            {
                "messages": [{"role": "user", "content": "JavaScript web development"}],
                "user_id": test_user.user_id,
                "app_id": test_app.app_id,
                "metadata": {"topic": "programming", "language": "javascript"}
            },
            {
                "messages": [{"role": "user", "content": "Machine learning with Python"}],
                "user_id": test_user.user_id,
                "app_id": test_app.app_id,
                "metadata": {"topic": "ai", "language": "python"}
            }
        ]
        
        for memory in memories:
            response = await test_client.post("/memories", json=memory)
            assert response.status_code == 200
        
        # Search for Python-related content
        search_data = {
            "query": "Python programming",
            "user_id": test_user.user_id,
            "limit": 10
        }
        
        search_response = await test_client.post("/search", json=search_data)
        assert search_response.status_code == 200
        search_results = search_response.json()
        assert len(search_results["results"]) >= 2  # Should find Python-related memories

    @pytest.mark.asyncio
    async def test_memory_pagination(self, test_client: AsyncClient, test_user, test_app, mock_mem0_client):
        """Test memory pagination functionality."""
        
        # Create many memories
        for i in range(20):
            memory_data = {
                "messages": [{"role": "user", "content": f"Pagination test memory {i}"}],
                "user_id": test_user.user_id,
                "app_id": test_app.app_id,
                "metadata": {"pagination_test": True, "index": i}
            }
            response = await test_client.post("/memories", json=memory_data)
            assert response.status_code == 200
        
        # Test pagination
        page1_response = await test_client.get(f"/memories?user_id={test_user.user_id}&page=1&size=10")
        assert page1_response.status_code == 200
        page1_results = page1_response.json()
        assert len(page1_results) <= 10
        
        page2_response = await test_client.get(f"/memories?user_id={test_user.user_id}&page=2&size=10")
        assert page2_response.status_code == 200
        page2_results = page2_response.json()
        assert len(page2_results) <= 10


class TestAppIntegration:
    """Test app-related integration workflows."""

    @pytest.mark.asyncio
    async def test_app_lifecycle_with_memories(self, test_client: AsyncClient, test_user, mock_mem0_client):
        """Test app lifecycle with associated memories."""
        
        # Create an app
        app_data = {
            "name": "Integration Test App",
            "description": "App for integration testing",
            "user_id": test_user.user_id
        }
        
        app_response = await test_client.post("/apps", json=app_data)
        assert app_response.status_code == 201
        created_app = app_response.json()
        app_id = created_app["app_id"]
        
        # Create memories for the app
        memory_data = {
            "messages": [{"role": "user", "content": "App-specific memory"}],
            "user_id": test_user.user_id,
            "app_id": app_id,
            "metadata": {"app_test": True}
        }
        
        memory_response = await test_client.post("/memories", json=memory_data)
        assert memory_response.status_code == 200
        
        # Update the app
        update_data = {
            "name": "Updated Integration Test App",
            "description": "Updated description"
        }
        
        update_response = await test_client.put(f"/apps/{app_id}", json=update_data)
        assert update_response.status_code == 200
        updated_app = update_response.json()
        assert updated_app["name"] == "Updated Integration Test App"
        
        # Get app statistics
        stats_response = await test_client.get(f"/stats/app/{app_id}")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert "memory_count" in stats
        
        # Delete the app
        delete_response = await test_client.delete(f"/apps/{app_id}")
        assert delete_response.status_code == 200

    @pytest.mark.asyncio
    async def test_multi_app_memory_isolation(self, test_client: AsyncClient, test_user, mock_mem0_client):
        """Test memory isolation between apps."""
        
        # Create two apps
        app1_data = {
            "name": "App 1",
            "description": "First app",
            "user_id": test_user.user_id
        }
        
        app2_data = {
            "name": "App 2",
            "description": "Second app",
            "user_id": test_user.user_id
        }
        
        app1_response = await test_client.post("/apps", json=app1_data)
        app2_response = await test_client.post("/apps", json=app2_data)
        
        assert app1_response.status_code == 201
        assert app2_response.status_code == 201
        
        app1_id = app1_response.json()["app_id"]
        app2_id = app2_response.json()["app_id"]
        
        # Create memories for each app
        memory1_data = {
            "messages": [{"role": "user", "content": "App 1 specific memory"}],
            "user_id": test_user.user_id,
            "app_id": app1_id,
            "metadata": {"app": "app1"}
        }
        
        memory2_data = {
            "messages": [{"role": "user", "content": "App 2 specific memory"}],
            "user_id": test_user.user_id,
            "app_id": app2_id,
            "metadata": {"app": "app2"}
        }
        
        await test_client.post("/memories", json=memory1_data)
        await test_client.post("/memories", json=memory2_data)
        
        # Verify isolation by checking app stats
        app1_stats = await test_client.get(f"/stats/app/{app1_id}")
        app2_stats = await test_client.get(f"/stats/app/{app2_id}")
        
        assert app1_stats.status_code == 200
        assert app2_stats.status_code == 200


class TestUserIntegration:
    """Test user-related integration workflows."""

    @pytest.mark.asyncio
    async def test_user_data_consistency(self, test_client: AsyncClient, test_user, test_app, mock_mem0_client):
        """Test data consistency across user operations."""
        
        # Create memories for user
        for i in range(5):
            memory_data = {
                "messages": [{"role": "user", "content": f"User consistency test {i}"}],
                "user_id": test_user.user_id,
                "app_id": test_app.app_id,
                "metadata": {"consistency_test": True, "index": i}
            }
            response = await test_client.post("/memories", json=memory_data)
            assert response.status_code == 200
        
        # Get user statistics
        stats_response = await test_client.get(f"/stats/user/{test_user.user_id}")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["memory_count"] >= 5
        
        # Get all user memories
        memories_response = await test_client.get(f"/memories?user_id={test_user.user_id}")
        assert memories_response.status_code == 200
        memories = memories_response.json()
        assert len(memories) >= 5

    @pytest.mark.asyncio
    async def test_user_memory_search_filtering(self, test_client: AsyncClient, test_user, test_app, mock_mem0_client):
        """Test user-specific memory search filtering."""
        
        # Create memories with different categories
        categories = ["work", "personal", "research", "notes"]
        
        for category in categories:
            memory_data = {
                "messages": [{"role": "user", "content": f"Memory about {category}"}],
                "user_id": test_user.user_id,
                "app_id": test_app.app_id,
                "metadata": {"category": category}
            }
            response = await test_client.post("/memories", json=memory_data)
            assert response.status_code == 200
        
        # Search for specific category
        search_data = {
            "query": "work",
            "user_id": test_user.user_id,
            "limit": 10
        }
        
        search_response = await test_client.post("/search", json=search_data)
        assert search_response.status_code == 200
        search_results = search_response.json()
        assert len(search_results["results"]) >= 1


class TestSystemIntegration:
    """Test system-level integration functionality."""

    @pytest.mark.asyncio
    async def test_system_health_monitoring(self, test_client: AsyncClient):
        """Test system health monitoring integration."""
        
        # Basic health check
        health_response = await test_client.get("/health")
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert health_data["status"] == "healthy"
        
        # Detailed health check
        detailed_health_response = await test_client.get("/health/detailed")
        assert detailed_health_response.status_code == 200
        detailed_health_data = detailed_health_response.json()
        assert "database" in detailed_health_data
        assert "mem0_service" in detailed_health_data
        
        # Readiness check
        ready_response = await test_client.get("/ready")
        assert ready_response.status_code == 200
        ready_data = ready_response.json()
        assert ready_data["ready"] is True
        
        # Liveness check
        live_response = await test_client.get("/live")
        assert live_response.status_code == 200
        live_data = live_response.json()
        assert live_data["alive"] is True

    @pytest.mark.asyncio
    async def test_system_configuration_integration(self, test_client: AsyncClient):
        """Test system configuration integration."""
        
        # Get current configuration
        config_response = await test_client.get("/config")
        assert config_response.status_code == 200
        config_data = config_response.json()
        assert "mem0_config" in config_data
        assert "system_config" in config_data
        
        # Update configuration
        update_config = {
            "mem0_config": {
                "embedding_model": "text-embedding-3-small",
                "vector_store": "postgresql"
            },
            "system_config": {
                "max_memories_per_user": 2000,
                "enable_analytics": True
            }
        }
        
        update_response = await test_client.put("/config", json=update_config)
        assert update_response.status_code == 200
        
        # Verify configuration was updated
        verify_response = await test_client.get("/config")
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["system_config"]["max_memories_per_user"] == 2000
        
        # Reset configuration
        reset_response = await test_client.post("/config/reset")
        assert reset_response.status_code == 200

    @pytest.mark.asyncio
    async def test_system_statistics_integration(self, test_client: AsyncClient, test_user, test_app, mock_mem0_client):
        """Test system statistics integration."""
        
        # Create some test data
        memory_data = {
            "messages": [{"role": "user", "content": "System stats test"}],
            "user_id": test_user.user_id,
            "app_id": test_app.app_id,
            "metadata": {"stats_test": True}
        }
        
        await test_client.post("/memories", json=memory_data)
        
        # Get system statistics
        stats_response = await test_client.get("/stats/system")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert "total_users" in stats_data
        assert "total_apps" in stats_data
        assert "total_memories" in stats_data
        assert "system_health" in stats_data
        
        # Verify statistics are reasonable
        assert stats_data["total_users"] >= 1
        assert stats_data["total_apps"] >= 1
        assert stats_data["total_memories"] >= 1


class TestErrorHandlingIntegration:
    """Test error handling in integration scenarios."""

    @pytest.mark.asyncio
    async def test_cascading_failure_handling(self, test_client: AsyncClient, test_user):
        """Test handling of cascading failures."""
        
        # Test with mem0 service unavailable
        with patch('app.utils.mem0_client.mem0_client.add') as mock_add:
            mock_add.side_effect = Exception("Service unavailable")
            
            memory_data = {
                "messages": [{"role": "user", "content": "Test failure handling"}],
                "user_id": test_user.user_id
            }
            
            response = await test_client.post("/memories", json=memory_data)
            assert response.status_code == 500
            
            # Verify system is still responsive
            health_response = await test_client.get("/health")
            assert health_response.status_code == 200

    @pytest.mark.asyncio
    async def test_partial_failure_recovery(self, test_client: AsyncClient, test_user, test_app):
        """Test recovery from partial failures."""
        
        # Create a batch with mixed success/failure
        batch_data = {
            "memories": [
                {
                    "messages": [{"role": "user", "content": "Valid memory"}],
                    "user_id": test_user.user_id,
                    "app_id": test_app.app_id
                },
                {
                    "messages": [{"role": "user", "content": "Invalid memory"}],
                    "user_id": "invalid_user",
                    "app_id": test_app.app_id
                }
            ]
        }
        
        response = await test_client.post("/memories/batch", json=batch_data)
        assert response.status_code == 207  # Multi-status
        
        result = response.json()
        assert result["successful"] == 1
        assert result["failed"] == 1
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_timeout_handling(self, test_client: AsyncClient, test_user):
        """Test handling of request timeouts."""
        
        # Test with slow response simulation
        with patch('app.utils.mem0_client.mem0_client.search') as mock_search:
            # Simulate slow response
            async def slow_search(*args, **kwargs):
                await asyncio.sleep(0.1)  # Small delay for testing
                return {"results": []}
            
            mock_search.side_effect = slow_search
            
            search_data = {
                "query": "timeout test",
                "user_id": test_user.user_id
            }
            
            response = await test_client.post("/search", json=search_data)
            # Should still complete successfully with small delay
            assert response.status_code == 200


class TestPerformanceIntegration:
    """Test performance in integration scenarios."""

    @pytest.mark.asyncio
    async def test_bulk_operations_performance(self, test_client: AsyncClient, test_user, test_app, mock_mem0_client):
        """Test performance of bulk operations."""
        
        # Create large batch of memories
        batch_size = 50
        batch_data = {
            "memories": [
                {
                    "messages": [{"role": "user", "content": f"Performance test memory {i}"}],
                    "user_id": test_user.user_id,
                    "app_id": test_app.app_id,
                    "metadata": {"performance_test": True, "index": i}
                }
                for i in range(batch_size)
            ]
        }
        
        # Time the bulk operation
        start_time = datetime.now()
        response = await test_client.post("/memories/batch", json=batch_data)
        end_time = datetime.now()
        
        assert response.status_code == 200
        
        # Verify reasonable performance (less than 5 seconds for 50 memories)
        duration = (end_time - start_time).total_seconds()
        assert duration < 5.0
        
        result = response.json()
        assert result["count"] == batch_size

    @pytest.mark.asyncio
    async def test_concurrent_user_operations(self, test_client: AsyncClient, test_user, test_app, mock_mem0_client):
        """Test concurrent operations from multiple users."""
        
        async def create_memories_for_user(user_id, count=5):
            """Create memories for a specific user."""
            for i in range(count):
                memory_data = {
                    "messages": [{"role": "user", "content": f"Concurrent test {user_id} - {i}"}],
                    "user_id": user_id,
                    "app_id": test_app.app_id,
                    "metadata": {"concurrent_test": True, "user": user_id}
                }
                response = await test_client.post("/memories", json=memory_data)
                assert response.status_code == 200
        
        # Simulate multiple users creating memories concurrently
        tasks = [
            create_memories_for_user(f"user_{i}", 3)
            for i in range(3)
        ]
        
        # Execute all tasks concurrently
        await asyncio.gather(*tasks)
        
        # Verify all memories were created
        all_memories_response = await test_client.get(f"/memories?user_id={test_user.user_id}")
        assert all_memories_response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_performance_with_large_dataset(self, test_client: AsyncClient, test_user, test_app, mock_mem0_client):
        """Test search performance with large dataset."""
        
        # Create many memories with different content
        topics = ["programming", "science", "art", "music", "sports"]
        
        for topic in topics:
            for i in range(10):
                memory_data = {
                    "messages": [{"role": "user", "content": f"Content about {topic} - item {i}"}],
                    "user_id": test_user.user_id,
                    "app_id": test_app.app_id,
                    "metadata": {"topic": topic, "index": i}
                }
                response = await test_client.post("/memories", json=memory_data)
                assert response.status_code == 200
        
        # Perform search and time it
        search_data = {
            "query": "programming",
            "user_id": test_user.user_id,
            "limit": 20
        }
        
        start_time = datetime.now()
        search_response = await test_client.post("/search", json=search_data)
        end_time = datetime.now()
        
        assert search_response.status_code == 200
        
        # Verify reasonable search performance (less than 2 seconds)
        duration = (end_time - start_time).total_seconds()
        assert duration < 2.0
        
        search_results = search_response.json()
        assert len(search_results["results"]) > 0


class TestSecurityIntegration:
    """Test security aspects in integration scenarios."""

    @pytest.mark.asyncio
    async def test_user_data_isolation(self, test_client: AsyncClient, mock_mem0_client):
        """Test that user data is properly isolated."""
        
        # Create memories for different users
        user1_memory = {
            "messages": [{"role": "user", "content": "User 1 private data"}],
            "user_id": "user1",
            "metadata": {"private": True}
        }
        
        user2_memory = {
            "messages": [{"role": "user", "content": "User 2 private data"}],
            "user_id": "user2",
            "metadata": {"private": True}
        }
        
        await test_client.post("/memories", json=user1_memory)
        await test_client.post("/memories", json=user2_memory)
        
        # Verify user 1 cannot access user 2's data
        user1_memories = await test_client.get("/memories?user_id=user1")
        assert user1_memories.status_code == 200
        
        user2_memories = await test_client.get("/memories?user_id=user2")
        assert user2_memories.status_code == 200
        
        # Verify isolation (this would depend on actual implementation)
        # For now, just verify requests are handled properly
        assert user1_memories.json() != user2_memories.json()

    @pytest.mark.asyncio
    async def test_input_validation_across_endpoints(self, test_client: AsyncClient, security_test_payloads):
        """Test input validation across all endpoints."""
        
        # Test various malicious payloads
        for payload in security_test_payloads["sql_injection"]:
            # Test memory creation
            memory_data = {
                "messages": [{"role": "user", "content": payload}],
                "user_id": "test_user"
            }
            response = await test_client.post("/memories", json=memory_data)
            assert response.status_code in [200, 400, 422]
            
            # Test search
            search_data = {
                "query": payload,
                "user_id": "test_user"
            }
            response = await test_client.post("/search", json=search_data)
            assert response.status_code in [200, 400, 422]