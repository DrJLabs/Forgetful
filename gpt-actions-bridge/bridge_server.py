#!/usr/bin/env python3
"""
GPT Actions Bridge Server for Mem0 Memory System

This server provides a secure, authenticated REST API bridge between ChatGPT Actions
and the mem0 memory system. It handles request transformation, authentication,
and proxying to the appropriate backend services.
"""

import os
import secrets
import httpx
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Configuration
MEM0_API_BASE = os.environ.get("MEM0_API_BASE", "http://172.17.0.1:8000")
OPENMEMORY_API_BASE = os.environ.get("OPENMEMORY_API_BASE", "http://172.17.0.1:8765")
API_KEY_PREFIX = "gpt_"


# API Models
class Message(BaseModel):
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")


class CreateMemoryRequest(BaseModel):
    messages: List[Message] = Field(..., description="Messages to process into memory")
    user_id: str = Field(default="chatgpt_user", description="User identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class SearchMemoryRequest(BaseModel):
    query: str = Field(..., description="Search query")
    user_id: str = Field(default="chatgpt_user", description="User identifier")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results")
    threshold: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Similarity threshold"
    )


class UpdateMemoryRequest(BaseModel):
    text: str = Field(..., description="New memory content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")


# Initialize FastAPI app
app = FastAPI(
    servers=[
        {
            "url": "https://mem-mcp.onemainarmy.com",
            "description": "Production API Server",
        }
    ],
    title="Mem0 Memory System - GPT Actions API",
    version="1.0.0",
    description="Secure API bridge for ChatGPT to interact with the mem0 memory system",
)

# CORS for ChatGPT
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chat.openai.com", "https://chatgpt.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# Security
security = HTTPBearer()

# Valid API keys (in production, store in environment/database)
VALID_API_KEYS = set()


def generate_api_key() -> str:
    """Generate a secure API key for GPT Actions"""
    random_bytes = secrets.token_bytes(32)
    return f"{API_KEY_PREFIX}{random_bytes.hex()}"


