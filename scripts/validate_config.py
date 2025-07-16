#!/usr/bin/env python3
"""
Configuration Validation Script for mem0-stack

This script validates all configuration settings before startup
to prevent runtime errors and deployment issues.

Features:
- Validates all environment variables
- Tests database connections
- Checks service connectivity
- Provides detailed error reporting
- Supports different validation levels

Usage:
    python scripts/validate_config.py
    python scripts/validate_config.py --level=full
    python scripts/validate_config.py --fix-issues
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from shared.config import Config, get_config
except ImportError:
    print("❌ Cannot import shared.config. Please ensure shared/config.py exists.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ValidationResult:
    """Stores validation results with severity levels."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.success: List[str] = []

    def add_error(self, message: str):
        """Add an error message."""
        self.errors.append(message)
        logger.error(message)

    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)
        logger.warning(message)

    def add_info(self, message: str):
        """Add an info message."""
        self.info.append(message)
        logger.info(message)

    def add_success(self, message: str):
        """Add a success message."""
        self.success.append(message)
        logger.info(f"✅ {message}")

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


def validate_basic_config(config: Config) -> ValidationResult:
    """Validate basic configuration settings."""
    result = ValidationResult()

    result.add_info("Starting basic configuration validation...")

    # Check required variables
    required_vars = [
        ("DATABASE_USER", config.DATABASE_USER),
        ("DATABASE_PASSWORD", config.DATABASE_PASSWORD),
        ("NEO4J_PASSWORD", config.NEO4J_PASSWORD),
        ("OPENAI_API_KEY", config.OPENAI_API_KEY),
        ("APP_USER_ID", config.APP_USER_ID),
    ]

    for var_name, var_value in required_vars:
        if not var_value or var_value.strip() == "":
            result.add_error(f"Required variable {var_name} is not set")
        else:
            result.add_success(f"{var_name} is configured")

    # Validate specific formats
    if config.OPENAI_API_KEY and not config.OPENAI_API_KEY.startswith("sk-"):
        result.add_error("OPENAI_API_KEY must start with 'sk-'")

    if config.DATABASE_PORT < 1024 or config.DATABASE_PORT > 65535:
        result.add_error(
            f"DATABASE_PORT {config.DATABASE_PORT} is not in valid range (1024-65535)"
        )

    if config.NEO4J_PORT < 1024 or config.NEO4J_PORT > 65535:
        result.add_error(
            f"NEO4J_PORT {config.NEO4J_PORT} is not in valid range (1024-65535)"
        )

    # Validate URLs
    service_urls = [
        ("MEM0_API_URL", config.MEM0_API_URL),
        ("OPENMEMORY_API_URL", config.OPENMEMORY_API_URL),
        ("OPENMEMORY_UI_URL", config.OPENMEMORY_UI_URL),
    ]

    for url_name, url_value in service_urls:
        if not url_value.startswith(("http://", "https://")):
            result.add_error(f"{url_name} must start with http:// or https://")
        else:
            result.add_success(f"{url_name} format is valid")

    return result


def validate_database_connection(config: Config) -> ValidationResult:
    """Test database connectivity."""
    result = ValidationResult()

    result.add_info("Testing database connectivity...")

    try:
        import psycopg2

        # Test PostgreSQL connection
        try:
            conn_params = {
                "host": config.DATABASE_HOST,
                "port": config.DATABASE_PORT,
                "database": config.DATABASE_NAME,
                "user": config.DATABASE_USER,
                "password": config.DATABASE_PASSWORD,
            }

            conn = psycopg2.connect(**conn_params, connect_timeout=10)

            # Test basic query
            cur = conn.cursor()
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            cur.close()
            conn.close()

            result.add_success(f"PostgreSQL connection successful ({version[:50]}...)")

            # Test pgvector extension
            conn = psycopg2.connect(**conn_params)
            cur = conn.cursor()

            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                conn.commit()
                cur.execute(
                    "SELECT version() FROM pg_extension WHERE extname = 'vector';"
                )
                vector_version = cur.fetchone()

                if vector_version:
                    result.add_success("pgvector extension available")
                else:
                    result.add_warning("pgvector extension not found")

            except Exception as e:
                result.add_warning(f"pgvector extension test failed: {str(e)}")

            cur.close()
            conn.close()

        except psycopg2.OperationalError as e:
            result.add_error(f"PostgreSQL connection failed: {str(e)}")
        except Exception as e:
            result.add_error(f"Database test error: {str(e)}")

    except ImportError:
        result.add_warning("psycopg2 not installed, skipping database connection test")

    return result


