"""
Memory client utilities for OpenMemory.

This module provides functionality to initialize and manage the Mem0 memory client
with automatic configuration management and Docker environment support.

Docker Ollama Configuration:
When running inside a Docker container and using Ollama as the LLM or embedder provider,
the system automatically detects the Docker environment and adjusts localhost URLs
to properly reach the host machine where Ollama is running.

Supported Docker host resolution (in order of preference):
1. OLLAMA_HOST environment variable (if set)
2. host.docker.internal (Docker Desktop for Mac/Windows)
3. Docker bridge gateway IP (typically 172.17.0.1 on Linux)
4. Fallback to 172.17.0.1

Example configuration that will be automatically adjusted:
{
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "llama3.1:latest",
            "ollama_base_url": "http://localhost:11434"  # Auto-adjusted in Docker
        }
    }
}
"""

import hashlib
import json
import os
import socket

from app.database import SessionLocal
from app.models import Config as ConfigModel
from mem0 import Memory
from shared.errors import ExternalServiceError, handle_error

# Agent 4 Integration - Structured Logging and Error Handling
from shared.logging_system import get_logger, performance_logger
from shared.resilience import CircuitBreakerConfig, RetryPolicy, circuit_breaker, retry

# Replace standard logging with structured logging
logger = get_logger("memory_utils")


_memory_client = None
_config_hash = None


def _get_config_hash(config_dict):
    """Generate a hash of the config to detect changes."""
    config_str = json.dumps(config_dict, sort_keys=True)
    return hashlib.md5(config_str.encode()).hexdigest()  # noqa: S324


def _get_docker_host_url():
    """
    Determine the appropriate host URL to reach host machine from inside Docker container.
    Returns the best available option for reaching the host from inside a container.
    """
    # Check for custom environment variable first
    custom_host = os.environ.get("OLLAMA_HOST")
    if custom_host:
        print(f"Using custom Ollama host from OLLAMA_HOST: {custom_host}")
        return custom_host.replace("http://", "").replace("https://", "").split(":")[0]

    # Check if we're running inside Docker
    if not os.path.exists("/.dockerenv"):
        # Not in Docker, return localhost as-is
        return "localhost"

    print("Detected Docker environment, adjusting host URL for Ollama...")

    # Try different host resolution strategies
    host_candidates = []

    # 1. host.docker.internal (works on Docker Desktop for Mac/Windows)
    try:
        socket.gethostbyname("host.docker.internal")
        host_candidates.append("host.docker.internal")
        print("Found host.docker.internal")
    except socket.gaierror:
        pass

    # 2. Docker bridge gateway (typically 172.17.0.1 on Linux)
    try:
        with open("/proc/net/route") as f:
            for line in f:
                fields = line.strip().split()
                if fields[1] == "00000000":  # Default route
                    gateway_hex = fields[2]
                    gateway_ip = socket.inet_ntoa(bytes.fromhex(gateway_hex)[::-1])
                    host_candidates.append(gateway_ip)
                    print(f"Found Docker gateway: {gateway_ip}")
                    break
    except (FileNotFoundError, IndexError, ValueError):
        pass

    # 3. Fallback to common Docker bridge IP
    if not host_candidates:
        host_candidates.append("172.17.0.1")
        print("Using fallback Docker bridge IP: 172.17.0.1")

    # Return the first available candidate
    return host_candidates[0]


def _fix_ollama_urls(config_section):
    """
    Fix Ollama URLs for Docker environment.
    Replaces localhost URLs with appropriate Docker host URLs.
    Sets default ollama_base_url if not provided.
    """
    if not config_section or "config" not in config_section:
        return config_section

    ollama_config = config_section["config"]

    # Set default ollama_base_url if not provided
    if "ollama_base_url" not in ollama_config:
        ollama_config["ollama_base_url"] = "http://host.docker.internal:11434"
    else:
        # Check for ollama_base_url and fix if it's localhost
        url = ollama_config["ollama_base_url"]
        if "localhost" in url or "127.0.0.1" in url:
            docker_host = _get_docker_host_url()
            if docker_host != "localhost":
                new_url = url.replace("localhost", docker_host).replace(
                    "127.0.0.1", docker_host
                )
                ollama_config["ollama_base_url"] = new_url
                print(f"Adjusted Ollama URL from {url} to {new_url}")

    return config_section


def reset_memory_client():
    """Reset the global memory client to force reinitialization with new config."""
    global _memory_client, _config_hash
    _memory_client = None
    _config_hash = None


def get_default_memory_config():
    """Get default memory client configuration with sensible defaults."""
    return {
        "vector_store": {
            "provider": "pgvector",
            "config": {
                "collection_name": "openmemory",
                "host": os.environ.get("POSTGRES_HOST", "postgres-mem0"),
                "port": 5432,
                "user": os.environ.get("POSTGRES_USER", "postgres"),
                "password": os.environ.get("POSTGRES_PASSWORD", "postgres"),
                "dbname": os.environ.get("POSTGRES_DB", "mem0"),
                "embedding_model_dims": 1536,  # OpenAI text-embedding-3-small dimensions
            },
        },
        "graph_store": {
            "provider": "neo4j",
            "config": {
                "url": os.environ.get("NEO4J_URL", "neo4j://neo4j-mem0:7687"),
                "username": os.environ.get("NEO4J_AUTH", "neo4j/password").split("/")[
                    0
                ],
                "password": os.environ.get("NEO4J_AUTH", "neo4j/password").split("/")[
                    1
                ],
                "database": "neo4j",
            },
        },
        "llm": {
            "provider": "openai",
            "config": {
                "model": "gpt-4o-mini",
                "temperature": 0.1,
                "max_tokens": 2000,
                "api_key": "env:OPENAI_API_KEY",
            },
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "text-embedding-3-small",
                "api_key": "env:OPENAI_API_KEY",
            },
        },
        "version": "v1.1",
    }


