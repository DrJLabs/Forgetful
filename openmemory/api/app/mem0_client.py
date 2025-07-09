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

# Configure mem0 with the same settings as the main mem0 API
config = {
    "llm": {
        "provider": "openai",
        "config": {
            "model": "gpt-4o-mini",
            "temperature": 0.1,
            "max_tokens": 2000,
            "api_key": os.getenv("OPENAI_API_KEY")
        }
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small",
            "api_key": os.getenv("OPENAI_API_KEY")
        }
    },
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "host": os.getenv("POSTGRES_HOST", "postgres-mem0"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "dbname": os.getenv("POSTGRES_DB", "mem0"),  # Changed from "database" to "dbname"
            "user": os.getenv("POSTGRES_USER"),
            "password": os.getenv("POSTGRES_PASSWORD"),
            "collection_name": "mem0_memories",
            "embedding_model_dims": 1536  # for text-embedding-3-small
        }
    },
    "graph_store": {
        "provider": "neo4j",
        "config": {
            "url": os.getenv("NEO4J_URL", "neo4j://neo4j-mem0:7687"),
            "username": os.getenv("NEO4J_AUTH", "neo4j/data2f!re").split("/")[0],
            "password": os.getenv("NEO4J_AUTH", "neo4j/data2f!re").split("/")[1]
        }
    },
    "version": "v1.1"
}

# Initialize mem0 Memory client
try:
    memory_client = Memory.from_config(config)
    logger.info("Successfully initialized mem0 Memory client")
except Exception as e:
    logger.error(f"Failed to initialize mem0 Memory client: {e}")
    raise

def get_memory_client():
    """Get the shared mem0 Memory client instance"""
    return memory_client 