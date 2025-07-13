import os
import logging
from urllib.parse import urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Configure logging
logger = logging.getLogger(__name__)

# load .env file (make sure you have DATABASE_URL set)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./openmemory.db")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in environment")


def _redact_database_url(url: str) -> str:
    """Redact sensitive information from database URLs."""
    try:
        parsed = urlparse(url)
        if parsed.password:
            # Only redact URLs that actually have credentials
            redacted_netloc = f"{parsed.username}:***@{parsed.hostname}"
            if parsed.port:
                redacted_netloc += f":{parsed.port}"
            return parsed._replace(netloc=redacted_netloc).geturl()
        return url
    except Exception:
        # If parsing fails, return original URL (likely SQLite file path)
        return url


def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """Enable foreign key enforcement for SQLite databases."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


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
