import os
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

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
