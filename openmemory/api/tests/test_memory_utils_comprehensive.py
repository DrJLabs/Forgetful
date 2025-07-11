"""
Comprehensive Unit Tests for Memory Utility Functions
=========================================================

This test suite provides comprehensive coverage for all memory utility functions,
including memory client management, configuration handling, Docker environment
detection, and error scenarios.

Test Coverage Areas:
1. Memory Client Initialization & Configuration
2. Docker Environment Detection & URL Fixing
3. Configuration Parsing & Environment Variables
4. Error Handling & Resilience Patterns
5. Default Configuration Management
6. Circuit Breaker & Retry Logic
"""

import pytest
import os
import json
import socket
import hashlib
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime, UTC

from app.utils.memory import (
    get_memory_client,
    get_default_memory_config,
    reset_memory_client,
    _get_config_hash,
    _get_docker_host_url,
    _fix_ollama_urls,
    _parse_environment_variables,
    get_default_user_id,
)


@pytest.mark.unit
class TestMemoryClientInitialization:
    """Test memory client initialization and configuration"""

    def setup_method(self):
        """Reset global variables before each test"""
        reset_memory_client()

    def test_get_memory_client_success(self):
        """Test successful memory client initialization"""
        with patch("app.utils.memory.Memory") as mock_memory_class:
            mock_client = MagicMock()
            mock_memory_class.from_config.return_value = mock_client

            with patch("app.utils.memory.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.filter.return_value.first.return_value = None

                client = get_memory_client()

                assert client == mock_client
                mock_memory_class.from_config.assert_called_once()

    def test_get_memory_client_with_custom_instructions(self):
        """Test memory client with custom instructions"""
        custom_instructions = "Test custom instructions"

        with patch("app.utils.memory.Memory") as mock_memory_class:
            mock_client = MagicMock()
            mock_memory_class.from_config.return_value = mock_client

            with patch("app.utils.memory.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.filter.return_value.first.return_value = None

                client = get_memory_client(custom_instructions)

                assert client == mock_client
                # Verify custom instructions were used in config
                config_call = mock_memory_class.from_config.call_args[1]["config_dict"]
                assert (
                    config_call["custom_fact_extraction_prompt"] == custom_instructions
                )

    def test_get_memory_client_database_config_override(self):
        """Test memory client with database configuration override"""
        db_config = {
            "mem0": {"llm": {"provider": "openai", "config": {"model": "gpt-4"}}},
            "openmemory": {"custom_instructions": "Database instructions"},
        }

        with patch("app.utils.memory.Memory") as mock_memory_class:
            mock_client = MagicMock()
            mock_memory_class.from_config.return_value = mock_client

            with patch("app.utils.memory.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db_config = MagicMock()
                mock_db_config.value = db_config
                mock_db.query.return_value.filter.return_value.first.return_value = (
                    mock_db_config
                )

                client = get_memory_client()

                assert client == mock_client
                # Verify database config was applied
                config_call = mock_memory_class.from_config.call_args[1]["config_dict"]
                assert config_call["llm"]["provider"] == "openai"
                assert config_call["llm"]["config"]["model"] == "gpt-4"

    def test_get_memory_client_initialization_error(self):
        """Test memory client initialization error handling"""
        with patch("app.utils.memory.Memory") as mock_memory_class:
            mock_memory_class.from_config.side_effect = Exception(
                "Initialization failed"
            )

            with patch("app.utils.memory.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.filter.return_value.first.return_value = None

                client = get_memory_client()

                assert client is None

    def test_get_memory_client_database_error(self):
        """Test memory client with database access error"""
        with patch("app.utils.memory.Memory") as mock_memory_class:
            mock_client = MagicMock()
            mock_memory_class.from_config.return_value = mock_client

            with patch("app.utils.memory.SessionLocal") as mock_session:
                mock_session.side_effect = Exception("Database connection failed")

                client = get_memory_client()

                assert client == mock_client  # Should fallback to default config

    def test_reset_memory_client(self):
        """Test memory client reset functionality"""
        with patch("app.utils.memory._memory_client") as mock_client:
            with patch("app.utils.memory._config_hash") as mock_hash:
                reset_memory_client()

                # Verify global variables are reset
                import app.utils.memory as memory_module

                assert memory_module._memory_client is None
                assert memory_module._config_hash is None


@pytest.mark.unit
class TestDockerEnvironmentDetection:
    """Test Docker environment detection and URL fixing"""

    def test_get_docker_host_url_not_in_docker(self):
        """Test host URL detection when not in Docker"""
        with patch("os.path.exists", return_value=False):
            result = _get_docker_host_url()
            assert result == "localhost"

    def test_get_docker_host_url_with_custom_host(self):
        """Test host URL with custom OLLAMA_HOST environment variable"""
        with patch.dict("os.environ", {"OLLAMA_HOST": "http://custom-host:11434"}):
            result = _get_docker_host_url()
            assert result == "custom-host"

    def test_get_docker_host_url_with_host_docker_internal(self):
        """Test host URL with host.docker.internal available"""
        with patch("os.path.exists", return_value=True):
            with patch("socket.gethostbyname", return_value="192.168.1.1"):
                result = _get_docker_host_url()
                assert result == "host.docker.internal"

    def test_get_docker_host_url_with_gateway_ip(self):
        """Test host URL with Docker gateway IP detection"""
        route_content = "Iface\tDestination\tGateway\neth0\t00000000\t0111A8C0\n"

        with patch("os.path.exists", return_value=True):
            with patch("socket.gethostbyname", side_effect=socket.gaierror):
                with patch("builtins.open", mock_open(read_data=route_content)):
                    result = _get_docker_host_url()
                    assert result == "192.168.17.1"  # 0111A8C0 reversed

    def test_get_docker_host_url_fallback(self):
        """Test host URL fallback to default Docker bridge IP"""
        with patch("os.path.exists", return_value=True):
            with patch("socket.gethostbyname", side_effect=socket.gaierror):
                with patch("builtins.open", side_effect=FileNotFoundError):
                    result = _get_docker_host_url()
                    assert result == "172.17.0.1"

    def test_fix_ollama_urls_no_config(self):
        """Test Ollama URL fixing with no config section"""
        result = _fix_ollama_urls(None)
        assert result is None

        result = _fix_ollama_urls({"provider": "ollama"})
        assert result == {"provider": "ollama"}

    def test_fix_ollama_urls_sets_default(self):
        """Test Ollama URL fixing sets default URL"""
        config = {"provider": "ollama", "config": {"model": "llama3.1"}}

        result = _fix_ollama_urls(config)
        assert (
            result["config"]["ollama_base_url"] == "http://host.docker.internal:11434"
        )

    def test_fix_ollama_urls_fixes_localhost(self):
        """Test Ollama URL fixing replaces localhost"""
        config = {
            "provider": "ollama",
            "config": {
                "model": "llama3.1",
                "ollama_base_url": "http://localhost:11434",
            },
        }

        with patch(
            "app.utils.memory._get_docker_host_url", return_value="host.docker.internal"
        ):
            result = _fix_ollama_urls(config)
            assert (
                result["config"]["ollama_base_url"]
                == "http://host.docker.internal:11434"
            )

    def test_fix_ollama_urls_preserves_non_localhost(self):
        """Test Ollama URL fixing preserves non-localhost URLs"""
        config = {
            "provider": "ollama",
            "config": {
                "model": "llama3.1",
                "ollama_base_url": "http://custom-host:11434",
            },
        }

        result = _fix_ollama_urls(config)
        assert result["config"]["ollama_base_url"] == "http://custom-host:11434"


@pytest.mark.unit
class TestConfigurationParsing:
    """Test configuration parsing and environment variable handling"""

    def test_parse_environment_variables_simple(self):
        """Test parsing environment variables in simple config"""
        config = {"api_key": "env:TEST_API_KEY", "model": "gpt-4"}

        with patch.dict("os.environ", {"TEST_API_KEY": "secret-key"}):
            result = _parse_environment_variables(config)
            assert result["api_key"] == "secret-key"
            assert result["model"] == "gpt-4"

    def test_parse_environment_variables_nested(self):
        """Test parsing environment variables in nested config"""
        config = {
            "llm": {
                "provider": "openai",
                "config": {"api_key": "env:OPENAI_API_KEY", "model": "gpt-4"},
            }
        }

        with patch.dict("os.environ", {"OPENAI_API_KEY": "openai-key"}):
            result = _parse_environment_variables(config)
            assert result["llm"]["config"]["api_key"] == "openai-key"
            assert result["llm"]["config"]["model"] == "gpt-4"

    def test_parse_environment_variables_missing_env_var(self):
        """Test parsing when environment variable is missing"""
        config = {"api_key": "env:MISSING_KEY", "model": "gpt-4"}

        result = _parse_environment_variables(config)
        assert result["api_key"] == "env:MISSING_KEY"  # Should keep original value
        assert result["model"] == "gpt-4"

    def test_parse_environment_variables_non_env_values(self):
        """Test parsing preserves non-environment values"""
        config = {
            "api_key": "direct-key",
            "model": "gpt-4",
            "temperature": 0.7,
            "enabled": True,
        }

        result = _parse_environment_variables(config)
        assert result == config

    def test_get_config_hash_consistent(self):
        """Test config hash generation is consistent"""
        config1 = {"model": "gpt-4", "temperature": 0.7}
        config2 = {"temperature": 0.7, "model": "gpt-4"}  # Different order

        hash1 = _get_config_hash(config1)
        hash2 = _get_config_hash(config2)

        assert hash1 == hash2  # Should be same due to sort_keys
        assert len(hash1) == 32  # MD5 hash length

    def test_get_config_hash_different_configs(self):
        """Test config hash generation for different configs"""
        config1 = {"model": "gpt-4", "temperature": 0.7}
        config2 = {"model": "gpt-4", "temperature": 0.8}

        hash1 = _get_config_hash(config1)
        hash2 = _get_config_hash(config2)

        assert hash1 != hash2


@pytest.mark.unit
class TestDefaultConfiguration:
    """Test default configuration generation"""

    def test_get_default_memory_config_structure(self):
        """Test default memory configuration structure"""
        config = get_default_memory_config()

        # Verify all required sections are present
        assert "vector_store" in config
        assert "graph_store" in config
        assert "llm" in config
        assert "embedder" in config
        assert "version" in config

        # Verify pgvector configuration
        assert config["vector_store"]["provider"] == "pgvector"
        assert "host" in config["vector_store"]["config"]
        assert "port" in config["vector_store"]["config"]
        assert config["vector_store"]["config"]["port"] == 5432

        # Verify Neo4j configuration
        assert config["graph_store"]["provider"] == "neo4j"
        assert "url" in config["graph_store"]["config"]
        assert "username" in config["graph_store"]["config"]
        assert "password" in config["graph_store"]["config"]

        # Verify OpenAI configuration
        assert config["llm"]["provider"] == "openai"
        assert config["llm"]["config"]["model"] == "gpt-4o-mini"
        assert config["embedder"]["provider"] == "openai"
        assert config["embedder"]["config"]["model"] == "text-embedding-3-small"

    def test_get_default_memory_config_environment_variables(self):
        """Test default config uses environment variables"""
        config = get_default_memory_config()

        # Check that environment variable patterns are used
        assert config["llm"]["config"]["api_key"] == "env:OPENAI_API_KEY"
        assert config["embedder"]["config"]["api_key"] == "env:OPENAI_API_KEY"

        # Check that database configs use environment variables
        pg_config = config["vector_store"]["config"]
        assert pg_config["host"] == os.environ.get("POSTGRES_HOST", "postgres-mem0")
        assert pg_config["user"] == os.environ.get("POSTGRES_USER", "postgres")
        assert pg_config["password"] == os.environ.get("POSTGRES_PASSWORD", "postgres")
        assert pg_config["dbname"] == os.environ.get("POSTGRES_DB", "mem0")

    def test_get_default_memory_config_with_custom_env_vars(self):
        """Test default config with custom environment variables"""
        custom_env = {
            "POSTGRES_HOST": "custom-postgres",
            "POSTGRES_USER": "custom-user",
            "POSTGRES_PASSWORD": "custom-password",
            "POSTGRES_DB": "custom-db",
            "NEO4J_URL": "neo4j://custom-neo4j:7687",
        }

        with patch.dict("os.environ", custom_env):
            config = get_default_memory_config()

            pg_config = config["vector_store"]["config"]
            assert pg_config["host"] == "custom-postgres"
            assert pg_config["user"] == "custom-user"
            assert pg_config["password"] == "custom-password"
            assert pg_config["dbname"] == "custom-db"

            neo4j_config = config["graph_store"]["config"]
            assert neo4j_config["url"] == "neo4j://custom-neo4j:7687"

    def test_get_default_user_id(self):
        """Test default user ID generation"""
        user_id = get_default_user_id()
        assert user_id == "default_user"
        assert isinstance(user_id, str)
        assert len(user_id) > 0


@pytest.mark.unit
class TestErrorHandlingAndResilience:
    """Test error handling and resilience patterns"""

    def setup_method(self):
        """Reset global variables before each test"""
        reset_memory_client()

    def test_memory_client_with_initialization_failure(self):
        """Test memory client returns None when initialization fails"""
        with patch("app.utils.memory.Memory") as mock_memory_class:
            mock_memory_class.from_config.side_effect = Exception("Temporary failure")

            with patch("app.utils.memory.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.filter.return_value.first.return_value = None

                # Should return None when initialization fails
                client = get_memory_client()

                # Should return None due to initialization failure
                assert client is None
                # Verify initialization was attempted
                assert mock_memory_class.from_config.call_count >= 1

    def test_memory_client_persistent_failure_handling(self):
        """Test memory client handles persistent failures gracefully"""
        with patch("app.utils.memory.Memory") as mock_memory_class:
            mock_memory_class.from_config.side_effect = Exception("Persistent failure")

            with patch("app.utils.memory.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.filter.return_value.first.return_value = None

                # Should handle persistent failures gracefully by returning None
                client = get_memory_client()

                # Should return None for persistent failures
                assert client is None

    def test_memory_client_handles_external_service_error(self):
        """Test memory client handles external service errors gracefully"""
        with patch("app.utils.memory.Memory") as mock_memory_class:
            mock_memory_class.from_config.side_effect = Exception(
                "External service unavailable"
            )

            with patch("app.utils.memory.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.filter.return_value.first.return_value = None

                # Should handle external service errors gracefully by returning None
                client = get_memory_client()

                # Should return None for external service errors
                assert client is None

    def test_memory_client_performance_logging(self):
        """Test memory client performance logging"""
        with patch("app.utils.memory.Memory") as mock_memory_class:
            mock_client = MagicMock()
            mock_memory_class.from_config.return_value = mock_client

            with patch("app.utils.memory.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.filter.return_value.first.return_value = None

                with patch("app.utils.memory.performance_logger") as mock_perf_logger:
                    mock_timer = MagicMock()
                    mock_perf_logger.timer.return_value = mock_timer

                    client = get_memory_client()

                    # Verify client was created successfully
                    assert client is not None
                    # Verify performance logging was called
                    mock_perf_logger.timer.assert_called_with(
                        "memory_client_initialization"
                    )

    def test_memory_client_caching_behavior(self):
        """Test memory client caching behavior"""
        with patch("app.utils.memory.Memory") as mock_memory_class:
            mock_client = MagicMock()
            mock_memory_class.from_config.return_value = mock_client

            with patch("app.utils.memory.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.filter.return_value.first.return_value = None

                # First call should initialize
                client1 = get_memory_client()
                assert client1 is not None

                # Second call should use cached instance (same object)
                client2 = get_memory_client()
                assert client2 is not None
                assert client1 is client2  # Should be the exact same cached instance

                # Should only initialize once due to caching
                mock_memory_class.from_config.assert_called_once()