def validate_neo4j_connection(config: Config) -> ValidationResult:
    """Test Neo4j connectivity."""
    result = ValidationResult()

    result.add_info("Testing Neo4j connectivity...")

    try:
        from neo4j import GraphDatabase

        try:
            driver = GraphDatabase.driver(
                config.neo4j_bolt_url,
                auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD),
                connection_timeout=10,
            )

            # Test connection
            with driver.session() as session:
                result_obj = session.run("RETURN 'Hello, Neo4j!' AS message")
                message = result_obj.single()["message"]

                result.add_success(f"Neo4j connection successful: {message}")

            driver.close()

        except Exception as e:
            result.add_error(f"Neo4j connection failed: {str(e)}")

    except ImportError:
        result.add_warning("neo4j driver not installed, skipping Neo4j connection test")

    return result


def validate_openai_connection(config: Config) -> ValidationResult:
    """Test OpenAI API connectivity."""
    result = ValidationResult()

    result.add_info("Testing OpenAI API connectivity...")

    try:
        import openai

        try:
            client = openai.OpenAI(api_key=config.OPENAI_API_KEY, timeout=10)

            # Test API with a minimal request
            response = client.models.list()
            models = [model.id for model in response.data]

            if config.OPENAI_MODEL in models:
                result.add_success(
                    f"OpenAI API connection successful, model {config.OPENAI_MODEL} available"
                )
            else:
                result.add_warning(
                    f"OpenAI API connected but model {config.OPENAI_MODEL} not found in available models"
                )

            if config.OPENAI_EMBEDDING_MODEL in models:
                result.add_success(
                    f"Embedding model {config.OPENAI_EMBEDDING_MODEL} available"
                )
            else:
                result.add_warning(
                    f"Embedding model {config.OPENAI_EMBEDDING_MODEL} not found"
                )

        except Exception as e:
            result.add_error(f"OpenAI API test failed: {str(e)}")

    except ImportError:
        result.add_warning("openai package not installed, skipping API connection test")

    return result


def validate_service_urls(config: Config) -> ValidationResult:
    """Test service URL accessibility."""
    result = ValidationResult()

    result.add_info("Testing service URL accessibility...")

    try:
        import requests

        service_urls = [
            ("mem0 API", config.MEM0_API_URL),
            ("OpenMemory API", config.OPENMEMORY_API_URL),
            ("OpenMemory UI", config.OPENMEMORY_UI_URL),
        ]

        for service_name, url in service_urls:
            try:
                # Try to reach the service
                response = requests.get(
                    f"{url}/health" if not url.endswith("/") else f"{url}health",
                    timeout=5,
                )

                if response.status_code < 500:
                    result.add_success(
                        f"{service_name} is accessible ({response.status_code})"
                    )
                else:
                    result.add_warning(
                        f"{service_name} returned {response.status_code}"
                    )

            except requests.exceptions.ConnectionError:
                result.add_warning(f"{service_name} is not running or not accessible")
            except requests.exceptions.Timeout:
                result.add_warning(f"{service_name} connection timeout")
            except Exception as e:
                result.add_warning(f"{service_name} test failed: {str(e)}")

    except ImportError:
        result.add_warning("requests package not installed, skipping service URL tests")

    return result


def validate_file_permissions() -> ValidationResult:
    """Validate file and directory permissions."""
    result = ValidationResult()

    result.add_info("Checking file permissions...")

    # Check critical directories and files
    paths_to_check = [
        (".env", "file"),
        ("data", "directory"),
        ("data/postgres", "directory"),
        ("data/neo4j", "directory"),
        ("shared/config.py", "file"),
        ("scripts", "directory"),
    ]

    for path, path_type in paths_to_check:
        full_path = project_root / path

        if path_type == "directory":
            if full_path.exists() and full_path.is_dir():
                if os.access(full_path, os.R_OK | os.W_OK):
                    result.add_success(f"Directory {path} has correct permissions")
                else:
                    result.add_error(f"Directory {path} has incorrect permissions")
            else:
                result.add_warning(f"Directory {path} does not exist")

        elif path_type == "file":
            if full_path.exists() and full_path.is_file():
                if os.access(full_path, os.R_OK):
                    result.add_success(f"File {path} is readable")
                else:
                    result.add_error(f"File {path} is not readable")
            else:
                if path == ".env":
                    result.add_warning(
                        f"File {path} does not exist (use env.template to create it)"
                    )
                else:
                    result.add_error(f"Required file {path} does not exist")

    return result


