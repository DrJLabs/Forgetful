"""
Mem0 client integration for OpenMemory API
This module provides a centralized mem0 Memory instance that integrates
with the main mem0 system instead of using a separate database.
"""

import os
import logging
from mem0 import Memory
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Global variable to store the memory client instance
_memory_client = None


def get_config():
    """Get mem0 configuration"""
    return {
        "llm": {
            "provider": "openai",
            "config": {
                "model": "gpt-4o-mini",
                "temperature": 0.1,
                "max_tokens": 2000,
                "api_key": os.getenv("OPENAI_API_KEY"),
            },
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "text-embedding-3-small",
                "api_key": os.getenv("OPENAI_API_KEY"),
            },
        },
        "vector_store": {
            "provider": "pgvector",
            "config": {
                "host": os.getenv("POSTGRES_HOST", "postgres-mem0"),
                "port": int(os.getenv("POSTGRES_PORT", "5432")),
                "dbname": os.getenv(
                    "POSTGRES_DB", "mem0"
                ),  # Changed from "database" to "dbname"
                "user": os.getenv("POSTGRES_USER"),
                "password": os.getenv("POSTGRES_PASSWORD"),
                "collection_name": "memories",  # Use the main memories table
                "embedding_model_dims": 1536,  # for text-embedding-3-small
            },
        },
        "graph_store": {
            "provider": "neo4j",
            "config": {
                "url": os.getenv("NEO4J_URL", "neo4j://neo4j-mem0:7687"),
                "username": os.getenv("NEO4J_AUTH", "neo4j/data2f!re").split("/")[0],
                "password": os.getenv("NEO4J_AUTH", "neo4j/data2f!re").split("/")[1],
            },
        },
        "version": "v1.1",
    }


def get_memory_client():
    """Get the shared mem0 Memory client instance (lazy initialization)"""
    global _memory_client

    # Return None if in testing environment to avoid connection issues
    if os.getenv("TESTING") == "true":
        logger.info("Testing environment detected, returning None for memory client")
        return None

    # Lazy initialization - only create when first needed
    if _memory_client is None:
        try:
            config = get_config()
            _memory_client = Memory.from_config(config)
            logger.info("Successfully initialized mem0 Memory client")
        except Exception as e:
            logger.error(f"Failed to initialize mem0 Memory client: {e}")
            # In production, you might want to raise here
            # For now, return None to handle gracefully
            return None

    return _memory_client


# For backward compatibility (if any code directly accesses memory_client)
# This will be None in test environment
memory_client = get_memory_client() if os.getenv("TESTING") != "true" else None
