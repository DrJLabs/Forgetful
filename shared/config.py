"""
Shared Configuration System for mem0-stack

This module provides centralized configuration management with validation
for all mem0-stack services including mem0 core, OpenMemory API, and OpenMemory UI.

Features:
- Pydantic validation for all configuration values
- Environment variable parsing with fallbacks
- Service-specific configuration classes
- Comprehensive validation rules
- Easy integration across all services
"""

import os
from typing import Optional, Dict, Any, List
from pydantic import validator, Field
from pydantic_settings import BaseSettings
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseConfig(BaseSettings):
    """Base configuration with common validation patterns."""

    class Config:
        # Support multiple .env files
        env_file = [".env", ".env.local", ".env.development"]
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"  # Allow extra fields not defined in the model

    @validator("*", pre=True)
    def empty_str_to_none(cls, v):
        """Convert empty strings to None."""
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


class DatabaseConfig(BaseConfig):
    """Database configuration with validation."""

    # PostgreSQL Configuration
    DATABASE_HOST: str = Field(default="postgres-mem0", description="PostgreSQL host")
    DATABASE_PORT: int = Field(default=5432, description="PostgreSQL port")
    DATABASE_NAME: str = Field(default="mem0", description="PostgreSQL database name")
    DATABASE_USER: str = Field(..., description="PostgreSQL username")
    DATABASE_PASSWORD: str = Field(..., description="PostgreSQL password")

    # Connection pool settings
    DATABASE_POOL_SIZE: int = Field(
        default=20, description="Database connection pool size"
    )
    DATABASE_MAX_OVERFLOW: int = Field(
        default=10, description="Max overflow connections"
    )
    DATABASE_POOL_TIMEOUT: int = Field(
        default=30, description="Pool timeout in seconds"
    )

    @validator("DATABASE_PASSWORD")
    def validate_password(cls, v):
        """Validate database password strength."""
        if not v or len(v) < 8:
            raise ValueError("Database password must be at least 8 characters")
        return v

    @validator("DATABASE_PORT")
    def validate_port(cls, v):
        """Validate database port range."""
        if not 1024 <= v <= 65535:
            raise ValueError("Database port must be between 1024 and 65535")
        return v

    @property
    def database_url(self) -> str:
        """Generate database URL from components."""
        return f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"


class Neo4jConfig(BaseConfig):
    """Neo4j configuration with validation."""

    NEO4J_HOST: str = Field(default="neo4j-mem0", description="Neo4j host")
    NEO4J_PORT: int = Field(default=7687, description="Neo4j port")
    NEO4J_USERNAME: str = Field(default="neo4j", description="Neo4j username")
    NEO4J_PASSWORD: str = Field(..., description="Neo4j password")
    NEO4J_DATABASE: str = Field(default="neo4j", description="Neo4j database name")

    # Connection settings
    NEO4J_MAX_CONNECTIONS: int = Field(default=50, description="Max Neo4j connections")
    NEO4J_CONNECTION_TIMEOUT: int = Field(default=30, description="Connection timeout")

    @validator("NEO4J_PASSWORD")
    def validate_password(cls, v):
        """Validate Neo4j password."""
        if not v or len(v) < 4:
            raise ValueError("Neo4j password must be at least 4 characters")
        return v

    @property
    def neo4j_url(self) -> str:
        """Generate Neo4j URL from components."""
        return f"neo4j://{self.NEO4J_USERNAME}:{self.NEO4J_PASSWORD}@{self.NEO4J_HOST}:{self.NEO4J_PORT}"

    @property
    def neo4j_bolt_url(self) -> str:
        """Generate Neo4j Bolt URL from components."""
        return f"bolt://{self.NEO4J_HOST}:{self.NEO4J_PORT}"

    @property
    def neo4j_auth(self) -> str:
        """Generate Neo4j auth string for legacy compatibility."""
        return f"{self.NEO4J_USERNAME}/{self.NEO4J_PASSWORD}"


