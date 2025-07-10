"""
Comprehensive test configuration for OpenMemory API
Provides test database, fixtures, and utilities
"""

import pytest
import asyncio
import os
import tempfile
from typing import AsyncGenerator, Generator
from uuid import uuid4
from datetime import datetime, UTC
from unittest.mock import patch, MagicMock

# Set up test environment BEFORE any imports
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from testcontainers.postgres import PostgresContainer
from testcontainers.neo4j import Neo4jContainer

# Import app components after setting environment
from main import app
from app.database import get_db, Base
from app.models import User, App, Memory, MemoryState

# Test configuration
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def postgres_container():
    """Setup PostgreSQL test container for integration tests"""
    with PostgresContainer("postgres:15") as postgres:
        # Wait for container to be ready
        postgres.get_connection_url()
        yield postgres


@pytest.fixture(scope="session")
def neo4j_container():
    """Setup Neo4j test container for integration tests"""
    with Neo4jContainer("neo4j:5.0") as neo4j:
        neo4j.with_env("NEO4J_AUTH", "neo4j/testpass")
        yield neo4j


@pytest.fixture(scope="function")
def test_db_engine():
    """Create test database engine with in-memory SQLite"""
    app, get_db, Base, User, App, Memory, MemoryState = get_app()
    
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # Set to True for SQL debugging
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Create test database session"""
    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
async def test_client(test_db_session):
    """Create test HTTP client with database override"""
    app, get_db, Base, User, App, Memory, MemoryState = get_app()
    
    # Override database dependency
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(test_db_session):
    """Create test user"""
    app, get_db, Base, User, App, Memory, MemoryState = get_app()
    
    user = User(
        id=uuid4(),
        user_id="test_user",
        name="Test User",
        created_at=datetime.now(UTC)
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_app(test_db_session, test_user):
    """Create test app"""
    app, get_db, Base, User, App, Memory, MemoryState = get_app()
    
    test_app = App(
        id=uuid4(),
        name="test_app",
        owner_id=test_user.id,
        is_active=True,
        created_at=datetime.now(UTC)
    )
    test_db_session.add(test_app)
    test_db_session.commit()
    test_db_session.refresh(test_app)
    return test_app


@pytest.fixture(scope="function")
def test_memory(test_db_session, test_user, test_app):
    """Create test memory"""
    app, get_db, Base, User, App, Memory, MemoryState = get_app()
    
    memory = Memory(
        id=uuid4(),
        content="Test memory content",
        user_id=test_user.id,
        app_id=test_app.id,
        state=MemoryState.active,
        created_at=datetime.now(UTC),
        metadata_={"test": "data"}
    )
    test_db_session.add(memory)
    test_db_session.commit()
    test_db_session.refresh(memory)
    return memory


@pytest.fixture(scope="function")
def multiple_test_memories(test_db_session, test_user, test_app):
    """Create multiple test memories"""
    app, get_db, Base, User, App, Memory, MemoryState = get_app()
    
    memories = []
    for i in range(5):
        memory = Memory(
            id=uuid4(),
            content=f"Test memory content {i}",
            user_id=test_user.id,
            app_id=test_app.id,
            state=MemoryState.active,
            created_at=datetime.now(UTC),
            metadata_={"test": f"data_{i}"}
        )
        test_db_session.add(memory)
        memories.append(memory)
    
    test_db_session.commit()
    for memory in memories:
        test_db_session.refresh(memory)
    
    return memories


@pytest.fixture(scope="function")
def mock_memory_client(mocker):
    """Mock memory client for testing"""
    mock_client = mocker.MagicMock()
    
    # Mock successful responses
    mock_client.add.return_value = {
        "results": [{"id": "test_memory_id", "memory": "Test memory"}]
    }
    
    mock_client.get_all.return_value = {
        "results": [
            {"id": "test_1", "memory": "Test memory 1", "created_at": "2024-01-01T00:00:00Z"},
            {"id": "test_2", "memory": "Test memory 2", "created_at": "2024-01-01T00:00:00Z"}
        ]
    }
    
    mock_client.search.return_value = {
        "results": [
            {"id": "test_1", "memory": "Test memory 1", "created_at": "2024-01-01T00:00:00Z"}
        ]
    }
    
    mock_client.get.return_value = {
        "id": "test_1", 
        "memory": "Test memory 1", 
        "created_at": "2024-01-01T00:00:00Z",
        "user_id": "test_user",
        "metadata": {}
    }
    
    # Mock get_memory_client function - this will override the lazy initialization
    mocker.patch("app.mem0_client.get_memory_client", return_value=mock_client)
    
    # Also patch any direct imports of the memory client
    mocker.patch("app.mem0_client.memory_client", mock_client)
    
    return mock_client


# Test utilities
class TestDataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_user_data(user_id: str = "test_user") -> dict:
        return {
            "user_id": user_id,
            "name": f"Test User {user_id}",
            "created_at": datetime.now(UTC).isoformat()
        }
    
    @staticmethod
    def create_memory_data(user_id: str = "test_user", app: str = "test_app") -> dict:
        return {
            "user_id": user_id,
            "text": "Test memory content",
            "metadata": {"test": "data"},
            "app": app
        }
    
    @staticmethod
    def create_app_data(name: str = "test_app") -> dict:
        return {
            "name": name,
            "description": f"Test application {name}",
            "is_active": True
        }


# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e


# Test environment setup
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables"""
    # Clear any existing memory client instance
    import app.mem0_client
    app.mem0_client._memory_client = None
    
    yield
    
    # Environment variables are set at module level, so we don't need to clean them up
    # as they should remain consistent throughout the test session


def get_app():
    """Get the FastAPI app and database components"""
    return app, get_db, Base, User, App, Memory, MemoryState


# Async test helper
def async_test(func):
    """Decorator to run async tests"""
    return pytest.mark.asyncio(func) 