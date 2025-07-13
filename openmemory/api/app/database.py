import logging
import os
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

# Configure logging
logger = logging.getLogger(__name__)

# load .env file (make sure you have DATABASE_URL set)
load_dotenv()


def _redact_database_url(url: str) -> str:
    """
    Redacts sensitive information from a database URL for safe logging.

    Handles edge cases:
    - Missing hostname: Returns generic message instead of malformed URL
    - Missing username with password: Preserves correct format `:***@hostname`

    Args:
        url: Database URL to redact

    Returns:
        Redacted URL string or generic message for invalid URLs
    """
    try:
        parsed = urlparse(url)

        # SQLite URLs don't have hostnames and don't contain sensitive info
        if parsed.scheme == "sqlite":
            return url

        # If hostname is None or empty, return generic redacted message
        if not parsed.hostname:
            return "[REDACTED_DATABASE_URL]"

        # Build netloc with proper redaction
        netloc_parts = []

        # Handle username
        if parsed.username:
            netloc_parts.append(parsed.username)

        # Handle password - preserve colon for no-username cases
        if parsed.password:
            if parsed.username:
                netloc_parts.append(":***")
            else:
                netloc_parts.append(":***")

        # Add @ separator if we have username or password
        if parsed.username or parsed.password:
            netloc = "".join(netloc_parts) + "@" + parsed.hostname
        else:
            netloc = parsed.hostname

        # Add port if present
        if parsed.port:
            netloc += f":{parsed.port}"

        # Reconstruct URL
        redacted_url = f"{parsed.scheme}://{netloc}"
        if parsed.path:
            redacted_url += parsed.path
        if parsed.query:
            redacted_url += f"?{parsed.query}"
        if parsed.fragment:
            redacted_url += f"#{parsed.fragment}"

        return redacted_url

    except Exception:
        # If URL parsing fails completely, return generic message
        return "[REDACTED_DATABASE_URL]"


def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """Enable foreign key enforcement for SQLite databases."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_database_url() -> str:
    """Get the database URL from environment variables."""
    return os.getenv("DATABASE_URL", "sqlite:///./openmemory.db")


def create_database_engine(database_url: str) -> Engine:
    """Create and configure the database engine."""
    if database_url.startswith("sqlite"):
        # SQLite configuration
        engine = create_engine(
            database_url, connect_args={"check_same_thread": False}  # Needed for SQLite
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

    return engine


# Initialize database components
DATABASE_URL = get_database_url()

# Log database connection info with proper redaction
logger.info(f"Connecting to database: {_redact_database_url(DATABASE_URL)}")

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
    """Check database health by executing a simple query with proper SQLAlchemy syntax."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            return result.fetchone() is not None
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def get_migration_database_url() -> str:
    """Get database URL for migrations (may differ from runtime URL)."""
    return DATABASE_URL
