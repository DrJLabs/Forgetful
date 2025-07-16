#!/usr/bin/env python3
"""
Standard mem0 MCP Server with SSE support
Bridges to existing openmemory-mcp backend
"""

import asyncio
import json
import logging
import os

import aiohttp
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
MEM0_API_URL = os.getenv("MEM0_API_URL", "http://localhost:8000")
OPENMEMORY_API_URL = os.getenv("OPENMEMORY_API_URL", "http://localhost:8765")

app = FastAPI(
    title="mem0 MCP SSE Server",
    description="Standard mem0 MCP Server with SSE support - bridges to local mem0 instance",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check mem0 API
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{MEM0_API_URL}/health") as response:
                mem0_healthy = response.status == 200

        # Check openmemory API
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OPENMEMORY_API_URL}/health") as response:
                openmemory_healthy = response.status == 200

        return {
            "status": "healthy" if mem0_healthy and openmemory_healthy else "degraded",
            "transport": "sse",
            "mem0_api": MEM0_API_URL,
            "openmemory_api": OPENMEMORY_API_URL,
            "services": {
                "mem0": "healthy" if mem0_healthy else "unhealthy",
                "openmemory": "healthy" if openmemory_healthy else "unhealthy",
            },
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503, content={"status": "unhealthy", "error": str(e)}
        )


@app.get("/sse")
async def sse_endpoint(request: Request):
    """Standard mem0 MCP SSE endpoint"""

    async def event_stream():
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connection', 'status': 'connected', 'server': 'mem0-mcp'})}\n\n"

            # Send available tools information
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
                                }
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
                                }
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "list_memories",
                        "description": "List all stored memories",
                        "input_schema": {"type": "object", "properties": {}},
                    },
                    {
                        "name": "delete_all_memories",
                        "description": "Clear all stored memories",
                        "input_schema": {"type": "object", "properties": {}},
                    },
                ],
            }
            yield f"data: {json.dumps(tools_info)}\n\n"

            # Keep connection alive with periodic heartbeats
            while True:
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': str(asyncio.get_event_loop().time())})}\n\n"
                await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"SSE stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

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
async def call_tool(request: Request):
    """Tool calling endpoint - proxies to your existing MCP server"""
    try:
        data = await request.json()
        tool_name = data.get("name")
        arguments = data.get("arguments", {})

        # Map tool calls to your existing memory operations
        if tool_name == "add_memories":
            # Call mem0 API directly
            async with aiohttp.ClientSession() as session:
                payload = {
                    "messages": [
                        {"role": "user", "content": arguments.get("text", "")}
                    ],
                    "user_id": "drj",
                }
                async with session.post(
                    f"{MEM0_API_URL}/memories", json=payload
                ) as response:
                    result = await response.json()
                    return {"success": True, "result": result}

        elif tool_name == "search_memory":
            # Call mem0 search API
            async with aiohttp.ClientSession() as session:
                payload = {"query": arguments.get("query", ""), "user_id": "drj"}
                async with session.post(
                    f"{MEM0_API_URL}/search", json=payload
                ) as response:
                    result = await response.json()
                    return {"success": True, "result": result}

        elif tool_name == "list_memories":
            # Call mem0 list API
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{MEM0_API_URL}/memories?user_id=drj"
                ) as response:
                    result = await response.json()
                    return {"success": True, "result": result}

        elif tool_name == "delete_all_memories":
            # Call mem0 delete API
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{MEM0_API_URL}/memories?user_id=drj"
                ) as response:
                    result = await response.json()
                    return {"success": True, "result": result}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")

    except Exception as e:
        logger.error(f"Tool call error: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    logger.info(f"Starting standard mem0 MCP server on {HOST}:{PORT}")
    logger.info(f"SSE endpoint: http://{HOST}:{PORT}/sse")
    logger.info(f"Connecting to mem0 API at: {MEM0_API_URL}")
    logger.info(f"Connecting to openmemory API at: {OPENMEMORY_API_URL}")
    uvicorn.run(app, host=HOST, port=PORT)
