"""
Comprehensive test configuration for OpenMemory API.

Provides test database, fixtures, and utilities.
"""

import asyncio
import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import alembic.command
import alembic.config
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from testcontainers.postgres import PostgresContainer

# Set up test environment BEFORE any imports
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database import Base, get_db  # noqa: E402
from app.models import App, Memory, MemoryState, User  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

# Import app components after setting environment
from main import app  # noqa: E402

# Test configuration
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def get_app():
    """Get app components for testing."""
    from app.database import Base, get_db
    from app.models import App, Memory, MemoryState, User
    from main import app

    return app, get_db, Base, User, App, Memory, MemoryState


# ============================================================================
# DATABASE TESTING FRAMEWORK
# ============================================================================


@pytest.fixture(scope="session")
def docker_postgres_container():
    """
    Create a PostgreSQL container for testing with production-like setup.

    This provides production fidelity for database testing while maintaining
    isolation. Container is shared across test session for performance.
    """
    with PostgresContainer(
        "pgvector/pgvector:pg16",
        username="test_user",
        password="test_password",
        dbname="test_mem0",
        port=5432,
    ) as postgres:
        # Wait for container to be ready
        postgres.get_connection_url()
        yield postgres


@pytest.fixture(scope="session")
def docker_postgres_url(docker_postgres_container):
    """Get PostgreSQL URL for Docker container."""
    return docker_postgres_container.get_connection_url()


@pytest.fixture(scope="session")
def docker_postgres_engine(docker_postgres_url):
    """
    Create PostgreSQL engine with proper setup for testing.

    This engine uses the production database type (PostgreSQL) for maximum
    fidelity while maintaining test isolation.
    """
    engine = create_engine(
        docker_postgres_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False,  # Set to True for SQL debugging
    )

    # Create pgvector extension if not exists
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_engine():
    """Create test database engine with in-memory SQLite for fast unit tests."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,  # Set to True for SQL debugging
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Create test database session with automatic rollback."""
    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def postgres_test_session(docker_postgres_engine):
    """
    Create PostgreSQL test session with transaction rollback.

    This fixture provides a PostgreSQL session that automatically rolls back
    all changes at the end of each test, ensuring test isolation.
    """
    connection = docker_postgres_engine.connect()
    transaction = connection.begin()

    # Create session bound to the transaction
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
async def test_client(test_db_session):
    """Create test HTTP client with database override."""

    # Override database dependency
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def postgres_test_client(postgres_test_session):
    """Create test HTTP client with PostgreSQL database."""

    # Override database dependency
    def override_get_db():
        try:
            yield postgres_test_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()


# ============================================================================
# TRANSACTION TESTING FIXTURES
# ============================================================================


@pytest.fixture
def transaction_test_session(docker_postgres_engine):
    """
    Session for testing transaction behavior.

    This fixture is specifically for testing transaction rollback,
    commit behavior, and concurrent access patterns.
    """
    connection = docker_postgres_engine.connect()

    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def concurrent_sessions(docker_postgres_engine):
    """
    Provide multiple concurrent database sessions for testing.

    Used for testing concurrent access, deadlock detection,
    and transaction isolation levels.
    """
    sessions = []

    try:
        for i in range(3):
            connection = docker_postgres_engine.connect()
            SessionLocal = sessionmaker(bind=connection)
            session = SessionLocal()
            sessions.append((connection, session))

        yield [session for _, session in sessions]
    finally:
        for connection, session in sessions:
            session.close()
            connection.close()


# ============================================================================
# MIGRATION TESTING FIXTURES
# ============================================================================


@pytest.fixture
def migration_test_engine():
    """
    Create a separate engine for migration testing.

    This engine is used specifically for testing Alembic migrations
    and database schema evolution.
    """
    with PostgresContainer(
        "pgvector/pgvector:pg16",
        username="migration_user",
        password="migration_password",
        dbname="migration_test",
        port=5432,
    ) as postgres:
        migration_url = postgres.get_connection_url()
        engine = create_engine(migration_url)

        # Create pgvector extension
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()

        yield engine, migration_url

        engine.dispose()


@pytest.fixture
def alembic_config(migration_test_engine):
    """Create Alembic configuration for migration testing."""
    engine, migration_url = migration_test_engine

    # Create temporary alembic.ini
    config = alembic.config.Config()
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", migration_url)

    return config, engine


# ============================================================================
# TEST DATA FACTORIES
# ============================================================================


@pytest.fixture
def test_user_factory():
    """Factory for creating test users."""

    def create_user(
        user_id: str = None,
        name: str = "Test User",
        email: str = "test@example.com"
    ) -> User:
        return User(
            id=uuid4(),
            user_id=user_id or f"test_user_{uuid4().hex[:8]}",
            name=name,
            email=email,
            created_at=datetime.now(UTC),
        )

    return create_user


