import logging
import os

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