class OpenAIConfig(BaseConfig):
    """OpenAI configuration with validation."""

    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="OpenAI LLM model")
    OPENAI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small", description="OpenAI embedding model"
    )
    OPENAI_MAX_TOKENS: int = Field(default=2000, description="Max tokens for responses")
    OPENAI_TEMPERATURE: float = Field(
        default=0.1, description="Temperature for responses"
    )

    # API settings
    OPENAI_REQUEST_TIMEOUT: int = Field(
        default=30, description="Request timeout in seconds"
    )
    OPENAI_MAX_RETRIES: int = Field(default=3, description="Max retry attempts")

    @validator("OPENAI_API_KEY")
    def validate_api_key(cls, v):
        """Validate OpenAI API key format."""
        if not v or not v.startswith("sk-"):
            raise ValueError("Invalid OpenAI API key format (must start with sk-)")
        return v

    @validator("OPENAI_TEMPERATURE")
    def validate_temperature(cls, v):
        """Validate temperature range."""
        if not 0.0 <= v <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v

    @validator("OPENAI_MAX_TOKENS")
    def validate_max_tokens(cls, v):
        """Validate max tokens."""
        if not 1 <= v <= 4000:
            raise ValueError("Max tokens must be between 1 and 4000")
        return v


class AppConfig(BaseConfig):
    """Application configuration."""

    # Application identity
    APP_USER_ID: str = Field(default="default_user", description="Default user ID")
    APP_ENVIRONMENT: str = Field(
        default="development",
        description="Environment (development/staging/production)",
    )
    APP_DEBUG: bool = Field(default=False, description="Debug mode")
    APP_LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # Security settings
    APP_SECRET_KEY: Optional[str] = Field(None, description="Application secret key")
    APP_API_KEY: Optional[str] = Field(
        None, description="Optional API key for authentication"
    )

    @validator("APP_LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @validator("APP_ENVIRONMENT")
    def validate_environment(cls, v):
        """Validate environment."""
        valid_envs = ["development", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of: {valid_envs}")
        return v.lower()


class ServiceUrlConfig(BaseConfig):
    """Service URL configuration."""

    # Internal service URLs
    MEM0_API_URL: str = Field(
        default="http://localhost:8000", description="mem0 API URL"
    )
    OPENMEMORY_API_URL: str = Field(
        default="http://localhost:8765", description="OpenMemory API URL"
    )
    OPENMEMORY_UI_URL: str = Field(
        default="http://localhost:3000", description="OpenMemory UI URL"
    )

    # External service URLs
    REDIS_URL: Optional[str] = Field(None, description="Redis URL for caching")
    ELASTICSEARCH_URL: Optional[str] = Field(
        None, description="Elasticsearch URL for search"
    )

    @validator("MEM0_API_URL", "OPENMEMORY_API_URL", "OPENMEMORY_UI_URL")
    def validate_urls(cls, v):
        """Validate URL format."""
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URLs must start with http:// or https://")
        return v


class FrontendConfig(BaseConfig):
    """Frontend (Next.js) configuration."""

    # Next.js public environment variables
    NEXT_PUBLIC_API_URL: str = Field(
        default="http://localhost:8765", description="Public API URL"
    )
    NEXT_PUBLIC_USER_ID: str = Field(
        default="default_user", description="Public user ID"
    )
    NEXT_PUBLIC_ENVIRONMENT: str = Field(
        default="development", description="Public environment"
    )

    # Build settings
    NEXT_PUBLIC_BUILD_TIME: Optional[str] = Field(None, description="Build timestamp")
    NEXT_PUBLIC_VERSION: Optional[str] = Field(None, description="Application version")


class DockerConfig(BaseConfig):
    """Docker Compose configuration."""

    COMPOSE_PROJECT_NAME: str = Field(
        default="mem0-stack", description="Docker Compose project name"
    )

    # Legacy compatibility variables
    POSTGRES_USER: Optional[str] = Field(None, description="Legacy PostgreSQL user")
    POSTGRES_PASSWORD: Optional[str] = Field(
        None, description="Legacy PostgreSQL password"
    )
    POSTGRES_DB: Optional[str] = Field(None, description="Legacy PostgreSQL database")
    USER: Optional[str] = Field(None, description="Legacy user variable")
    NEO4J_AUTH: Optional[str] = Field(None, description="Legacy Neo4j auth")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Auto-populate legacy variables from main config
        if hasattr(self, "_database_config"):
            self.POSTGRES_USER = self._database_config.DATABASE_USER
            self.POSTGRES_PASSWORD = self._database_config.DATABASE_PASSWORD
            self.POSTGRES_DB = self._database_config.DATABASE_NAME
        if hasattr(self, "_app_config"):
            self.USER = self._app_config.APP_USER_ID
        if hasattr(self, "_neo4j_config"):
            self.NEO4J_AUTH = self._neo4j_config.neo4j_auth


class Config(
    DatabaseConfig,
    Neo4jConfig,
    OpenAIConfig,
    AppConfig,
    ServiceUrlConfig,
    FrontendConfig,
    DockerConfig,
):
    """Combined configuration for all services."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Store config sections for legacy compatibility
        self._database_config = self
        self._neo4j_config = self
        self._app_config = self

        # Auto-populate legacy variables
        if not self.POSTGRES_USER:
            self.POSTGRES_USER = self.DATABASE_USER
        if not self.POSTGRES_PASSWORD:
            self.POSTGRES_PASSWORD = self.DATABASE_PASSWORD
        if not self.POSTGRES_DB:
            self.POSTGRES_DB = self.DATABASE_NAME
        if not self.USER:
            self.USER = self.APP_USER_ID
        if not self.NEO4J_AUTH:
            self.NEO4J_AUTH = self.neo4j_auth
        if not self.NEXT_PUBLIC_USER_ID:
            self.NEXT_PUBLIC_USER_ID = self.APP_USER_ID

    def get_mem0_config(self) -> Dict[str, Any]:
        """Generate mem0 configuration dictionary."""
        return {
            "version": "v1.1",
            "llm": {
                "provider": "openai",
                "config": {
                    "model": self.OPENAI_MODEL,
                    "temperature": self.OPENAI_TEMPERATURE,
                    "max_tokens": self.OPENAI_MAX_TOKENS,
                    "api_key": self.OPENAI_API_KEY,
                    "request_timeout": self.OPENAI_REQUEST_TIMEOUT,
                    "max_retries": self.OPENAI_MAX_RETRIES,
                },
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "model": self.OPENAI_EMBEDDING_MODEL,
                    "api_key": self.OPENAI_API_KEY,
                },
            },
            "vector_store": {
                "provider": "pgvector",
                "config": {
                    "host": self.DATABASE_HOST,
                    "port": self.DATABASE_PORT,
                    "dbname": self.DATABASE_NAME,
                    "user": self.DATABASE_USER,
                    "password": self.DATABASE_PASSWORD,
                    "collection_name": "memories",
                    "embedding_model_dims": 1536,
                },
            },
            "graph_store": {
                "provider": "neo4j",
                "config": {
                    "url": self.neo4j_url,
                    "username": self.NEO4J_USERNAME,
                    "password": self.NEO4J_PASSWORD,
                    "database": self.NEO4J_DATABASE,
                },
            },
        }

    def validate_all(self) -> List[str]:
        """Validate all configuration and return any errors."""
        errors = []

        try:
            # Test database connection parameters
            if not self.DATABASE_USER or not self.DATABASE_PASSWORD:
                errors.append("Database credentials are required")

            # Test Neo4j connection parameters
            if not self.NEO4J_PASSWORD:
                errors.append("Neo4j password is required")

            # Test OpenAI API key
            if not self.OPENAI_API_KEY or not self.OPENAI_API_KEY.startswith("sk-"):
                errors.append("Valid OpenAI API key is required")

            # Test service URLs
            for url_field in [
                "MEM0_API_URL",
                "OPENMEMORY_API_URL",
                "OPENMEMORY_UI_URL",
            ]:
                url = getattr(self, url_field)
                if not url.startswith(("http://", "https://")):
                    errors.append(f"{url_field} must be a valid URL")

        except Exception as e:
            errors.append(f"Configuration validation error: {str(e)}")

        return errors


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()

        # Validate configuration
        errors = _config.validate_all()
        if errors:
            logger.warning(f"Configuration validation errors: {errors}")
            # Don't raise exception in production, just log warnings
            if _config.APP_ENVIRONMENT == "development":
                logger.error("Configuration errors detected in development mode")

    return _config


def reload_config() -> Config:
    """Reload the global configuration."""
    global _config
    _config = None
    return get_config()


# Convenience function for backward compatibility
config = get_config
