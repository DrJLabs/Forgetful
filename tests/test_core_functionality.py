#!/usr/bin/env python3
"""
Core Functionality Tests - Demonstrates the established testing framework
"""

import pytest
import unittest
import json
import time
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import test utilities from our established framework
import sys
sys.path.append(str(Path(__file__).parent.parent / "shared"))

from test_utils import (
    TestConfig,
    TestEnvironment,
    DataFactory,
    MockServices,
    TestAssertions,
    PerformanceTracker,
    async_test,
    performance_test
)


class TestCoreMemoryOperations(unittest.TestCase):
    """Test core memory operations using established framework"""

    def setUp(self):
        """Set up test environment"""
        self.config = TestConfig()
        self.test_env = TestEnvironment(self.config)
        self.test_env.setup()
        self.data_factory = DataFactory()
        self.assertions = TestAssertions()

    def tearDown(self):
        """Clean up test environment"""
        self.test_env.teardown()

    @pytest.mark.unit
    def test_memory_data_creation(self):
        """Test memory data creation using data factory"""
        # Create test memory data
        memory_data = self.data_factory.create_memory_data(
            user_id="test_user_123",
            content="This is a test memory for unit testing",
            metadata={"test_type": "unit", "priority": "high"}
        )

        # Validate structure using custom assertions
        expected_keys = ["user_id", "content", "metadata", "created_at"]
        self.assertions.assert_json_structure(memory_data, expected_keys)

        # Validate content
        self.assertEqual(memory_data["user_id"], "test_user_123")
        self.assertEqual(memory_data["content"], "This is a test memory for unit testing")
        self.assertEqual(memory_data["metadata"]["test_type"], "unit")
        
        # Validate datetime format
        self.assertions.assert_valid_datetime(memory_data["created_at"])

    @pytest.mark.unit
    def test_user_data_creation(self):
        """Test user data creation and validation"""
        # Create user data with random elements
        user_data = self.data_factory.create_user_data(
            name="Test User",
            email="test@example.com"
        )

        # Validate structure
        expected_keys = ["user_id", "name", "email", "created_at"]
        self.assertions.assert_json_structure(user_data, expected_keys)

        # Validate specific values
        self.assertEqual(user_data["name"], "Test User")
        self.assertEqual(user_data["email"], "test@example.com")
        
        # Validate generated UUID
        self.assertions.assert_valid_uuid(user_data["user_id"])

    @pytest.mark.unit
    def test_batch_data_creation(self):
        """Test batch data creation capabilities"""
        # Create batch of memory data
        batch_size = 5
        batch_data = self.data_factory.create_batch_data(
            self.data_factory.create_memory_data,
            count=batch_size,
            user_id="batch_test_user"
        )

        # Validate batch
        self.assertEqual(len(batch_data), batch_size)
        
        # Validate each item
        for item in batch_data:
            self.assertEqual(item["user_id"], "batch_test_user")
            self.assertions.assert_valid_datetime(item["created_at"])

    @pytest.mark.unit
    def test_message_data_creation(self):
        """Test message data creation for conversation contexts"""
        # Create different types of messages
        user_message = self.data_factory.create_message_data(
            role="user",
            content="Hello, I need help with memory management"
        )
        
        assistant_message = self.data_factory.create_message_data(
            role="assistant",
            content="I can help you with memory management. What specific area?"
        )

        # Validate messages
        self.assertEqual(user_message["role"], "user")
        self.assertEqual(assistant_message["role"], "assistant")
        
        # Both should have timestamps
        self.assertions.assert_valid_datetime(user_message["timestamp"])
        self.assertions.assert_valid_datetime(assistant_message["timestamp"])


