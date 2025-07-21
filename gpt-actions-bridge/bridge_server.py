#!/usr/bin/env python3
"""
GPT Actions Bridge Server for Mem0 Memory System

This server provides a secure, authenticated REST API bridge between ChatGPT Actions
and the mem0 memory system. It handles request transformation, authentication,
and proxying to the appropriate backend services.
"""

import logging
import os
import secrets
from datetime import datetime
from typing import Any

import httpx
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
OPENMEMORY_API_BASE = os.environ.get(
    "OPENMEMORY_API_BASE", "http://openmemory-mcp:8765"
)
API_KEY_PREFIX = "gpt_"


# API Models
class Message(BaseModel):
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")


class CreateMemoryRequest(BaseModel):
    messages: list[Message] = Field(..., description="Messages to process into memory")
    user_id: str = Field(default="chatgpt_user", description="User identifier")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class SearchMemoryRequest(BaseModel):
    query: str = Field(..., description="Search query")
    user_id: str = Field(default="chatgpt_user", description="User identifier")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results")
    threshold: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Similarity threshold"
    )


class UpdateMemoryRequest(BaseModel):
    text: str = Field(..., description="New memory content")
    metadata: dict[str, Any] | None = Field(None, description="Updated metadata")


# Initialize FastAPI app
app = FastAPI(
    servers=[
        {
            "url": "https://mem-mcp.onemainarmy.com",
            "description": "Production API Server via Cloudflare Tunnel",
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
    """HTTP client for mem0 and OpenMemory APIs with robust error handling"""

    def __init__(self):
        # Configure timeout with fine-grained control
        timeout = httpx.Timeout(
            connect=10.0,  # Time to establish connection
            read=30.0,  # Time to read response
            write=10.0,  # Time to send request
            pool=5.0,  # Time to get connection from pool
        )

        # Configure connection limits
        limits = httpx.Limits(
            max_keepalive_connections=5, max_connections=10, keepalive_expiry=30.0
        )

        # Enhanced headers for better compatibility
        headers = {
            "User-Agent": "GPT-Actions-Bridge/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        self.openmemory_client = httpx.AsyncClient(
            base_url=OPENMEMORY_API_BASE,
            timeout=timeout,
            limits=limits,
            headers=headers,
            follow_redirects=True,
        )

        logger.info(f"Initialized MemoryClient with base URL: {OPENMEMORY_API_BASE}")

    async def create_memory(self, request: CreateMemoryRequest) -> dict[str, Any]:
        """Create new memories via OpenMemory API with automatic user creation"""
        # Convert messages to text format that OpenMemory expects
        text_content = "\n".join(
            [f"{msg.role}: {msg.content}" for msg in request.messages]
        )

        payload = {
            "text": text_content,
            "user_id": request.user_id,
            "app": "chatgpt_actions",
        }
        if request.metadata:
            payload["metadata"] = request.metadata

        try:
            logger.info(f"Creating memory for user: {request.user_id}")

            # First, ensure user exists by calling stats endpoint
            try:
                stats_response = await self.openmemory_client.get(
                    f"/api/v1/stats/?user_id={request.user_id}"
                )
                if stats_response.status_code == 200:
                    logger.info(
                        f"User '{request.user_id}' verified/created successfully"
                    )
                else:
                    logger.info(
                        f"User '{request.user_id}' not found. Creating user via stats endpoint..."
                    )
                    try:
                        # Call stats endpoint to trigger user creation (fixed URL - with trailing slash)
                        stats_response = await self.openmemory_client.get(
                            f"/api/v1/stats/?user_id={request.user_id}"
                        )
                        if stats_response.status_code == 200:
                            logger.info(
                                f"User '{request.user_id}' created successfully. Retrying memory creation..."
                            )
                            # Retry memory creation
                            response = await self.openmemory_client.post(
                                "/api/v1/memories/", json=payload
                            )
                            logger.info(
                                f"Retry memory creation status: {response.status_code}"
                            )
                        else:
                            logger.warning(
                                f"User creation via stats failed with status: {stats_response.status_code}"
                            )
                    except Exception as stats_error:
                        logger.warning(f"Stats endpoint call failed: {stats_error}")
            except Exception as e:
                logger.warning(f"User verification/creation failed: {e}")

            # Now attempt memory creation
            response = await self.openmemory_client.post(
                "/api/v1/memories/", json=payload
            )

            # Handle 404 User Not Found - Try user creation via stats endpoint
            if response.status_code == 404:
                error_text = response.text
                if "User not found" in error_text:
                    logger.info(
                        f"User '{request.user_id}' not found. Creating user via stats endpoint..."
                    )
                    try:
                        # Call stats endpoint to trigger user creation (fixed URL - no trailing slash in query)
                        stats_response = await self.openmemory_client.get(
                            f"/api/v1/stats?user_id={request.user_id}"
                        )
                        if stats_response.status_code == 200:
                            logger.info(
                                f"User '{request.user_id}' created successfully. Retrying memory creation..."
                            )
                            # Retry memory creation
                            response = await self.openmemory_client.post(
                                "/api/v1/memories/", json=payload
                            )
                            logger.info(
                                f"Retry response status: {response.status_code}"
                            )
                        else:
                            logger.warning(
                                f"Stats endpoint returned {stats_response.status_code}"
                            )
                    except Exception as user_creation_error:
                        logger.error(f"Failed to create user: {user_creation_error}")

            # Log the actual response for debugging
            logger.info(f"Memory creation response status: {response.status_code}")
            logger.info(f"Memory creation response body: {response.text}")

            response.raise_for_status()

            data = response.json()
            logger.info("Memory created successfully")
            logger.info(f"Response data: {data}")

            # Extract memory information from response
            # OpenMemory MCP now returns properly formatted response with real UUIDs
            memory_ids = []

            # Check for the standard response format from OpenMemory MCP
            if isinstance(data, dict) and "results" in data:
                results = data.get("results", [])

                if isinstance(results, list):
                    for result in results:
                        if isinstance(result, dict) and "id" in result:
                            memory_ids.append(result["id"])

            # Fallback: check for direct memory_ids field
            elif isinstance(data, dict) and "memory_ids" in data:
                memory_ids = data["memory_ids"]

            # If we have memory IDs, return success with proper IDs
            if memory_ids:
                return {
                    "success": True,
                    "message": data.get("message", "Memories created successfully"),
                    "memory_ids": memory_ids,
                    "relations": data.get("relations", {}),
                    "debug_response": data,  # Include full response for debugging
                }

            # If no memory IDs but operation was successful, check for error
            elif isinstance(data, dict) and "error" in data:
                logger.error(f"Memory creation failed: {data['error']}")
                raise Exception(f"Memory creation failed: {data['error']}")

            # If no memory IDs and no error, something is wrong
            else:
                logger.error(
                    "Memory creation succeeded but no memory IDs returned and no error reported"
                )
                logger.error(f"Full response: {data}")
                raise Exception("Memory creation failed: No memory IDs returned")

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Status Error in create_memory: {e}")
            logger.error(f"Response body: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request Error in create_memory: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in create_memory: {e}")
            raise

    async def search_memories(self, request: SearchMemoryRequest) -> dict[str, Any]:
        """Search memories via OpenMemory MCP API with enhanced error handling"""
        payload = {
            "query": request.query,
            "user_id": request.user_id,
            "limit": request.limit,
        }

        url_path = "/api/v1/memories/search"

        logger.info(f"Searching memories: POST {OPENMEMORY_API_BASE}{url_path}")
        logger.debug(f"Search payload: {payload}")

        try:
            response = await self.openmemory_client.post(url_path, json=payload)

            logger.info(f"Search response status: {response.status_code}")

            if response.status_code == 404:
                # Log detailed information for 404 debugging
                logger.error("404 Error Details for search:")
                logger.error(f"  Request URL: {response.url}")
                logger.error(f"  Request method: {response.request.method}")
                logger.error(f"  Base URL: {self.openmemory_client.base_url}")

                # Try alternative search paths
                alternative_paths = ["/api/v1/search", "/memories/search", "/search"]
                for alt_path in alternative_paths:
                    try:
                        logger.info(f"Attempting alternative search path: {alt_path}")
                        alt_response = await self.openmemory_client.post(
                            alt_path, json=payload
                        )
                        if alt_response.status_code != 404:
                            logger.info(
                                f"Alternative search path {alt_path} worked with status {alt_response.status_code}"
                            )
                            response = alt_response
                            break
                    except Exception as e:
                        logger.debug(f"Alternative search path {alt_path} failed: {e}")
                        continue

            response.raise_for_status()

            data = response.json()
            logger.debug(f"Raw search response: {data}")

            # OpenMemory MCP returns results directly in 'results' field, not 'result'
            results = data.get("results", [])

            # Ensure results is a list (should already be from OpenMemory MCP)
            if not isinstance(results, list):
                logger.warning(
                    f"Expected results to be a list, got {type(results)}: {results}"
                )
                results = []

            logger.info(f"Search completed, found {len(results)} results")
            return {
                "success": True,
                "results": results,
                "total": len(results),
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Status Error in search: {e}")
            logger.error(f"Response body: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request Error in search: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in search_memories: {e}")
            raise

    async def list_memories(self, user_id: str) -> dict[str, Any]:
        """List memories for user with enhanced error handling"""
        url_path = f"/api/v1/memories/?user_id={user_id}"

        logger.info(f"Listing memories: GET {OPENMEMORY_API_BASE}{url_path}")

        try:
            response = await self.openmemory_client.get(url_path)

            logger.info(f"List response status: {response.status_code}")

            if response.status_code == 404:
                # Try alternative list paths
                alternative_paths = [
                    f"/api/v1/memories?user_id={user_id}",
                    f"/memories/?user_id={user_id}",
                    f"/memories?user_id={user_id}",
                ]
                for alt_path in alternative_paths:
                    try:
                        logger.info(f"Attempting alternative list path: {alt_path}")
                        alt_response = await self.openmemory_client.get(alt_path)
                        if alt_response.status_code != 404:
                            logger.info(
                                f"Alternative list path {alt_path} worked with status {alt_response.status_code}"
                            )
                            response = alt_response
                            break
                    except Exception as e:
                        logger.debug(f"Alternative list path {alt_path} failed: {e}")
                        continue

            response.raise_for_status()

            data = response.json()
            # OpenMemory MCP returns memories in 'items', not 'results'
            memories = data.get("items", [])
            total = data.get("total", len(memories))

            logger.info(f"Listed {len(memories)} memories for user {user_id}")
            return {
                "success": True,
                "memories": memories,
                "total": total,
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Status Error in list_memories: {e}")
            logger.error(f"Response body: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request Error in list_memories: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in list_memories: {e}")
            raise

    async def get_memory(self, memory_id: str) -> dict[str, Any]:
        """Get specific memory via OpenMemory API"""
        try:
            response = await self.openmemory_client.get(f"/api/v1/memories/{memory_id}")
            response.raise_for_status()

            data = response.json()
            logger.info(f"Retrieved memory {memory_id} successfully")

            return {
                "success": True,
                "memory": {
                    "id": str(data.get("id", memory_id)),
                    "text": data.get(
                        "text", data.get("content")
                    ),  # Handle both possible field names
                    "content": data.get("text", data.get("content")),
                    "created_at": data.get("created_at"),
                    "state": data.get("state"),
                    "app_id": data.get("app_id"),
                    "app_name": data.get("app_name"),
                    "categories": data.get("categories", []),
                    "metadata": data.get("metadata_", {}),
                },
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Status Error in get_memory: {e}")
            logger.error(f"Response body: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request Error in get_memory: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_memory: {e}")
            raise

    async def update_memory(
        self, memory_id: str, request: UpdateMemoryRequest
    ) -> dict[str, Any]:
        """Update memory via OpenMemory API"""
        payload = {
            "memory_content": request.text,
            "user_id": "chatgpt_user",  # Default user_id for GPT Actions
        }
        # Note: OpenMemory API doesn't currently support metadata updates in the same call

        try:
            response = await self.openmemory_client.put(
                f"/api/v1/memories/{memory_id}", json=payload
            )
            response.raise_for_status()

            data = response.json()
            return {
                "success": True,
                "message": "Memory updated successfully",
                "memory": {
                    "id": str(data.get("id", memory_id)),
                    "content": data.get("content", request.text),
                    "updated_at": data.get("updated_at"),
                },
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Status Error in update_memory: {e}")
            logger.error(f"Response body: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request Error in update_memory: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in update_memory: {e}")
            raise

    async def delete_memory(self, memory_id: str) -> dict[str, Any]:
        """Delete memory via OpenMemory API"""
        try:
            response = await self.openmemory_client.delete(
                f"/api/v1/memories/{memory_id}"
            )
            response.raise_for_status()

            logger.info(f"Deleted memory {memory_id} successfully")
            return {
                "success": True,
                "message": f"Memory {memory_id} deleted successfully",
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Status Error in delete_memory: {e}")
            logger.error(f"Response body: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request Error in delete_memory: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in delete_memory: {e}")
            raise

    async def get_stats(self, user_id: str) -> dict[str, Any]:
        """Get memory statistics via OpenMemory API with robust error handling and user auto-creation"""
        try:
            logger.info(f"Getting stats for user: {user_id}")
            # Use correct URL format with trailing slash as required by OpenMemory MCP
            response = await self.openmemory_client.get(
                f"/api/v1/stats/?user_id={user_id}"
            )

            logger.info(f"Stats response status: {response.status_code}")
            logger.info(f"Stats response body: {response.text}")

            if response.status_code == 404:
                # User doesn't exist, the stats endpoint should auto-create them
                logger.info(
                    f"User '{user_id}' not found for stats. Should be auto-created by stats endpoint..."
                )
                # The stats endpoint in OpenMemory auto-creates users, so try again
                response = await self.openmemory_client.get(
                    f"/api/v1/stats/?user_id={user_id}"
                )
                logger.info(f"Retry stats response status: {response.status_code}")

            response.raise_for_status()

            data = response.json()
            logger.info(f"Stats retrieved successfully: {data}")

            return {
                "success": True,
                "stats": {
                    "total_memories": data.get("total_memories", 0),
                    "total_apps": data.get("total_apps", 0),
                    "categories": [],  # Would need additional API call
                    "recent_activity": {
                        "last_created": datetime.now().isoformat(),
                        "last_accessed": datetime.now().isoformat(),
                    },
                    "apps": data.get("apps", []),
                },
                "debug_response": data,  # Include full response for debugging
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Status Error in get_stats: {e}")
            logger.error(f"Response body: {e.response.text}")
            # Return default stats on error with error details
            return {
                "success": False,
                "error": f"Stats API error: {e.response.status_code}",
                "stats": {
                    "total_memories": 0,
                    "total_apps": 0,
                    "categories": [],
                    "recent_activity": {
                        "last_created": datetime.now().isoformat(),
                        "last_accessed": datetime.now().isoformat(),
                    },
                },
            }
        except Exception as e:
            logger.error(f"Unexpected error in get_stats: {e}")
            # Return default stats on error
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "stats": {
                    "total_memories": 0,
                    "total_apps": 0,
                    "categories": [],
                    "recent_activity": {
                        "last_created": datetime.now().isoformat(),
                        "last_accessed": datetime.now().isoformat(),
                    },
                },
            }

    async def health_check(self) -> dict[str, Any]:
        """Check health of backend services"""
        services = {}

        try:
            response = await self.openmemory_client.get("/health")
            services["openmemory_mcp"] = (
                "healthy" if response.status_code == 200 else "unhealthy"
            )
        except Exception:
            services["openmemory_mcp"] = "unhealthy"

        # Neo4j would need separate check - for now assume healthy if OpenMemory is healthy
        services["neo4j"] = (
            "healthy" if services["openmemory_mcp"] == "healthy" else "unknown"
        )

        return {
            "status": "healthy"
            if all(s == "healthy" for s in services.values())
            else "degraded",
            "services": services,
            "timestamp": datetime.now().isoformat(),
        }

    async def close(self):
        """Close HTTP clients properly"""
        try:
            await self.openmemory_client.aclose()
            logger.info("HTTP clients closed successfully")
        except Exception as e:
            logger.error(f"Error closing HTTP clients: {e}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


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
    category: str | None = None,
    api_key: str = Depends(verify_api_key),
):
    """List all memories for a user"""
    return await memory_client.list_memories(user_id)


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


@app.get("/memories/stats")
async def get_memory_stats(
    user_id: str = "chatgpt_user", api_key: str = Depends(verify_api_key)
):
    """Get memory statistics for a user"""
    return await memory_client.get_stats(user_id)


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
