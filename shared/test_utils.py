"""
Shared test utilities for mem0-stack project
Provides comprehensive testing infrastructure, factories, and utilities
"""

import asyncio
import json
import os
import tempfile
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional, Generator, AsyncGenerator
from unittest.mock import Mock, MagicMock, patch
import pytest
import random
import string
import time
from dataclasses import dataclass, field

# Database and HTTP testing
import httpx
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Factory and fixture utilities
from factory import Factory, Faker, LazyFunction, SubFactory
from factory.alchemy import SQLAlchemyModelFactory

# Performance and benchmark utilities
import psutil
import pytest_benchmark


@dataclass
class TestConfig:
    """Test configuration container"""

    database_url: str = "sqlite:///:memory:"
    test_data_dir: Path = field(
        default_factory=lambda: Path(__file__).parent / "test_data"
    )
    mock_external_services: bool = True
    enable_performance_tracking: bool = True
    coverage_threshold: float = 80.0
    max_test_duration: float = 30.0


class TestEnvironment:
    """Test environment management"""

    def __init__(self, config: TestConfig = None):
        self.config = config or TestConfig()
        self.temp_dirs: List[Path] = []
        self.mock_patches: List[Mock] = []
        self.performance_data: Dict[str, Any] = {}

    def setup(self):
        """Setup test environment"""
        # Set environment variables
        os.environ["TESTING"] = "true"
        os.environ["DATABASE_URL"] = self.config.database_url
        os.environ["LOG_LEVEL"] = "DEBUG"

        # Create test data directory
        self.config.test_data_dir.mkdir(exist_ok=True)

        # Setup performance tracking
        if self.config.enable_performance_tracking:
            self.performance_data["start_time"] = time.time()
            self.performance_data["start_memory"] = psutil.Process().memory_info().rss

    def teardown(self):
        """Cleanup test environment"""
        # Clean up temporary directories
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                import shutil

                shutil.rmtree(temp_dir)

        # Clean up mocks
        for mock in self.mock_patches:
            if hasattr(mock, "stop"):
                mock.stop()

        # Record performance data
        if self.config.enable_performance_tracking:
            self.performance_data["end_time"] = time.time()
            self.performance_data["end_memory"] = psutil.Process().memory_info().rss
            self.performance_data["duration"] = (
                self.performance_data["end_time"] - self.performance_data["start_time"]
            )
            self.performance_data["memory_delta"] = (
                self.performance_data["end_memory"]
                - self.performance_data["start_memory"]
            )

    def create_temp_dir(self, prefix: str = "test_") -> Path:
        """Create a temporary directory for test"""
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        self.temp_dirs.append(temp_dir)
        return temp_dir

    def create_temp_file(self, content: str = "", suffix: str = ".tmp") -> Path:
        """Create a temporary file with content"""
        temp_dir = self.create_temp_dir()
        temp_file = temp_dir / f"test_file{suffix}"
        temp_file.write_text(content)
        return temp_file


