#!/usr/bin/env python3
"""
Secure mem0 MCP Server with authentication and rate limiting
For internet-facing deployment
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, Optional

import aiohttp
import jwt
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
HOST = os.getenv("HOST", "127.0.0.1")  # Keep localhost for security
PORT = int(os.getenv("PORT", "8081"))
MEM0_API_URL = os.getenv("MEM0_API_URL", "http://localhost:8000")
OPENMEMORY_API_URL = os.getenv("OPENMEMORY_API_URL", "http://localhost:8765")

# Security configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-this")
ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS", "localhost,127.0.0.1,mem-mcp.onemainarmy.com"
).split(",")
API_KEYS = os.getenv("API_KEYS", "").split(",") if os.getenv("API_KEYS") else []

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="Secure mem0 MCP Server",
    description="Internet-facing MCP Server with authentication and rate limiting",
    version="2.0.0",
)

# Security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://mem-mcp.onemainarmy.com",
        "https://onemainarmy.com",
        "https://drjlabs.com",
        "https://chat.openai.com",
        "https://chatgpt.com",
    ],  # Restrict to trusted domains only
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security
security = HTTPBearer()


class AuthManager:
    @staticmethod
    def verify_api_key(api_key: str) -> bool:
        return api_key in API_KEYS if API_KEYS else False

    @staticmethod
    def verify_jwt(token: str) -> Optional[Dict]:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


async def verify_auth(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials

    # Try API key first
    if AuthManager.verify_api_key(token):
        return {"type": "api_key", "token": token}

    # Try JWT
    payload = AuthManager.verify_jwt(token)
    if payload:
        return {"type": "jwt", "payload": payload}

    raise HTTPException(status_code=401, detail="Invalid authentication token")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    return response


@app.get("/health")
@limiter.limit("30/minute")
async def health_check(request: Request):
    """Public health check endpoint"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{MEM0_API_URL}/health", timeout=5) as response:
                mem0_healthy = response.status == 200

        return {
            "status": "healthy" if mem0_healthy else "degraded",
            "transport": "sse",
            "version": "2.0.0",
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": "Service unavailable"},
        )


@app.get("/sse")
@limiter.limit("5/minute")
async def sse_endpoint(request: Request):
    """Public SSE endpoint for tool discovery"""

    async def event_stream():
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connection', 'status': 'connected', 'server': 'secure-mem0-mcp'})}\n\n"

            # Send available tools
            tools_info = {
                "type": "tools",
                "tools": [
                    {
                        "name": "add_memories",
                        "description": "Store new information in memory",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "text": {
                                    "type": "string",
                                    "description": "Text to store in memory",
                                },
                                "user_id": {
                                    "type": "string",
                                    "description": "User ID to associate with memory",
                                    "default": "external_user",
                                },
                            },
                            "required": ["text"],
                        },
                    },
                    {
                        "name": "search_memory",
                        "description": "Search for relevant memories",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Search query",
                                },
                                "user_id": {
                                    "type": "string",
                                    "description": "User ID to search memories for",
                                    "default": "external_user",
                                },
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "list_memories",
                        "description": "List all stored memories",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "user_id": {
                                    "type": "string",
                                    "description": "User ID to list memories for",
                                    "default": "external_user",
                                }
                            },
                        },
                    },
                ],
            }
            yield f"data: {json.dumps(tools_info)}\n\n"

            # Keep connection alive
            while True:
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"
                await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"SSE stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Stream error'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.post("/tools/call")
@limiter.limit("60/minute")
async def call_tool(request: Request, auth: dict = Depends(verify_auth)):
    """Authenticated tool calling endpoint"""
    try:
        data = await request.json()
        tool_name = data.get("name")
        arguments = data.get("arguments", {})

        # Log the request for monitoring
        logger.info(f"Tool call: {tool_name} by {auth.get('type', 'unknown')}")

        # Map tool calls to mem0 operations
        if tool_name == "add_memories":
            async with aiohttp.ClientSession() as session:
                payload = {
                    "messages": [
                        {"role": "user", "content": arguments.get("text", "")}
                    ],
                    "user_id": arguments.get("user_id", "external_user"),
                }
                async with session.post(
                    f"{MEM0_API_URL}/memories", json=payload, timeout=10
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {"success": True, "result": result}
                    else:
                        raise HTTPException(
                            status_code=500, detail="Memory service error"
                        )

        elif tool_name == "search_memory":
            async with aiohttp.ClientSession() as session:
                payload = {
                    "query": arguments.get("query", ""),
                    "user_id": arguments.get("user_id", "external_user"),
                }
                async with session.post(
                    f"{MEM0_API_URL}/search", json=payload, timeout=10
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {"success": True, "result": result}
                    else:
                        raise HTTPException(
                            status_code=500, detail="Search service error"
                        )

        elif tool_name == "list_memories":
            async with aiohttp.ClientSession() as session:
                user_id = arguments.get("user_id", "external_user")
                async with session.get(
                    f"{MEM0_API_URL}/memories?user_id={user_id}", timeout=10
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {"success": True, "result": result}
                    else:
                        raise HTTPException(
                            status_code=500, detail="List service error"
                        )

        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")

    except Exception as e:
        logger.error(f"Tool call error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Generate JWT token endpoint (for testing)
@app.post("/auth/token")
@limiter.limit("10/minute")
async def generate_token(request: Request):
    """Generate JWT token for testing (remove in production)"""
    data = await request.json()
    user_id = data.get("user_id", "test_user")

    payload = {
        "user_id": user_id,
        "exp": time.time() + 3600,  # 1 hour expiry
        "iat": time.time(),
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer"}


if __name__ == "__main__":
    logger.info(f"Starting secure mem0 MCP server on {HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
