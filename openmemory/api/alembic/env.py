import os
import sys
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Import your models here
from app.database import Base
from app.models import *  # Import all your models

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def get_database_url_for_migration():
    """Get database URL for migrations with environment detection."""
    # Check if we're in CI environment
    is_ci = os.getenv("CI", "false").lower() == "true"
    is_testing = os.getenv("TESTING", "false").lower() == "true"
    
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        return database_url
    
    if is_testing and is_ci:
        # CI environment - use localhost for GitHub Actions services
        return "postgresql://postgres:testpass@localhost:5432/test_db"
    elif is_testing:
        # Local testing - use test database
        return "sqlite:///./test_openmemory.db"
    else:
        # Production/development - use docker-compose hostnames
        postgres_host = os.getenv("POSTGRES_HOST", "postgres-mem0")
        postgres_port = os.getenv("POSTGRES_PORT", "5432")
        postgres_db = os.getenv("POSTGRES_DB", "mem0")
        postgres_user = os.getenv("POSTGRES_USER", "postgres")
        postgres_password = os.getenv("POSTGRES_PASSWORD", "postgres")
        
        return f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url_for_migration()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=url.startswith("sqlite"),  # Enable batch mode for SQLite
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section)
    database_url = get_database_url_for_migration()
    configuration["sqlalchemy.url"] = database_url
    
    # Configure connection pooling for PostgreSQL
    if database_url.startswith("postgresql"):
        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
    else:
        # SQLite configuration
        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.StaticPool,
            connect_args={"check_same_thread": False},
        )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=database_url.startswith("sqlite"),  # Enable batch mode for SQLite
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
