import os
import logging

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# load .env file (make sure you have DATABASE_URL set)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./openmemory.db")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in environment")

# Setup logging
logger = logging.getLogger(__name__)

def redact_database_url(url: str) -> str:
    """
    Redact sensitive information from database URLs.
    
    For PostgreSQL URLs (contains '@'), redact the user:password portion.
    For SQLite URLs (no '@'), return as-is since they don't contain credentials.
    """
    if '@' in url:
        # PostgreSQL-style URL: postgresql://user:password@host:port/database
        parts = url.split('@')
        if len(parts) >= 2:
            # Keep everything after the '@' and redact the credential part
            return f"{parts[0].split('://')[0]}://[REDACTED]@{parts[1]}"
    
    # SQLite or other URLs without '@' - return as-is since no credentials to redact
    return url

# Log database connection info with proper redaction
logger.info(f"Connecting to database: {redact_database_url(DATABASE_URL)}")

# SQLAlchemy engine & session
# Only add check_same_thread for SQLite databases
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}  # Needed for SQLite
    )
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
