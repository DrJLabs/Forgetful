#!/usr/bin/env python3
"""
Test Database Setup Script

This script sets up the test database for both local and CI environments.
It handles:
- Database creation and initialization
- Extension installation (pgvector)
- Schema migration
- Test data seeding
- Environment detection
"""

import os
import sys
import logging
import argparse
from pathlib import Path


# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import alembic.command
import alembic.config
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def detect_environment():
    """Detect the current environment (local, CI, docker)."""
    is_ci = os.getenv('CI', 'false').lower() == 'true'
    is_testing = os.getenv('TESTING', 'false').lower() == 'true'
    is_docker = os.path.exists('/.dockerenv')
    
    logger.info(f"Environment detection: CI={is_ci}, Testing={is_testing}, Docker={is_docker}")
    return is_ci, is_testing, is_docker

def get_database_config():
    """Get database configuration based on environment."""
    is_ci, is_testing, is_docker = detect_environment()
    
    if is_ci:
        # CI environment - use localhost
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'user': 'postgres',
            'password': 'testpass'
        }
    elif is_testing:
        # Local testing - use docker-compose services
        config = {
            'host': os.getenv('POSTGRES_HOST', 'postgres-mem0'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'mem0'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
        }
    else:
        # Production/development
        config = {
            'host': os.getenv('POSTGRES_HOST', 'postgres-mem0'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'mem0'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
        }
    
    logger.info(f"Database config: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
    return config

def wait_for_database(config, timeout=60):
    """Wait for database to be ready."""
    import time
    
    logger.info(f"Waiting for database at {config['host']}:{config['port']}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                database='postgres',  # Connect to default database first
                user=config['user'],
                password=config['password']
            )
            conn.close()
            logger.info("✅ Database is ready!")
            return True
        except psycopg2.OperationalError:
            logger.info("Database not ready, waiting...")
            time.sleep(2)
    
    logger.error(f"❌ Database not ready after {timeout} seconds")
    return False

def create_database_if_not_exists(config):
    """Create the target database if it doesn't exist."""
    try:
        # Connect to default postgres database
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database='postgres',
            user=config['user'],
            password=config['password']
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (config['database'],)
        )
        
        if not cursor.fetchone():
            logger.info(f"Creating database '{config['database']}'...")
            cursor.execute(f"CREATE DATABASE {config['database']}")
            logger.info("✅ Database created successfully")
        else:
            logger.info(f"Database '{config['database']}' already exists")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error creating database: {e}")
        return False
    
    return True

def install_extensions(config):
    """Install required PostgreSQL extensions."""
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        cursor = conn.cursor()
        
        # Install pgvector extension
        logger.info("Installing pgvector extension...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        
        # Install uuid-ossp extension
        logger.info("Installing uuid-ossp extension...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
        
        cursor.close()
        conn.close()
        
        logger.info("✅ Extensions installed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error installing extensions: {e}")
        return False

def run_migrations(config):
    """Run Alembic migrations."""
    try:
        # Set environment variables for Alembic
        database_url = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        os.environ['DATABASE_URL'] = database_url
        os.environ['TESTING'] = 'true'
        
        # Create Alembic configuration
        alembic_cfg = alembic.config.Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        
        logger.info("Running database migrations...")
        alembic.command.upgrade(alembic_cfg, "head")
        logger.info("✅ Migrations completed successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error running migrations: {e}")
        return False

def verify_database_setup(config):
    """Verify that the database is set up correctly."""
    try:
        database_url = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check pgvector extension
            result = conn.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'"))
            if not result.fetchone():
                logger.error("❌ pgvector extension not installed")
                return False
            
            # Check if basic tables exist
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name IN ('users', 'apps', 'memories')
            """))
            tables = [row[0] for row in result.fetchall()]
            
            expected_tables = ['users', 'apps', 'memories']
            missing_tables = [t for t in expected_tables if t not in tables]
            
            if missing_tables:
                logger.warning(f"⚠️  Missing tables: {missing_tables}")
            else:
                logger.info("✅ All expected tables present")
        
        logger.info("✅ Database setup verification completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error verifying database setup: {e}")
        return False

def clean_database(config):
    """Clean the database for testing."""
    try:
        database_url = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Truncate all tables
            logger.info("Cleaning database tables...")
            conn.execute(text("TRUNCATE TABLE memories, apps, users CASCADE"))
            conn.commit()
            
        logger.info("✅ Database cleaned successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error cleaning database: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Setup test database')
    parser.add_argument('--clean', action='store_true', help='Clean existing data')
    parser.add_argument('--verify-only', action='store_true', help='Only verify setup')
    parser.add_argument('--timeout', type=int, default=60, help='Database wait timeout')
    
    args = parser.parse_args()
    
    # Get database configuration
    config = get_database_config()
    
    # Wait for database to be ready
    if not wait_for_database(config, args.timeout):
        sys.exit(1)
    
    if args.verify_only:
        if verify_database_setup(config):
            logger.info("✅ Database setup is valid")
            sys.exit(0)
        else:
            logger.error("❌ Database setup is invalid")
            sys.exit(1)
    
    # Create database if it doesn't exist
    if not create_database_if_not_exists(config):
        sys.exit(1)
    
    # Install extensions
    if not install_extensions(config):
        sys.exit(1)
    
    # Run migrations
    if not run_migrations(config):
        sys.exit(1)
    
    # Clean database if requested
    if args.clean:
        if not clean_database(config):
            sys.exit(1)
    
    # Verify setup
    if not verify_database_setup(config):
        sys.exit(1)
    
    logger.info("🎉 Database setup completed successfully!")

if __name__ == '__main__':
    main()