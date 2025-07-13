import os
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# load .env file (make sure you have DATABASE_URL set)
load_dotenv()


def _redact_database_url(url: str) -> str:
    """
    Redact sensitive information from a database URL for logging purposes.
    
    Args:
        url: The database URL to redact
        
    Returns:
        The redacted URL with password replaced by '***'
    """
    try:
        parsed = urlparse(url)
        
        # Only redact if there's a password to redact
        if not parsed.password:
            return url
            
        # Handle None values properly to avoid "None" in the URL
        username = parsed.username or ""
        hostname = parsed.hostname or ""
        
        # Construct the netloc with proper handling of None values
        if username:
            netloc = f"{username}:***@{hostname}"
        else:
            netloc = f"***@{hostname}"
            
        # Add port if it exists
        if parsed.port:
            netloc += f":{parsed.port}"
            
        # Reconstruct the URL with redacted password
        redacted_parsed = parsed._replace(netloc=netloc)
        return urlunparse(redacted_parsed)
        
    except Exception:
        # If parsing fails, return a generic message to avoid exposing sensitive info
        return "[REDACTED_DATABASE_URL]"


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./openmemory.db")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in environment")

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
