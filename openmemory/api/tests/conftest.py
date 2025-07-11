"""
Test configuration and fixtures for API contract testing
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import Mock, patch

# Set testing environment variable
os.environ["TESTING"] = "true"

from main import app
from app.database import Base, get_db
from app.models import User, App, Memory, MemoryState
from app.utils.memory import get_memory_client
from uuid import uuid4


# Test database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


@pytest.fixture
def test_db():
    """Create test database session"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(test_db):
    """Create test client with database override"""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def openapi_schema(client):
    """Get OpenAPI schema from the test client"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def mock_memory_client():
    """Mock memory client for testing"""
    mock_client = Mock()

    # Mock methods
    mock_client.add.return_value = {
        "id": str(uuid4()),
        "memory": "Test memory content",
        "created_at": "2023-01-01T00:00:00Z",
        "user_id": "test_user",
        "metadata": {},
    }

    mock_client.get_all.return_value = {"results": []}

    mock_client.search.return_value = {"results": []}

    mock_client.get.return_value = {
        "id": str(uuid4()),
        "memory": "Test memory content",
        "created_at": "2023-01-01T00:00:00Z",
        "user_id": "test_user",
        "metadata": {},
    }

    with patch("app.utils.memory.get_memory_client", return_value=mock_client):
        with patch("app.mem0_client.get_memory_client", return_value=mock_client):
            with patch(
                "app.routers.mem0_memories.get_memory_client", return_value=mock_client
            ):
                yield mock_client


@pytest.fixture
def test_user(test_db):
    """Create test user for contract testing"""
    user = User(
        id=uuid4(),
        user_id="test_user_contract",
        name="Test User Contract",
        email="test_contract@example.com",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_app_obj(test_db, test_user):
    """Create test app for contract testing"""
    app_obj = App(
        id=uuid4(),
        owner_id=test_user.id,
        name="test_app_contract",
        description="Test App for Contract Testing",
    )
    test_db.add(app_obj)
    test_db.commit()
    test_db.refresh(app_obj)
    return app_obj


@pytest.fixture
def test_memory(test_db, test_user, test_app_obj):
    """Create test memory for contract testing"""
    memory = Memory(
        id=uuid4(),
        user_id=test_user.id,
        app_id=test_app_obj.id,
        content="Test memory content for contract testing",
        state=MemoryState.active,
        metadata_={"test": True, "contract_test": True},
    )
    test_db.add(memory)
    test_db.commit()
    test_db.refresh(memory)
    return memory


@pytest.fixture
def sample_memories(test_db, test_user, test_app_obj):
    """Create sample memories for testing"""
    memories = []
    for i in range(10):
        memory = Memory(
            id=uuid4(),
            user_id=test_user.id,
            app_id=test_app_obj.id,
            content=f"Sample memory content {i + 1}",
            state=MemoryState.active,
            metadata_={"sample": True, "index": i},
        )
        test_db.add(memory)
        memories.append(memory)

    test_db.commit()
    return memories


@pytest.fixture(autouse=True)
def cleanup_after_test(test_db):
    """Cleanup database after each test"""
    yield

    # Clean up test data
    test_db.query(Memory).delete()
    test_db.query(App).delete()
    test_db.query(User).delete()
    test_db.commit()


# API Contract Testing Fixtures
@pytest.fixture
def valid_memory_create_request():
    """Valid memory creation request data"""
    return {
        "user_id": "test_user_contract",
        "text": "Test memory content for API contract testing",
        "metadata": {"test": True, "contract_test": True, "category": "testing"},
        "app": "test_app_contract",
    }


@pytest.fixture
def invalid_memory_create_requests():
    """List of invalid memory creation requests"""
    return [
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
        {"user_id": "test_user", "text": "test", "app": ""},  # Empty app
        {"user_id": "test_user", "text": "test", "app": None},  # Null app
    ]


@pytest.fixture
def expected_memory_response_fields():
    """Expected fields in memory response"""
    return [
        "id",
        "content",
        "created_at",
        "user_id",
        "metadata",
        "state",
        "categories",
        "app_name",
    ]


@pytest.fixture
def expected_pagination_fields():
    """Expected fields in pagination response"""
    return ["items", "total", "page", "size", "pages"]


@pytest.fixture
def expected_error_response_fields():
    """Expected fields in error response"""
    return ["detail"]


@pytest.fixture
def expected_validation_error_fields():
    """Expected fields in validation error detail"""
    return ["loc", "msg", "type"]


# Test markers
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "contract: marks tests as API contract tests")
    config.addinivalue_line("markers", "openapi: marks tests as OpenAPI schema tests")
    config.addinivalue_line(
        "markers", "validation: marks tests as input validation tests"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "slow: marks tests as slow running tests")