@pytest.fixture
def test_app_factory():
    """Factory for creating test applications."""

    def create_app(name: str = "Test App", user_id: str = None) -> App:
        return App(
            id=uuid4(),
            name=name,
            user_id=user_id or f"test_user_{uuid4().hex[:8]}",
            created_at=datetime.now(UTC),
        )

    return create_app


@pytest.fixture
def test_memory_factory():
    """Factory for creating test memories."""

    def create_memory(
        content: str = "Test memory content",
        user_id: str = None,
        app_id: str = None
    ) -> Memory:
        return Memory(
            id=uuid4(),
            content=content,
            user_id=user_id or f"test_user_{uuid4().hex[:8]}",
            app_id=app_id or f"test_app_{uuid4().hex[:8]}",
            created_at=datetime.now(UTC),
        )

    return create_memory


# ============================================================================
# TESTING UTILITIES
# ============================================================================


@pytest.fixture
def db_inspector():
    """Utility for inspecting database state during tests."""

    def inspector(engine):
        """Inspect database state and structure."""
        with engine.connect() as conn:
            # Get table information
            result = conn.execute(
                text(
                    """
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
            """
                )
            )

            tables = {}
            for row in result:
                table_name = row[0]
                if table_name not in tables:
                    tables[table_name] = []
                tables[table_name].append(
                    {
                        "column": row[1],
                        "type": row[2],
                        "nullable": row[3] == "YES"
                    }
                )

            return tables

    return inspector


@pytest.fixture
def performance_monitor():
    """Monitor database performance during tests."""

    def monitor(engine):
        """Monitor database performance metrics."""
        with engine.connect() as conn:
            # Get connection stats
            result = conn.execute(
                text(
                    """
                SELECT
                    datname,
                    numbackends,
                    xact_commit,
                    xact_rollback,
                    blks_read,
                    blks_hit,
                    tup_returned,
                    tup_fetched,
                    tup_inserted,
                    tup_updated,
                    tup_deleted
                FROM pg_stat_database
                WHERE datname = current_database()
            """
                )
            )

            stats = result.fetchone()
            return {
                "database": stats[0],
                "connections": stats[1],
                "commits": stats[2],
                "rollbacks": stats[3],
                "disk_reads": stats[4],
                "buffer_hits": stats[5],
                "tuples_returned": stats[6],
                "tuples_fetched": stats[7],
                "tuples_inserted": stats[8],
                "tuples_updated": stats[9],
                "tuples_deleted": stats[10],
            }

    return monitor


# ============================================================================
# MOCK FIXTURES
# ============================================================================


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    with patch("openai.OpenAI") as mock_client:
        # Mock embedding response
        mock_client.return_value.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.1] * 1536)]
        )

        # Mock chat completion response
        mock_client.return_value.chat.completions.create.return_value = (
            MagicMock(
                choices=[MagicMock(message=MagicMock(content="Test response"))]
            )
        )

        yield mock_client


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver for testing."""
    with patch("neo4j.GraphDatabase.driver") as mock_driver:
        mock_session = MagicMock()
        mock_driver.return_value.session.return_value = mock_session
        mock_session.run.return_value = []

        yield mock_driver


# ============================================================================
# DIRECT TEST FIXTURES
# ============================================================================

@pytest.fixture
def test_user(test_db_session):
    """Create a test user instance."""
    user = User(
        id=uuid4(),
        user_id="test_user",
        name="Test User",
        created_at=datetime.now(UTC),
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def test_app(test_db_session, test_user):
    """Create a test app instance."""
    app_obj = App(
        id=uuid4(),
        name="test_app",
        owner_id=test_user.id,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    test_db_session.add(app_obj)
    test_db_session.commit()
    test_db_session.refresh(app_obj)
    return app_obj


@pytest.fixture
def test_memory(test_db_session, test_user, test_app):
    """Create a test memory instance."""
    memory = Memory(
        id=uuid4(),
        content="Test memory content",
        user_id=test_user.id,
        app_id=test_app.id,
        state=MemoryState.active,
        created_at=datetime.now(UTC),
    )
    test_db_session.add(memory)
    test_db_session.commit()
    test_db_session.refresh(memory)
    return memory


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Automatically cleanup test data after each test."""
    yield

    # Clear any global state
    if hasattr(app, "dependency_overrides"):
        app.dependency_overrides.clear()

    # Reset environment variables
    test_env_vars = [
        "TESTING",
        "DATABASE_URL",
        "OPENAI_API_KEY",
        "NEO4J_URL",
        "NEO4J_USERNAME",
        "NEO4J_PASSWORD",
    ]

    for var in test_env_vars:
        if var in os.environ:
            if var == "TESTING":
                os.environ[var] = "true"
            elif var == "DATABASE_URL":
                os.environ[var] = "sqlite:///:memory:"
            # Don't reset other vars that might be needed