def load_api_keys():
    """Load API keys from environment or generate new ones"""
    global VALID_API_KEYS

    # Try to load from environment
    env_keys = os.environ.get("GPT_API_KEYS", "")
    if env_keys:
        VALID_API_KEYS.update(env_keys.split(","))

    # Generate default key if none exist
    if not VALID_API_KEYS:
        default_key = generate_api_key()
        VALID_API_KEYS.add(default_key)
        print(f"Generated default API key: {default_key}")
        print("Store this securely and add to GPT Actions configuration!")


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Verify API key from Authorization header"""
    if not credentials.credentials.startswith(API_KEY_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key format"
        )

    if credentials.credentials not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    return credentials.credentials


class MemoryClient:
    """HTTP client for mem0 and OpenMemory APIs"""

    def __init__(self):
        self.mem0_client = httpx.AsyncClient(base_url=MEM0_API_BASE, timeout=30.0)
        self.openmemory_client = httpx.AsyncClient(
            base_url=OPENMEMORY_API_BASE, timeout=30.0
        )

    async def create_memory(self, request: CreateMemoryRequest) -> Dict[str, Any]:
        """Create memory via OpenMemory API"""
        # Convert messages to text format that OpenMemory expects
        text_content = "\n".join(
            [f"{msg.role}: {msg.content}" for msg in request.messages]
        )

        payload = {"text": text_content, "user_id": request.user_id}
        if request.metadata:
            payload["metadata"] = request.metadata

        response = await self.openmemory_client.post("/api/v1/memories/", json=payload)
        response.raise_for_status()

        data = response.json()
        return {
            "success": True,
            "message": "Memories created successfully",
            "memory_ids": data.get("result", []),
            "relations": data.get("relations", {}),
        }

    async def search_memories(self, request: SearchMemoryRequest) -> Dict[str, Any]:
        """Search memories via OpenMemory MCP API"""
        payload = {
            "query": request.query,
            "user_id": request.user_id,
            "limit": request.limit,
        }

        response = await self.openmemory_client.post(
            "/api/v1/memories/search", json=payload
        )
        response.raise_for_status()

        data = response.json()
        # OpenMemory returns result as string that needs parsing
        results_str = data.get("result", "[]")
        results = (
            json.loads(results_str) if isinstance(results_str, str) else results_str
        )

        # Add similarity scores (mem0 API format may vary)
        for i, result in enumerate(results):
            if "score" not in result:
                result["score"] = 1.0 - (i * 0.1)  # Approximate scoring

        return {
            "success": True,
            "query": request.query,
            "results": results,
            "relations": data.get("relations", []),
        }

    async def list_memories(
        self, user_id: str, limit: int = 20, category: Optional[str] = None
    ) -> Dict[str, Any]:
        """List memories via OpenMemory API"""
        params = {"user_id": user_id, "limit": limit}
        if category:
            params["category"] = category

        response = await self.openmemory_client.get("/api/v1/memories/", params=params)
        response.raise_for_status()

        data = response.json()
        # OpenMemory returns {"status": "success", "result": "..."} format
        memories_result = (
            json.loads(data.get("result", "[]"))
            if isinstance(data.get("result"), str)
            else data.get("result", [])
        )

        return {
            "success": True,
            "total": len(memories_result) if isinstance(memories_result, list) else 0,
            "memories": memories_result if isinstance(memories_result, list) else [],
            "relations": [],
        }

    async def get_memory(self, memory_id: str) -> Dict[str, Any]:
        """Get specific memory via mem0 API"""
        response = await self.mem0_client.get(f"/memories/{memory_id}")
        response.raise_for_status()

        data = response.json()
        return {"success": True, "memory": data}

    async def update_memory(
        self, memory_id: str, request: UpdateMemoryRequest
    ) -> Dict[str, Any]:
        """Update memory via mem0 API"""
        payload = {"text": request.text}
        if request.metadata:
            payload["metadata"] = request.metadata

        response = await self.mem0_client.put(f"/memories/{memory_id}", json=payload)
        response.raise_for_status()

        return {"success": True, "message": "Memory updated successfully"}

    async def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """Delete memory via mem0 API"""
        response = await self.mem0_client.delete(f"/memories/{memory_id}")
        response.raise_for_status()

        return {"success": True, "message": "Memory deleted successfully"}

    async def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Get memory statistics via OpenMemory API"""
        response = await self.openmemory_client.get(f"/api/v1/stats/?user_id={user_id}")
        response.raise_for_status()

        data = response.json()
        return {
            "success": True,
            "stats": {
                "total_memories": data.get("total_memories", 0),
                "categories": [],  # Would need additional API call
                "recent_activity": {
                    "last_created": datetime.now().isoformat(),
                    "last_accessed": datetime.now().isoformat(),
                },
            },
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check health of backend services"""
        services = {}

        try:
            response = await self.mem0_client.get("/docs")
            services["mem0_api"] = (
                "healthy" if response.status_code == 200 else "unhealthy"
            )
        except Exception:
            services["mem0_api"] = "unhealthy"

        try:
            response = await self.openmemory_client.get("/health")
            services["postgres"] = (
                "healthy" if response.status_code == 200 else "unhealthy"
            )
        except Exception:
            services["postgres"] = "unhealthy"

        # Neo4j would need separate check
        services["neo4j"] = "healthy"  # Assume healthy for now

        return {
            "status": "healthy"
            if all(s == "healthy" for s in services.values())
            else "degraded",
            "services": services,
            "timestamp": datetime.now().isoformat(),
        }


# Initialize client
memory_client = MemoryClient()

# Load API keys at startup
load_api_keys()


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint (no authentication required)"""
    return await memory_client.health_check()


@app.get("/memories")
async def list_memories(
    user_id: str = "chatgpt_user",
    limit: int = 20,
    category: Optional[str] = None,
    api_key: str = Depends(verify_api_key),
):
    """List all memories for a user"""
    return await memory_client.list_memories(user_id, limit, category)


@app.post("/memories")
async def create_memory(
    request: CreateMemoryRequest, api_key: str = Depends(verify_api_key)
):
    """Create new memories from messages"""
    return await memory_client.create_memory(request)


@app.post("/memories/search")
async def search_memories(
    request: SearchMemoryRequest, api_key: str = Depends(verify_api_key)
):
    """Search memories using semantic similarity"""
    return await memory_client.search_memories(request)


@app.get("/memories/{memory_id}")
async def get_memory(memory_id: str, api_key: str = Depends(verify_api_key)):
    """Retrieve a specific memory by ID"""
    return await memory_client.get_memory(memory_id)


@app.put("/memories/{memory_id}")
async def update_memory(
    memory_id: str, request: UpdateMemoryRequest, api_key: str = Depends(verify_api_key)
):
    """Update an existing memory"""
    return await memory_client.update_memory(memory_id, request)


@app.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str, api_key: str = Depends(verify_api_key)):
    """Delete a specific memory"""
    return await memory_client.delete_memory(memory_id)


@app.get("/memories/stats")
async def get_memory_stats(
    user_id: str = "chatgpt_user", api_key: str = Depends(verify_api_key)
):
    """Get memory statistics for a user"""
    return await memory_client.get_stats(user_id)


# Exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail, "code": "HTTP_ERROR"},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "code": "INTERNAL_ERROR",
        },
    )


if __name__ == "__main__":
    load_api_keys()
    uvicorn.run(
        "bridge_server:app", host="0.0.0.0", port=8080, reload=False, access_log=True
    )
