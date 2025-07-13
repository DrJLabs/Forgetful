import logging
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


def redact_database_url(url: str) -> str:
    """
    Redact sensitive information from a database URL.

    Handles:
    - Multiple '@' characters in usernames/passwords
    - URLs without proper scheme (://missing)
    """
    if not url:
        return url

    # Check if URL has proper scheme
    if "://" not in url:
        # For URLs without scheme, assume they start with credentials
        # If there's an '@' character, redact everything before the last '@'
        if "@" in url:
            # Find the last '@' which should be the separator
            last_at_pos = url.rfind("@")
            return f"[REDACTED]@{url[last_at_pos+1:]}"
        else:
            # No credentials to redact
            return url

    # For URLs with proper scheme
    if "@" in url:
        # Split by '://' to separate scheme from the rest
        scheme_sep = url.split("://", 1)
        scheme = scheme_sep[0]
        rest = scheme_sep[1]

        # Find the authority part (before the path)
        # The path starts with '/' after the host
        path_start = rest.find("/")
        if path_start == -1:
            # No path, entire rest is authority
            authority = rest
            path = ""
        else:
            authority = rest[:path_start]
            path = rest[path_start:]

        # Find the '@' in the authority part - this is the credential separator
        auth_at_pos = authority.rfind("@")
        if auth_at_pos != -1:
            host_and_port = authority[auth_at_pos + 1 :]
            return f"{scheme}://[REDACTED]@{host_and_port}{path}"
        else:
            # No credentials in authority part
            return url

    # No credentials to redact
    return url


# Environment detection
IS_TESTING = os.getenv("TESTING", "false").lower() == "true"
IS_CI = os.getenv("CI", "false").lower() == "true"


def get_database_url() -> str:
    """Get database URL with environment-specific handling."""
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return database_url

    # Environment-specific database URL construction
    if IS_TESTING and IS_CI:
        # CI environment - use localhost for GitHub Actions services
        return "postgresql://postgres:testpass@localhost:5432/test_db"
    elif IS_TESTING:
        # Local testing - use SQLite by default for unit tests
        return "sqlite:///./test_openmemory.db"
    else:
        # Production/development - use docker-compose hostnames
        postgres_host = os.getenv("POSTGRES_HOST", "postgres-mem0")
        postgres_port = os.getenv("POSTGRES_PORT", "5432")
        postgres_db = os.getenv("POSTGRES_DB", "mem0")
        postgres_user = os.getenv("POSTGRES_USER", "postgres")
        postgres_password = os.getenv("POSTGRES_PASSWORD", "postgres")

        return f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"


def create_database_engine(database_url: str) -> Engine:
    """Create database engine with appropriate configuration."""
    if database_url.startswith("sqlite"):
        # SQLite configuration
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if "sqlite" in str(engine.url):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

    else:
        # PostgreSQL configuration
        engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if "sqlite" in str(engine.url):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

    return engine


# Initialize database components
DATABASE_URL = get_database_url()

# Log database connection info with proper redaction
logger.info(f"Connecting to database: {redact_database_url(DATABASE_URL)}")

engine = create_database_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_health() -> bool:
    """Check if database connection is healthy."""
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def get_migration_database_url() -> str:
    """Get database URL for migrations (may differ from runtime URL)."""
    return DATABASE_URL
