"""
Pytest configuration and shared fixtures for OpenMemory API tests.
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
from testcontainers.compose import DockerCompose
import os
import tempfile
from pathlib import Path

from app.database import Base, get_db
from app.models import User, App, Memory
from main import app
from app.config import USER_ID, DEFAULT_APP_ID


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def postgres_container():
    """Start a PostgreSQL container for testing."""
    with PostgresContainer("postgres:15") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def test_database_url(postgres_container):
    """Get the database URL for testing."""
    return postgres_container.get_connection_url()


@pytest.fixture(scope="session")
def test_engine(test_database_url):
    """Create a test database engine."""
    engine = create_engine(test_database_url)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """Create a test session factory."""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def test_db(test_session_factory):
    """Create a test database session."""
    session = test_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def override_get_db(test_db):
    """Override the get_db dependency for testing."""
    def _override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def test_client(override_get_db):
    """Create a test HTTP client."""
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def test_user(test_db):
    """Create a test user."""
    user = User(
        user_id=USER_ID,
        name="Test User",
        email="test@example.com"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_app(test_db, test_user):
    """Create a test app."""
    app_instance = App(
        app_id=DEFAULT_APP_ID,
        name="Test App",
        description="Test application",
        user_id=test_user.user_id
    )
    test_db.add(app_instance)
    test_db.commit()
    test_db.refresh(app_instance)
    return app_instance


@pytest.fixture
def test_memory_data():
    """Sample memory data for testing."""
    return {
        "messages": [
            {"role": "user", "content": "Test user message"},
            {"role": "assistant", "content": "Test assistant response"}
        ],
        "user_id": USER_ID,
        "app_id": DEFAULT_APP_ID,
        "metadata": {
            "source": "test",
            "category": "conversation"
        }
    }


@pytest.fixture
def multiple_test_memories():
    """Multiple memory entries for testing."""
    return [
        {
            "messages": [
                {"role": "user", "content": "First test message"},
                {"role": "assistant", "content": "First test response"}
            ],
            "user_id": USER_ID,
            "metadata": {"category": "test", "priority": "high"}
        },
        {
            "messages": [
                {"role": "user", "content": "Second test message about API"},
                {"role": "assistant", "content": "Second test response about API"}
            ],
            "user_id": USER_ID,
            "metadata": {"category": "api", "priority": "medium"}
        },
        {
            "messages": [
                {"role": "user", "content": "Third test message about database"},
                {"role": "assistant", "content": "Third test response about database"}
            ],
            "user_id": USER_ID,
            "metadata": {"category": "database", "priority": "low"}
        }
    ]


@pytest.fixture
def test_search_query():
    """Sample search query for testing."""
    return {
        "query": "test message",
        "user_id": USER_ID,
        "limit": 10
    }


# Async fixtures for async tests
@pytest.fixture
async def async_test_client():
    """Create an async test HTTP client."""
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


# Mock fixtures for external dependencies
@pytest.fixture
def mock_openai_client(monkeypatch):
    """Mock OpenAI client for testing."""
    class MockOpenAIClient:
        def __init__(self):
            self.embeddings = MockEmbeddings()
        
        class MockEmbeddings:
            def create(self, input, model="text-embedding-3-small"):
                return MockEmbeddingResponse()
        
        class MockEmbeddingResponse:
            def __init__(self):
                self.data = [MockEmbeddingData()]
        
        class MockEmbeddingData:
            def __init__(self):
                self.embedding = [0.1] * 1536  # Mock embedding vector
    
    monkeypatch.setattr("app.utils.embeddings.openai_client", MockOpenAIClient())
    return MockOpenAIClient()


@pytest.fixture
def mock_mem0_client(monkeypatch):
    """Mock Mem0 client for testing."""
    class MockMem0Client:
        def add(self, messages, user_id=None, metadata=None):
            return {"message": "Memory added successfully", "id": "test-memory-id"}
        
        def search(self, query, user_id=None, limit=10):
            return {
                "results": [
                    {
                        "id": "test-memory-id",
                        "memory": "Test memory content",
                        "score": 0.95,
                        "metadata": {"category": "test"}
                    }
                ]
            }
        
        def get_all(self, user_id=None):
            return [
                {
                    "id": "test-memory-id",
                    "memory": "Test memory content",
                    "metadata": {"category": "test"}
                }
            ]
        
        def delete(self, memory_id):
            return {"message": "Memory deleted successfully"}
        
        def delete_all(self, user_id=None):
            return {"message": "All memories deleted successfully"}
    
    monkeypatch.setattr("app.utils.mem0_client.mem0_client", MockMem0Client())
    return MockMem0Client()


# Performance testing fixtures
@pytest.fixture
def performance_test_data():
    """Large dataset for performance testing."""
    return {
        "bulk_memories": [
            {
                "messages": [
                    {"role": "user", "content": f"Performance test message {i}"},
                    {"role": "assistant", "content": f"Performance test response {i}"}
                ],
                "user_id": USER_ID,
                "metadata": {"batch": "performance_test", "index": i}
            }
            for i in range(100)  # 100 test memories
        ]
    }


# Security testing fixtures
@pytest.fixture
def security_test_payloads():
    """Security test payloads for injection testing."""
    return {
        "sql_injection": [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "admin' OR 1=1#"
        ],
        "xss_payloads": [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//"
        ],
        "command_injection": [
            "; rm -rf /",
            "| cat /etc/passwd",
            "`rm -rf /`",
            "$(rm -rf /)"
        ]
    }


# Database cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_database(test_db):
    """Automatically clean up database after each test."""
    yield
    # Clean up all test data
    test_db.query(Memory).delete()
    test_db.query(App).delete()
    test_db.query(User).delete()
    test_db.commit()