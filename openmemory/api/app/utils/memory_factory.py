"""
Memory Client Factory for Dependency Injection

This module provides a factory pattern for memory client creation,
enabling proper dependency injection and testing isolation.
"""

import logging
from typing import Optional, Protocol, Any, Dict
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class MemoryClient(Protocol):
    """Protocol defining the memory client interface"""
    
    def add(self, text: str, user_id: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add a memory"""
        ...
    
    def search(self, query: str, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """Search memories"""
        ...
    
    def get_all(self, user_id: str) -> Dict[str, Any]:
        """Get all memories for user"""
        ...
    
    def delete(self, memory_id: str) -> Dict[str, Any]:
        """Delete a memory"""
        ...
    
    def update(self, memory_id: str, text: str) -> Dict[str, Any]:
        """Update a memory"""
        ...


class MockMemoryClient:
    """Mock memory client for testing and development"""
    
    def __init__(self):
        self._memories = {}
        self._next_id = 1
    
    def add(self, text: str, user_id: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add a mock memory"""
        memory_id = f"mock_memory_{self._next_id}"
        self._next_id += 1
        
        memory = {
            "id": memory_id,
            "memory": text,
            "user_id": user_id,
            "metadata": metadata or {},
            "created_at": "2025-01-09T00:00:00Z"
        }
        
        self._memories[memory_id] = memory
        
        return {
            "results": [{
                "id": memory_id,
                "memory": text,
                "event": "ADD"
            }]
        }
    
    def search(self, query: str, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """Search mock memories"""
        # Simple text matching for mock
        results = []
        for memory in self._memories.values():
            if (memory["user_id"] == user_id and 
                query.lower() in memory["memory"].lower()):
                results.append({
                    "id": memory["id"],
                    "memory": memory["memory"],
                    "score": 0.95,
                    "created_at": memory["created_at"]
                })
                if len(results) >= limit:
                    break
        
        return {"results": results}
    
    def get_all(self, user_id: str) -> Dict[str, Any]:
        """Get all mock memories for user"""
        user_memories = [
            memory for memory in self._memories.values() 
            if memory["user_id"] == user_id
        ]
        return {"results": user_memories}
    
    def delete(self, memory_id: str) -> Dict[str, Any]:
        """Delete a mock memory"""
        if memory_id in self._memories:
            del self._memories[memory_id]
            return {"message": f"Memory {memory_id} deleted"}
        return {"error": f"Memory {memory_id} not found"}
    
    def update(self, memory_id: str, text: str) -> Dict[str, Any]:
        """Update a mock memory"""
        if memory_id in self._memories:
            self._memories[memory_id]["memory"] = text
            return {"message": f"Memory {memory_id} updated"}
        return {"error": f"Memory {memory_id} not found"}


class MemoryClientFactory:
    """Factory for creating memory clients with dependency injection"""
    
    _instance: Optional['MemoryClientFactory'] = None
    _client_provider: Optional[callable] = None
    _mock_mode: bool = False
    
    def __new__(cls) -> 'MemoryClientFactory':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def configure(cls, 
                  client_provider: Optional[callable] = None, 
                  mock_mode: bool = False):
        """Configure the factory with a client provider"""
        if cls._instance is None:
            cls._instance = cls()
        
        cls._instance._client_provider = client_provider
        cls._instance._mock_mode = mock_mode
        logger.info(f"MemoryClientFactory configured: mock_mode={mock_mode}")
    
    @classmethod
    def create_client(cls) -> MemoryClient:
        """Create a memory client instance"""
        if cls._instance is None:
            cls._instance = cls()
        
        # Use mock client if in mock mode or if dependencies unavailable
        if cls._instance._mock_mode:
            logger.debug("Creating mock memory client")
            return MockMemoryClient()
        
        # Try custom provider first
        if cls._instance._client_provider:
            try:
                client = cls._instance._client_provider()
                if client:
                    logger.debug("Created memory client from custom provider")
                    return client
            except Exception as e:
                logger.warning(f"Custom provider failed: {e}, falling back to default")
        
        # Try default mem0 client
        try:
            from app.utils.memory import get_memory_client
            client = get_memory_client()
            if client:
                logger.debug("Created memory client from default provider")
                return client
        except ImportError as e:
            logger.warning(f"mem0 dependency not available: {e}, using mock client")
        except Exception as e:
            logger.error(f"Failed to create memory client: {e}, using mock client")
        
        # Fall back to mock client
        logger.info("Using mock memory client as fallback")
        return MockMemoryClient()
    
    @classmethod
    def reset(cls):
        """Reset factory configuration (for testing)"""
        if cls._instance:
            cls._instance._client_provider = None
            cls._instance._mock_mode = False
        logger.debug("MemoryClientFactory reset")


def get_memory_client_safe() -> MemoryClient:
    """Get a memory client safely with proper error handling"""
    try:
        return MemoryClientFactory.create_client()
    except Exception as e:
        logger.error(f"Failed to create memory client: {e}")
        # Always return a working client, even if it's a mock
        return MockMemoryClient()


# Configure factory based on environment
import os
if os.getenv("TESTING") == "true":
    MemoryClientFactory.configure(mock_mode=True)
elif os.getenv("MCP_MOCK_MODE") == "true":
    MemoryClientFactory.configure(mock_mode=True)
else:
    MemoryClientFactory.configure(mock_mode=False)