def _parse_environment_variables(config_dict):
    """
    Parse environment variables in config values.
    Converts 'env:VARIABLE_NAME' to actual environment variable values.
    """
    if isinstance(config_dict, dict):
        parsed_config = {}
        for key, value in config_dict.items():
            if isinstance(value, str) and value.startswith("env:"):
                env_var = value.split(":", 1)[1]
                env_value = os.environ.get(env_var)
                if env_value:
                    parsed_config[key] = env_value
                    if key.lower() in {"password", "api_key"}:
                        logger.info(
                            f"Loaded {env_var} from environment for {key}, but value is masked in logs"
                        )
                    else:
                        logger.info(f"Loaded {env_var} from environment for {key}")
                else:
                    logger.warning(
                        f"Environment variable {env_var} not found, keeping original value"
                    )
                    parsed_config[key] = value
            elif isinstance(value, dict):
                parsed_config[key] = _parse_environment_variables(value)
            else:
                parsed_config[key] = value
        return parsed_config
    return config_dict


@retry(RetryPolicy(max_attempts=3, initial_delay=1.0))
@circuit_breaker(CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60))
def get_memory_client(custom_instructions: str = None):
    """
    Get memory client with Agent 4 resilience patterns
    """
    global _memory_client, _config_hash

    try:
        with performance_logger.timer("memory_client_initialization"):
            # Start with default configuration
            config = get_default_memory_config()

            # Variable to track custom instructions
            db_custom_instructions = None

            # Load configuration from database
            try:
                db = SessionLocal()
                db_config = (
                    db.query(ConfigModel).filter(ConfigModel.key == "main").first()
                )

                if db_config:
                    json_config = db_config.value

                    # Extract custom instructions from openmemory settings
                    if (
                        "openmemory" in json_config
                        and "custom_instructions" in json_config["openmemory"]
                    ):
                        db_custom_instructions = json_config["openmemory"][
                            "custom_instructions"
                        ]

                    # Override defaults with configurations from the database
                    if "mem0" in json_config:
                        mem0_config = json_config["mem0"]

                        # Update vector_store configuration if available
                        if (
                            "vector_store" in mem0_config
                            and mem0_config["vector_store"] is not None
                        ):
                            config["vector_store"] = mem0_config["vector_store"]
                            logger.info(
                                f"Loaded vector_store provider from database: {config['vector_store']['provider']}"
                            )
                        else:
                            # Ensure we're using pgvector as default, not qdrant
                            logger.info(
                                "No vector_store config in database, using default provider: pgvector"
                            )

                        # Update LLM configuration if available
                        if "llm" in mem0_config and mem0_config["llm"] is not None:
                            config["llm"] = mem0_config["llm"]

                            # Fix Ollama URLs for Docker if needed
                            if config["llm"].get("provider") == "ollama":
                                config["llm"] = _fix_ollama_urls(config["llm"])

                        # Update Embedder configuration if available
                        if (
                            "embedder" in mem0_config
                            and mem0_config["embedder"] is not None
                        ):
                            config["embedder"] = mem0_config["embedder"]

                            # Fix Ollama URLs for Docker if needed
                            if config["embedder"].get("provider") == "ollama":
                                config["embedder"] = _fix_ollama_urls(
                                    config["embedder"]
                                )
                else:
                    print("No configuration found in database, using defaults")

                db.close()

            except Exception as e:
                print(f"Warning: Error loading configuration from database: {e}")
                print("Using default configuration")
                # Continue with default configuration if database config can't be loaded

            # Use custom_instructions parameter first, then fall back to database value
            instructions_to_use = custom_instructions or db_custom_instructions
            if instructions_to_use:
                config["custom_fact_extraction_prompt"] = instructions_to_use

            # ALWAYS parse environment variables in the final config
            # This ensures that even default config values like "env:OPENAI_API_KEY" get parsed
            logger.info("Parsing environment variables in final config...")
            config = _parse_environment_variables(config)

            # Debug: Show the final vector store configuration being used
            logger.info(
                f"Final vector_store configuration: provider={config['vector_store']['provider']}"
            )
            sanitized_config = config["vector_store"]["config"].copy()
            if "password" in sanitized_config:
                sanitized_config["password"] = "*****"  # noqa: S105
            logger.info(f"Vector store config details: {sanitized_config}")

            # Check if config has changed by comparing hashes
            current_config_hash = _get_config_hash(config)

            # Only reinitialize if config changed or client doesn't exist
            if _memory_client is None or _config_hash != current_config_hash:
                logger.info(
                    f"Initializing memory client with config hash: {current_config_hash}"
                )
                try:
                    _memory_client = Memory.from_config(config_dict=config)
                    _config_hash = current_config_hash
                    logger.info("Memory client initialized successfully")
                except Exception as init_error:
                    logger.warning(f"Failed to initialize memory client: {init_error}")
                    logger.warning(
                        "Server will continue running with limited memory functionality"
                    )
                    _memory_client = None
                    _config_hash = None
                    return None

            return _memory_client

    except Exception as e:
        structured_error = handle_error(
            e,
            {
                "operation": "memory_client_initialization",
                "custom_instructions": bool(custom_instructions),
            },
        )
        logger.error(
            "Memory client initialization failed", error=structured_error.to_dict()
        )
        raise ExternalServiceError(
            "Memory service unavailable", service_name="mem0_client"
        ) from e


def get_default_user_id():
    return "default_user"