class DataFactory:
    """Factory for creating test data"""

    @staticmethod
    def random_string(length: int = 10) -> str:
        """Generate random string"""
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    @staticmethod
    def random_email() -> str:
        """Generate random email"""
        return f"{DataFactory.random_string()}@test.com"

    @staticmethod
    def random_uuid() -> str:
        """Generate random UUID"""
        return str(uuid.uuid4())

    @staticmethod
    def create_user_data(
        user_id: str = None, name: str = None, email: str = None, **kwargs
    ) -> Dict[str, Any]:
        """Create user test data"""
        return {
            "user_id": user_id or DataFactory.random_string(),
            "name": name or f"Test User {DataFactory.random_string(5)}",
            "email": email or DataFactory.random_email(),
            "created_at": datetime.now(UTC).isoformat(),
            **kwargs,
        }

    @staticmethod
    def create_memory_data(
        user_id: str = None,
        content: str = None,
        metadata: Dict[str, Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create memory test data"""
        return {
            "user_id": user_id or DataFactory.random_string(),
            "content": content or f"Test memory content {DataFactory.random_string()}",
            "metadata": metadata
            or {"test": "data", "timestamp": datetime.now(UTC).isoformat()},
            "created_at": datetime.now(UTC).isoformat(),
            **kwargs,
        }

    @staticmethod
    def create_app_data(
        name: str = None, description: str = None, **kwargs
    ) -> Dict[str, Any]:
        """Create app test data"""
        return {
            "name": name or f"test_app_{DataFactory.random_string(5)}",
            "description": description
            or f"Test application {DataFactory.random_string()}",
            "is_active": True,
            "created_at": datetime.now(UTC).isoformat(),
            **kwargs,
        }

    @staticmethod
    def create_message_data(
        role: str = "user", content: str = None, **kwargs
    ) -> Dict[str, Any]:
        """Create message test data"""
        return {
            "role": role,
            "content": content or f"Test message {DataFactory.random_string()}",
            "timestamp": datetime.now(UTC).isoformat(),
            **kwargs,
        }

    @staticmethod
    def create_batch_data(
        factory_func: callable, count: int = 5, **kwargs
    ) -> List[Dict[str, Any]]:
        """Create batch of test data"""
        return [factory_func(**kwargs) for _ in range(count)]


class MockServices:
    """Mock external services for testing"""

    def __init__(self):
        self.openai_mock = None
        self.postgres_mock = None
        self.neo4j_mock = None
        self.redis_mock = None

    def setup_openai_mock(self) -> Mock:
        """Setup OpenAI API mock"""
        self.openai_mock = Mock()

        # Mock embeddings
        self.openai_mock.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )

        # Mock chat completions
        self.openai_mock.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="Test response"))]
        )

        return self.openai_mock

    def setup_postgres_mock(self) -> Mock:
        """Setup PostgreSQL mock"""
        self.postgres_mock = Mock()

        # Mock connection
        self.postgres_mock.connect.return_value = Mock()

        # Mock cursor
        cursor_mock = Mock()
        cursor_mock.fetchall.return_value = []
        cursor_mock.fetchone.return_value = None
        self.postgres_mock.cursor.return_value = cursor_mock

        return self.postgres_mock

    def setup_neo4j_mock(self) -> Mock:
        """Setup Neo4j mock"""
        self.neo4j_mock = Mock()

        # Mock session
        session_mock = Mock()
        session_mock.run.return_value = Mock(data=[])
        self.neo4j_mock.session.return_value = session_mock

        return self.neo4j_mock

    def setup_redis_mock(self) -> Mock:
        """Setup Redis mock"""
        self.redis_mock = Mock()

        # Mock basic operations
        self.redis_mock.get.return_value = None
        self.redis_mock.set.return_value = True
        self.redis_mock.delete.return_value = 1

        return self.redis_mock


class TestDatabaseManager:
    """Database management for tests"""

    def __init__(self, database_url: str = "sqlite:///:memory:"):
        self.database_url = database_url
        self.engine = None
        self.session_factory = None

    def setup(self):
        """Setup test database"""
        self.engine = create_engine(
            self.database_url,
            connect_args=(
                {"check_same_thread": False} if "sqlite" in self.database_url else {}
            ),
            poolclass=StaticPool if "sqlite" in self.database_url else None,
            echo=False,  # Set to True for SQL debugging
        )

        self.session_factory = sessionmaker(bind=self.engine)

        # Create tables
        self._create_tables()

    def _create_tables(self):
        """Create test tables"""
        # This would typically import your models and create tables
        # For now, we'll handle this in the actual test setup
        pass

    def get_session(self) -> Session:
        """Get database session"""
        return self.session_factory()

    def cleanup(self):
        """Cleanup database"""
        if self.engine:
            self.engine.dispose()


class AsyncTestUtils:
    """Utilities for async testing"""

    @staticmethod
    def run_async_test(coro):
        """Run async test function"""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)

    @staticmethod
    async def async_retry(
        func: callable, max_attempts: int = 3, delay: float = 0.1, backoff: float = 2.0
    ):
        """Retry async function with backoff"""
        for attempt in range(max_attempts):
            try:
                return await func()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                await asyncio.sleep(delay * (backoff**attempt))

    @staticmethod
    async def wait_for_condition(
        condition: callable, timeout: float = 5.0, interval: float = 0.1
    ) -> bool:
        """Wait for condition to be true"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if (
                await condition()
                if asyncio.iscoroutinefunction(condition)
                else condition()
            ):
                return True
            await asyncio.sleep(interval)
        return False


class PerformanceTracker:
    """Performance tracking utilities"""

    def __init__(self):
        self.metrics = {}

    def start_timer(self, name: str):
        """Start timing a operation"""
        self.metrics[name] = {
            "start_time": time.time(),
            "start_memory": psutil.Process().memory_info().rss,
        }

    def end_timer(self, name: str):
        """End timing and calculate metrics"""
        if name in self.metrics:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss

            self.metrics[name].update(
                {
                    "end_time": end_time,
                    "end_memory": end_memory,
                    "duration": end_time - self.metrics[name]["start_time"],
                    "memory_delta": end_memory - self.metrics[name]["start_memory"],
                }
            )

    def get_metrics(self, name: str) -> Dict[str, Any]:
        """Get metrics for operation"""
        return self.metrics.get(name, {})

    def assert_performance(
        self, name: str, max_duration: float = None, max_memory_mb: float = None
    ):
        """Assert performance constraints"""
        metrics = self.get_metrics(name)

        if max_duration and metrics.get("duration", 0) > max_duration:
            raise AssertionError(
                f"Operation '{name}' took {metrics['duration']:.2f}s, "
                f"expected < {max_duration}s"
            )

        if max_memory_mb:
            memory_mb = metrics.get("memory_delta", 0) / (1024 * 1024)
            if memory_mb > max_memory_mb:
                raise AssertionError(
                    f"Operation '{name}' used {memory_mb:.2f}MB, "
                    f"expected < {max_memory_mb}MB"
                )


class TestAssertions:
    """Custom test assertions"""

    @staticmethod
    def assert_valid_uuid(value: str, message: str = "Invalid UUID"):
        """Assert value is a valid UUID"""
        try:
            uuid.UUID(value)
        except ValueError:
            raise AssertionError(message)

    @staticmethod
    def assert_valid_datetime(value: str, message: str = "Invalid datetime"):
        """Assert value is a valid datetime string"""
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise AssertionError(message)

    @staticmethod
    def assert_json_structure(data: Dict[str, Any], expected_keys: List[str]):
        """Assert JSON has expected structure"""
        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            raise AssertionError(f"Missing keys: {missing_keys}")

    @staticmethod
    def assert_response_success(response: httpx.Response):
        """Assert HTTP response is successful"""
        if not 200 <= response.status_code < 300:
            raise AssertionError(
                f"Expected successful response, got {response.status_code}: {response.text}"
            )

    @staticmethod
    def assert_response_error(response: httpx.Response, expected_status: int = None):
        """Assert HTTP response is an error"""
        if 200 <= response.status_code < 300:
            raise AssertionError(f"Expected error response, got {response.status_code}")

        if expected_status and response.status_code != expected_status:
            raise AssertionError(
                f"Expected status {expected_status}, got {response.status_code}"
            )


# Global test utilities instance
test_env = TestEnvironment()
data_factory = DataFactory()
mock_services = MockServices()
async_utils = AsyncTestUtils()
performance_tracker = PerformanceTracker()
assertions = TestAssertions()


# Pytest fixtures
@pytest.fixture(scope="session")
def test_config():
    """Test configuration fixture"""
    return TestConfig()


@pytest.fixture(scope="function")
def test_environment(test_config):
    """Test environment fixture"""
    env = TestEnvironment(test_config)
    env.setup()
    yield env
    env.teardown()


@pytest.fixture(scope="function")
def test_db_manager(test_config):
    """Test database manager fixture"""
    db_manager = TestDatabaseManager(test_config.database_url)
    db_manager.setup()
    yield db_manager
    db_manager.cleanup()


@pytest.fixture(scope="function")
def mock_external_services():
    """Mock external services fixture"""
    services = MockServices()
    services.setup_openai_mock()
    services.setup_postgres_mock()
    services.setup_neo4j_mock()
    services.setup_redis_mock()
    yield services


@pytest.fixture(scope="function")
def performance_tracker_fixture():
    """Performance tracker fixture"""
    tracker = PerformanceTracker()
    yield tracker


@pytest.fixture(scope="function")
def test_data_factory():
    """Test data factory fixture"""
    return DataFactory()


# Pytest markers
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "async_test: Async tests")


# Test decorators
def async_test(func):
    """Decorator for async tests"""
    return pytest.mark.asyncio(func)


def performance_test(max_duration: float = None, max_memory_mb: float = None):
    """Decorator for performance tests"""

    def decorator(func):
        @pytest.mark.performance
        def wrapper(*args, **kwargs):
            tracker = PerformanceTracker()
            tracker.start_timer(func.__name__)

            try:
                result = func(*args, **kwargs)
            finally:
                tracker.end_timer(func.__name__)

                if max_duration or max_memory_mb:
                    tracker.assert_performance(
                        func.__name__,
                        max_duration=max_duration,
                        max_memory_mb=max_memory_mb,
                    )

            return result

        return wrapper

    return decorator


# Export all utilities
__all__ = [
    "TestConfig",
    "TestEnvironment",
    "DataFactory",
    "MockServices",
    "TestDatabaseManager",
    "AsyncTestUtils",
    "PerformanceTracker",
    "TestAssertions",
    "test_env",
    "data_factory",
    "mock_services",
    "async_utils",
    "performance_tracker",
    "assertions",
    "async_test",
    "performance_test",
]
