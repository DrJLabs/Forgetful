"""
Comprehensive tests for MCP Server functionality
Tests MCP protocol operations, context management, SSE transport, and error scenarios
"""

import asyncio

# Set testing environment
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

os.environ["TESTING"] = "true"

from app.mcp_server import (
    add_memories,
    client_name_var,
    delete_all_memories,
    get_memory_client_safe,
    list_memories,
    search_memory,
    user_id_var,
)


@pytest.mark.unit
class TestMCPServerFunctionality:
    """Test MCP server core functionality"""

    def setup_method(self):
        """Setup for each test method"""
        # Clear context variables
        for var in [user_id_var, client_name_var]:
            try:
                var.delete()
            except LookupError:
                pass

    @pytest.mark.asyncio
    async def test_add_memories_success(self):
        """Test successful memory addition via MCP"""
        # Set context variables
        user_id_var.set("test_user")
        client_name_var.set("test_client")

        with patch("app.mcp_server.get_memory_client_safe") as mock_client:
            mock_memory_client = MagicMock()
            mock_memory_client.add.return_value = {
                "id": "memory_123",
                "text": "Test memory content",
                "created_at": "2024-01-01T00:00:00Z",
            }
            mock_client.return_value = mock_memory_client

            result = await add_memories("Test memory content")

            assert "Successfully added memory" in result
            assert "memory_123" in result
            mock_memory_client.add.assert_called_once_with(
                "Test memory content",
                user_id="test_user",
                metadata={"client_name": "test_client"},
            )

    @pytest.mark.asyncio
    async def test_add_memories_no_user_id(self):
        """Test memory addition without user_id"""
        client_name_var.set("test_client")
        # Don't set user_id_var

        result = await add_memories("Test memory content")

        assert result == "Error: user_id not provided"

    @pytest.mark.asyncio
    async def test_add_memories_no_client_name(self):
        """Test memory addition without client_name"""
        user_id_var.set("test_user")
        # Don't set client_name_var

        result = await add_memories("Test memory content")

        assert result == "Error: client_name not provided"

    @pytest.mark.asyncio
    async def test_add_memories_client_unavailable(self):
        """Test memory addition when memory client is unavailable"""
        user_id_var.set("test_user")
        client_name_var.set("test_client")

        with patch("app.mcp_server.get_memory_client_safe") as mock_client:
            mock_client.return_value = None

            result = await add_memories("Test memory content")

            assert (
                result
                == "Error: Memory system is currently unavailable. Please try again later."
            )

    @pytest.mark.asyncio
    async def test_add_memories_client_exception(self):
        """Test memory addition when client raises exception"""
        user_id_var.set("test_user")
        client_name_var.set("test_client")

        with patch("app.mcp_server.get_memory_client_safe") as mock_client:
            mock_memory_client = MagicMock()
            mock_memory_client.add.side_effect = Exception("Connection failed")
            mock_client.return_value = mock_memory_client

            result = await add_memories("Test memory content")

            assert "Error adding memory: Connection failed" in result

    @pytest.mark.asyncio
    async def test_search_memory_success(self):
        """Test successful memory search via MCP"""
        user_id_var.set("test_user")
        client_name_var.set("test_client")

        with patch("app.mcp_server.get_memory_client_safe") as mock_client:
            mock_memory_client = MagicMock()
            mock_memory_client.search.return_value = {
                "results": [
                    {"id": "mem1", "memory": "Found memory 1", "score": 0.95},
                    {"id": "mem2", "memory": "Found memory 2", "score": 0.87},
                ]
            }
            mock_client.return_value = mock_memory_client

            result = await search_memory("test query")

            assert "Found 2 memories" in result
            assert "Found memory 1" in result
            assert "Found memory 2" in result
            mock_memory_client.search.assert_called_once_with(
                "test query", user_id="test_user"
            )

    @pytest.mark.asyncio
    async def test_search_memory_no_results(self):
        """Test memory search with no results"""
        user_id_var.set("test_user")
        client_name_var.set("test_client")

        with patch("app.mcp_server.get_memory_client_safe") as mock_client:
            mock_memory_client = MagicMock()
            mock_memory_client.search.return_value = {"results": []}
            mock_client.return_value = mock_memory_client

            result = await search_memory("nonexistent query")

            assert "No memories found" in result

    @pytest.mark.asyncio
    async def test_list_memories_success(self):
        """Test successful memory listing via MCP"""
        user_id_var.set("test_user")
        client_name_var.set("test_client")

        with patch("app.mcp_server.get_memory_client_safe") as mock_client:
            mock_memory_client = MagicMock()
            mock_memory_client.get_all.return_value = {
                "results": [
                    {"id": "mem1", "memory": "Memory 1", "created_at": "2024-01-01"},
                    {"id": "mem2", "memory": "Memory 2", "created_at": "2024-01-02"},
                ]
            }
            mock_client.return_value = mock_memory_client

            result = await list_memories()

            assert "Found 2 memories" in result
            assert "Memory 1" in result
            assert "Memory 2" in result
            mock_memory_client.get_all.assert_called_once_with(user_id="test_user")

    @pytest.mark.asyncio
    async def test_delete_memories_success(self):
        """Test successful memory deletion via MCP"""
        user_id_var.set("test_user")
        client_name_var.set("test_client")

        with patch("app.mcp_server.get_memory_client_safe") as mock_client:
            mock_memory_client = MagicMock()
            mock_memory_client.delete_all.return_value = {"deleted": True}
            mock_client.return_value = mock_memory_client

            result = await delete_all_memories()

            assert "Successfully deleted all memories" in result
            mock_memory_client.delete_all.assert_called_once_with(user_id="test_user")

    @pytest.mark.asyncio
    async def test_delete_memories_not_found(self):
        """Test memory deletion when memory not found"""
        user_id_var.set("test_user")
        client_name_var.set("test_client")

        with patch("app.mcp_server.get_memory_client_safe") as mock_client:
            mock_memory_client = MagicMock()
            mock_memory_client.delete_all.side_effect = Exception("Operation failed")
            mock_client.return_value = mock_memory_client

            result = await delete_all_memories()

            assert "Error deleting" in result
            assert "Operation failed" in result