def generate_validation_report(results: List[ValidationResult], level: str) -> None:
    """Generate a comprehensive validation report."""

    print("\n" + "=" * 60)
    print("🔍 mem0-stack Configuration Validation Report")
    print("=" * 60)

    total_errors = sum(len(r.errors) for r in results)
    total_warnings = sum(len(r.warnings) for r in results)
    total_success = sum(len(r.success) for r in results)

    print("\n📊 Summary:")
    print(f"   ✅ Success: {total_success}")
    print(f"   ⚠️  Warnings: {total_warnings}")
    print(f"   ❌ Errors: {total_errors}")

    # Show detailed results
    for i, result in enumerate(results):
        if result.errors or result.warnings or (level == "verbose" and result.success):
            print(f"\n{'─' * 40}")

            if result.errors:
                print("\n❌ Errors:")
                for error in result.errors:
                    print(f"   • {error}")

            if result.warnings:
                print("\n⚠️  Warnings:")
                for warning in result.warnings:
                    print(f"   • {warning}")

            if level == "verbose" and result.success:
                print("\n✅ Success:")
                for success in result.success:
                    print(f"   • {success}")

    # Overall status
    print(f"\n{'=' * 60}")
    if total_errors == 0:
        if total_warnings == 0:
            print("🎉 Configuration validation PASSED! All systems ready.")
            exit_code = 0
        else:
            print("✅ Configuration validation PASSED with warnings.")
            print("   System should work but consider addressing warnings.")
            exit_code = 0
    else:
        print("❌ Configuration validation FAILED!")
        print("   Please fix the errors before starting the system.")
        exit_code = 1

    print("=" * 60)

    return exit_code


def fix_common_issues(config: Config) -> None:
    """Attempt to fix common configuration issues."""

    print("🔧 Attempting to fix common configuration issues...")

    fixes_applied = []

    # Create .env file from template if it doesn't exist
    env_file = project_root / ".env"
    env_template = project_root / "env.template"

    if not env_file.exists() and env_template.exists():
        try:
            import shutil

            shutil.copy(env_template, env_file)
            fixes_applied.append("Created .env file from template")
        except Exception as e:
            print(f"❌ Failed to create .env file: {e}")

    # Create data directories
    data_dirs = ["data", "data/postgres", "data/neo4j", "data/mem0"]

    for dir_path in data_dirs:
        full_path = project_root / dir_path
        if not full_path.exists():
            try:
                full_path.mkdir(parents=True, exist_ok=True)
                fixes_applied.append(f"Created directory {dir_path}")
            except Exception as e:
                print(f"❌ Failed to create directory {dir_path}: {e}")

    # Set appropriate permissions
    try:
        for dir_path in data_dirs:
            full_path = project_root / dir_path
            if full_path.exists():
                os.chmod(full_path, 0o755)

        fixes_applied.append("Set correct directory permissions")
    except Exception as e:
        print(f"❌ Failed to set permissions: {e}")

    if fixes_applied:
        print("✅ Applied fixes:")
        for fix in fixes_applied:
            print(f"   • {fix}")
    else:
        print("ℹ️  No automatic fixes were needed or possible.")


def main():
    """Main validation function."""

    parser = argparse.ArgumentParser(description="Validate mem0-stack configuration")
    parser.add_argument(
        "--level",
        choices=["basic", "full", "verbose"],
        default="full",
        help="Validation level (default: full)",
    )
    parser.add_argument(
        "--fix-issues",
        action="store_true",
        help="Attempt to fix common issues automatically",
    )
    parser.add_argument(
        "--skip-connections", action="store_true", help="Skip external connection tests"
    )

    args = parser.parse_args()

    print("🚀 Starting mem0-stack configuration validation...")
    print(f"📋 Validation level: {args.level}")

    if args.fix_issues:
        try:
            config = get_config()
            fix_common_issues(config)
        except Exception as e:
            print(f"⚠️  Could not load config for fixes: {e}")

    try:
        # Load configuration
        config = get_config()
        print("✅ Configuration loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        sys.exit(1)

    # Run validation tests
    results = []

    # Basic configuration validation
    results.append(validate_basic_config(config))

    if args.level in ["full", "verbose"]:
        # File permissions
        results.append(validate_file_permissions())

        if not args.skip_connections:
            # Connection tests
            results.append(validate_database_connection(config))
            results.append(validate_neo4j_connection(config))
            results.append(validate_openai_connection(config))
            results.append(validate_service_urls(config))

    # Generate report
    exit_code = generate_validation_report(results, args.level)

    if exit_code == 0:
        print("\n🎯 Next steps:")
        print("   1. Run: docker-compose up -d")
        print("   2. Test: python test_memory_system.py")
        print("   3. Monitor: docker-compose logs -f")
    else:
        print("\n🔧 Recommended actions:")
        print("   1. Fix the errors listed above")
        print("   2. Rerun: python scripts/validate_config.py")
        print("   3. Check: env.template for examples")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
