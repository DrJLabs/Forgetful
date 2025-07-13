import logging
import os
from typing import Generator
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
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


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./openmemory.db")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in environment")

# Log database connection info
logger.info(f"Connecting to database: {_redact_database_url(DATABASE_URL)}")

# SQLAlchemy engine & session
# Only add check_same_thread for SQLite databases and enable foreign keys
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}  # Needed for SQLite
    )
    # Enable foreign key enforcement for SQLite
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)
else:
    engine = create_engine(DATABASE_URL)


def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """Enable foreign key enforcement for SQLite databases."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Initialize SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


# Dependency for FastAPI
def get_db() -> Generator[Session, None, None]:
    """
    Get database session for dependency injection.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_database_connection() -> bool:
    """
    Test database connection health.

    Returns:
        bool: True if connection is healthy, False otherwise
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database connection test failed: {e}")
        return False