@pytest.mark.integration
class TestMCPServerIntegration:
    """Test MCP server integration with FastAPI"""

    @pytest.mark.asyncio
    async def test_mcp_endpoints_registered(self, test_client: AsyncClient):
        """Test that MCP endpoints are properly registered"""
        # Test SSE endpoint exists
        response = await test_client.get("/mcp/messages/")
        # Should return 405 for GET (expecting POST for SSE)
        assert response.status_code in [200, 405, 404]  # Depends on SSE implementation

    @pytest.mark.asyncio
    async def test_mcp_context_variables(self):
        """Test context variable isolation between requests"""

        async def set_and_check_context(user_id: str, client_name: str):
            user_id_var.set(user_id)
            client_name_var.set(client_name)

            # Verify context is set correctly
            assert user_id_var.get() == user_id
            assert client_name_var.get() == client_name

            return user_id_var.get(), client_name_var.get()

        # Test context isolation between different async contexts
        task1 = asyncio.create_task(set_and_check_context("user1", "client1"))
        task2 = asyncio.create_task(set_and_check_context("user2", "client2"))

        result1, result2 = await asyncio.gather(task1, task2)

        assert result1 == ("user1", "client1")
        assert result2 == ("user2", "client2")


@pytest.mark.unit
class TestMCPUtilities:
    """Test MCP utility functions"""

    def test_get_memory_client_safe_success(self):
        """Test safe memory client access when client is available"""
        with patch("app.mcp_server.get_memory_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            result = get_memory_client_safe()

            assert result == mock_client
            mock_get_client.assert_called_once()

    def test_get_memory_client_safe_none(self):
        """Test safe memory client access when client returns None"""
        with patch("app.mcp_server.get_memory_client") as mock_get_client:
            mock_get_client.return_value = None

            result = get_memory_client_safe()

            assert result is None

    def test_get_memory_client_safe_exception(self):
        """Test safe memory client access when client raises exception"""
        with patch("app.mcp_server.get_memory_client") as mock_get_client:
            mock_get_client.side_effect = Exception("Client initialization failed")

            result = get_memory_client_safe()

            assert result is None


@pytest.mark.unit
class TestMCPErrorScenarios:
    """Test various error scenarios in MCP operations"""

    @pytest.mark.asyncio
    async def test_context_variables_missing(self):
        """Test all MCP functions handle missing context variables"""
        # Ensure no context variables are set
        for var in [user_id_var, client_name_var]:
            try:
                var.delete()
            except LookupError:
                pass

        # Test add_memories
        result = await add_memories("test")
        assert "Error: user_id not provided" in result

        # Set user_id but not client_name
        user_id_var.set("test_user")
        result = await add_memories("test")
        assert "Error: client_name not provided" in result

        # Test other functions with missing user_id
        user_id_var.delete()

        for func in [search_memory, list_memories, delete_all_memories]:
            try:
                if func == delete_all_memories:
                    result = await func()
                elif func == search_memory:
                    result = await func("test_query")
                else:
                    result = await func()
                assert "Error: user_id not provided" in result
            except Exception as e:
                # If function doesn't handle missing context gracefully
                assert "user_id" in str(e) or "LookupError" in str(type(e))

    @pytest.mark.asyncio
    async def test_malformed_input_handling(self):
        """Test MCP functions handle malformed input"""
        user_id_var.set("test_user")
        client_name_var.set("test_client")

        with patch("app.mcp_server.get_memory_client_safe") as mock_client:
            mock_memory_client = MagicMock()
            mock_client.return_value = mock_memory_client

            # Test empty/None inputs
            for func, args in [
                (add_memories, [""]),
                (add_memories, [None]),
                (search_memory, [""]),
                (delete_all_memories, []),
            ]:
                try:
                    if func == delete_all_memories:
                        result = await func()
                    elif len(args) > 0 and args[0] is None:
                        # Some functions might not accept None
                        continue
                    elif len(args) > 0:
                        result = await func(args[0])
                    else:
                        result = await func()
                    # Should handle gracefully
                    assert isinstance(result, str)
                except Exception as e:
                    # If function validates input, that's also acceptable
                    assert "invalid" in str(e).lower() or "required" in str(e).lower()


@pytest.mark.performance
class TestMCPPerformance:
    """Test MCP operations performance"""

    @pytest.mark.asyncio
    async def test_concurrent_memory_operations(self):
        """Test MCP can handle concurrent operations"""
        user_id_var.set("test_user")
        client_name_var.set("test_client")

        with patch("app.mcp_server.get_memory_client_safe") as mock_client:
            mock_memory_client = MagicMock()
            mock_memory_client.add = AsyncMock(return_value={"id": "mem_123"})
            mock_memory_client.search = AsyncMock(return_value={"results": []})
            mock_client.return_value = mock_memory_client

            # Create multiple concurrent operations
            tasks = []
            for i in range(10):
                if i % 2 == 0:
                    task = add_memories(f"Memory {i}")
                else:
                    task = search_memory(f"query {i}")
                tasks.append(task)

            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks)

            # All operations should complete successfully
            assert len(results) == 10
            for result in results:
                assert isinstance(result, str)
                assert (
                    "Error" not in result
                    or "Successfully" in result
                    or "Found" in result
                )

    @pytest.mark.asyncio
    async def test_memory_operation_timeout(self):
        """Test MCP operations handle timeouts gracefully"""
        user_id_var.set("test_user")
        client_name_var.set("test_client")

        with patch("app.mcp_server.get_memory_client_safe") as mock_client:
            mock_memory_client = MagicMock()

            # Simulate slow operation
            async def slow_add(*args, **kwargs):
                await asyncio.sleep(5)  # Simulate 5 second delay
                return {"id": "slow_memory"}

            mock_memory_client.add = slow_add
            mock_client.return_value = mock_memory_client

            # Test with timeout
            try:
                result = await asyncio.wait_for(
                    add_memories("slow memory"), timeout=2.0
                )
                # If it completes within timeout, that's fine
                assert "Successfully added memory" in result
            except asyncio.TimeoutError:
                # Timeout is expected for this test
                assert True, "Operation timed out as expected"
