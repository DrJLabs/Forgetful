#!/usr/bin/env python3
"""
Test database setup script for OpenMemory API
This script sets up test databases for development and testing purposes.
"""

import logging
import os
import re
import sys

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_database_config():
    """Get database configuration from environment variables."""
    config = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "password"),
        "database": os.getenv("POSTGRES_DB", "openmemory_test"),
        "admin_database": os.getenv("POSTGRES_ADMIN_DB", "postgres"),
    }
    return config


def connect_to_admin_database(config):
    """Connect to the admin database to create new databases."""
    try:
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["admin_database"],
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn
    except psycopg2.Error as e:
        logger.error(f"Failed to connect to admin database: {e}")
        raise


def validate_database_name(db_name):
    """
    Validate database name according to PostgreSQL naming conventions.

    Args:
        db_name (str): Database name to validate

    Returns:
        bool: True if valid, False otherwise

    Raises:
        ValueError: If database name is invalid
    """
    if not db_name:
        raise ValueError("Database name cannot be empty")

    if len(db_name) > 63:
        raise ValueError("Database name cannot exceed 63 characters")

    # PostgreSQL identifier rules:
    # - Must start with a letter (a-z) or underscore
    # - Can contain letters, digits, underscores, and dollar signs
    # - Cannot be a reserved keyword (basic check)
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_$]*$", db_name):
        raise ValueError(
            "Database name must start with a letter or underscore and contain only "
            "letters, numbers, underscores, and dollar signs"
        )

    # Check for common PostgreSQL reserved keywords
    reserved_keywords = {
        "user",
        "table",
        "database",
        "schema",
        "index",
        "view",
        "trigger",
        "function",
        "procedure",
        "select",
        "insert",
        "update",
        "delete",
        "create",
        "drop",
        "alter",
        "grant",
        "revoke",
        "commit",
        "rollback",
    }

    if db_name.lower() in reserved_keywords:
        raise ValueError(f"Database name '{db_name}' is a reserved keyword")

    return True


def database_exists(cursor, db_name):
    """Check if a database already exists."""
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
    return cursor.fetchone() is not None


def create_database_if_not_exists(config):
    """Create database if it doesn't exist."""
    conn = None
    try:
        # Validate database name before proceeding
        validate_database_name(config["database"])

        conn = connect_to_admin_database(config)
        cursor = conn.cursor()

        if not database_exists(cursor, config["database"]):
            logger.info(f"Creating database: {config['database']}")

            # SECURE CODE - Use psycopg2.sql.Identifier for proper SQL identifier escaping
            # This prevents SQL injection by properly escaping database identifiers
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(config["database"]))
            )

            logger.info(f"Database '{config['database']}' created successfully")
        else:
            logger.info(f"Database '{config['database']}' already exists")

    except ValueError as e:
        logger.error(f"Invalid database name: {e}")
        raise
    except psycopg2.Error as e:
        logger.error(f"Error creating database: {e}")
        raise
    finally:
        if conn:
            conn.close()


def create_test_tables(config):
    """Create test tables in the database."""
    try:
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
        )

        cursor = conn.cursor()

        # Create pgvector extension
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()

        # Create test table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS test_memories (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                embedding vector(1536),
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.commit()
        logger.info("Test tables created successfully")

    except psycopg2.Error as e:
        logger.error(f"Error creating test tables: {e}")
        raise
    finally:
        if conn:
            conn.close()


def setup_test_database():
    """Main function to setup test database."""
    try:
        config = get_database_config()

        logger.info("Setting up test database...")
        logger.info(f"Target database: {config['database']}")

        # Create database if it doesn't exist
        create_database_if_not_exists(config)

        # Create test tables
        create_test_tables(config)

        logger.info("Test database setup completed successfully")

    except Exception as e:
        logger.error(f"Test database setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    setup_test_database()