class TestPerformanceOperations(unittest.TestCase):
    """Test performance monitoring using established framework"""

    def setUp(self):
        """Set up performance tracking"""
        self.performance_tracker = PerformanceTracker()

    @pytest.mark.performance
    @performance_test(max_duration=1.0, max_memory_mb=10.0)
    def test_memory_processing_performance(self):
        """Test memory processing performance with constraints"""
        # Start tracking
        self.performance_tracker.start_timer("memory_processing")

        # Simulate memory processing work
        data_batch = []
        for i in range(1000):
            memory_data = {
                "id": str(uuid.uuid4()),
                "content": f"Memory content {i} " * 10,  # Some content
                "metadata": {"index": i, "batch": "performance_test"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            data_batch.append(memory_data)

        # Simulate processing
        processed_count = 0
        for item in data_batch:
            # Simple processing simulation
            content_length = len(item["content"])
            if content_length > 0:
                processed_count += 1

        # End tracking
        self.performance_tracker.end_timer("memory_processing")

        # Validate results
        self.assertEqual(processed_count, 1000)
        
        # Get performance metrics
        metrics = self.performance_tracker.get_metrics("memory_processing")
        self.assertIn("duration", metrics)
        self.assertIn("memory_delta", metrics)
        
        # The @performance_test decorator will assert performance constraints

    @pytest.mark.performance
    def test_concurrent_memory_operations(self):
        """Test concurrent memory operations performance"""
        self.performance_tracker.start_timer("concurrent_ops")

        # Simulate concurrent operations
        operations = []
        for i in range(100):
            operation = {
                "type": "create" if i % 2 == 0 else "update",
                "data": DataFactory.create_memory_data(user_id=f"user_{i % 10}"),
                "timestamp": time.time()
            }
            operations.append(operation)

        # Process operations
        results = []
        for op in operations:
            result = {
                "operation_id": str(uuid.uuid4()),
                "type": op["type"],
                "status": "success",
                "duration": 0.001  # Simulated processing time
            }
            results.append(result)

        self.performance_tracker.end_timer("concurrent_ops")

        # Validate results
        self.assertEqual(len(results), 100)
        
        # Check performance metrics
        metrics = self.performance_tracker.get_metrics("concurrent_ops")
        self.assertLess(metrics["duration"], 2.0)  # Should complete within 2 seconds


class TestMockServices(unittest.TestCase):
    """Test mock services integration"""

    def setUp(self):
        """Set up mock services"""
        self.mock_services = MockServices()

    @pytest.mark.unit
    def test_mock_openai_integration(self):
        """Test OpenAI mock service integration"""
        # Setup OpenAI mock
        openai_mock = self.mock_services.setup_openai_mock()
        
        # Test embeddings mock
        embedding_response = openai_mock.embeddings.create(
            model="text-embedding-ada-002",
            input="Test content for embedding"
        )
        
        # Validate mock response
        self.assertIsNotNone(embedding_response)
        self.assertEqual(len(embedding_response.data[0].embedding), 1536)

        # Test chat completions mock
        chat_response = openai_mock.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        # Validate mock response
        self.assertIsNotNone(chat_response)
        self.assertEqual(chat_response.choices[0].message.content, "Test response")

    @pytest.mark.unit
    def test_mock_database_integration(self):
        """Test database mock service integration"""
        # Setup database mocks
        postgres_mock = self.mock_services.setup_postgres_mock()
        redis_mock = self.mock_services.setup_redis_mock()

        # Test PostgreSQL mock
        connection = postgres_mock.connect()
        self.assertIsNotNone(connection)

        cursor = postgres_mock.cursor()
        cursor.fetchall.return_value = [{"id": 1, "content": "test"}]
        
        # Test Redis mock
        redis_mock.set("test_key", "test_value")
        redis_mock.get.return_value = "test_value"
        
        result = redis_mock.get("test_key")
        self.assertEqual(result, "test_value")


class TestCustomAssertions(unittest.TestCase):
    """Test custom assertions functionality"""

    def setUp(self):
        """Set up test assertions"""
        self.assertions = TestAssertions()

    @pytest.mark.unit
    def test_uuid_validation(self):
        """Test UUID validation assertions"""
        # Valid UUID
        valid_uuid = str(uuid.uuid4())
        self.assertions.assert_valid_uuid(valid_uuid)

        # Invalid UUID should raise AssertionError
        with self.assertRaises(AssertionError):
            self.assertions.assert_valid_uuid("not-a-valid-uuid")

    @pytest.mark.unit
    def test_datetime_validation(self):
        """Test datetime validation assertions"""
        # Valid datetime
        valid_datetime = datetime.now(timezone.utc).isoformat()
        self.assertions.assert_valid_datetime(valid_datetime)

        # Invalid datetime should raise AssertionError
        with self.assertRaises(AssertionError):
            self.assertions.assert_valid_datetime("not-a-valid-datetime")

    @pytest.mark.unit
    def test_json_structure_validation(self):
        """Test JSON structure validation"""
        # Valid structure
        test_data = {
            "id": "123",
            "name": "Test",
            "email": "test@example.com",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        expected_keys = ["id", "name", "email", "created_at"]
        self.assertions.assert_json_structure(test_data, expected_keys)

        # Missing keys should raise AssertionError
        incomplete_data = {"id": "123", "name": "Test"}
        with self.assertRaises(AssertionError):
            self.assertions.assert_json_structure(incomplete_data, expected_keys)


class TestAsyncOperations(unittest.TestCase):
    """Test async operations using established framework"""

    @pytest.mark.async_test
    @async_test
    async def test_async_memory_processing(self):
        """Test async memory processing operations"""
        import asyncio
        
        # Simulate async memory operations
        async def process_memory_item(item):
            # Simulate async processing
            await asyncio.sleep(0.01)
            return {
                "id": item["id"],
                "processed": True,
                "content_length": len(item["content"])
            }

        # Create test data
        test_items = [
            {"id": str(uuid.uuid4()), "content": f"Test content {i}"}
            for i in range(10)
        ]

        # Process items asynchronously
        results = await asyncio.gather(
            *[process_memory_item(item) for item in test_items]
        )

        # Validate results
        self.assertEqual(len(results), 10)
        for result in results:
            self.assertTrue(result["processed"])
            self.assertGreater(result["content_length"], 0)


if __name__ == "__main__":
    # Run tests with pytest markers
    pytest.main([__file__, "-v", "--tb=short"])