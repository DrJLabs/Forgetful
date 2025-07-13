import os
import logging
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

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
            echo=IS_TESTING and os.getenv("DEBUG_SQL", "false").lower() == "true",
        )
    else:
        # PostgreSQL configuration
        engine_kwargs = {
            "pool_size": 10 if IS_TESTING else 20,
            "max_overflow": 5 if IS_TESTING else 10,
            "pool_timeout": 30,
            "pool_recycle": 3600,
            "pool_pre_ping": True,
            "echo": IS_TESTING and os.getenv("DEBUG_SQL", "false").lower() == "true",
        }
        
        # Use QueuePool for better connection management
        engine_kwargs["poolclass"] = QueuePool
        
        engine = create_engine(database_url, **engine_kwargs)
    
    # Add connection event listeners for better debugging
    if IS_TESTING:
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if "sqlite" in str(engine.url):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
    
    return engine

# Initialize database components
DATABASE_URL = get_database_url()
logger.info(f"Using database URL: {DATABASE_URL.split('@')[0]}@[REDACTED]")

engine = create_database_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI
def get_db():
    """Database session dependency for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Health check function
def check_database_health() -> bool:
    """Check if database connection is healthy."""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

# Migration helper function
def get_migration_database_url() -> str:
    """Get database URL specifically for migrations."""
    # For migrations, always use the actual database URL
    # This ensures migrations run against the correct database
    return DATABASE_URL
