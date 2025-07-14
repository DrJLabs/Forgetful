#!/bin/bash
# Modified Standard mem0 MCP Server Startup Script
# Uses your existing setup but provides standard SSE endpoint

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MCP_PORT=8081
MEM0_API_URL="http://localhost:8000"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] ℹ️${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌${NC} $1"
}

# Check if required services are running
check_services() {
    log "Checking required services..."

    # Check mem0 API
    if ! curl -s -f "$MEM0_API_URL/health" >/dev/null 2>&1; then
        log_error "mem0 API is not running at $MEM0_API_URL"
        log_error "Please start mem0 services: docker-compose up -d mem0 postgres-mem0 neo4j-mem0"
        exit 1
    fi

    # Check openmemory-mcp container
    if ! docker ps | grep -q "openmemory-mcp"; then
        log_error "openmemory-mcp container is not running"
        log_error "Please start: docker-compose up -d openmemory-mcp"
        exit 1
    fi

    log "✅ All required services are running"
}

# Create standard SSE MCP server using your existing backend
create_standard_sse_server() {
    log "Creating standard SSE MCP server using your existing backend..."

    # Create the SSE server that bridges to your existing MCP server
    cat > "$PROJECT_ROOT/standard_mem0_mcp_server.py" << 'EOF'
#!/usr/bin/env python3
"""
Standard mem0 MCP Server with SSE support
Bridges to existing openmemory-mcp backend
"""

import asyncio
import json
import os
import logging
import aiohttp
from typing import Dict, Any, List

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

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
    version="1.0.0"
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
                "openmemory": "healthy" if openmemory_healthy else "unhealthy"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
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
                                "text": {"type": "string", "description": "Text to store in memory"}
                            },
                            "required": ["text"]
                        }
                    },
                    {
                        "name": "search_memory",
                        "description": "Search for relevant memories",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query"}
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "list_memories",
                        "description": "List all stored memories",
                        "input_schema": {"type": "object", "properties": {}}
                    },
                    {
                        "name": "delete_all_memories",
                        "description": "Clear all stored memories",
                        "input_schema": {"type": "object", "properties": {}}
                    }
                ]
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
        }
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
                    "messages": [{"role": "user", "content": arguments.get("text", "")}],
                    "user_id": "drj"
                }
                async with session.post(f"{MEM0_API_URL}/memories", json=payload) as response:
                    result = await response.json()
                    return {"success": True, "result": result}

        elif tool_name == "search_memory":
            # Call mem0 search API
            async with aiohttp.ClientSession() as session:
                payload = {
                    "query": arguments.get("query", ""),
                    "user_id": "drj"
                }
                async with session.post(f"{MEM0_API_URL}/search", json=payload) as response:
                    result = await response.json()
                    return {"success": True, "result": result}

        elif tool_name == "list_memories":
            # Call mem0 list API
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{MEM0_API_URL}/memories?user_id=drj") as response:
                    result = await response.json()
                    return {"success": True, "result": result}

        elif tool_name == "delete_all_memories":
            # Call mem0 delete API
            async with aiohttp.ClientSession() as session:
                async with session.delete(f"{MEM0_API_URL}/memories?user_id=drj") as response:
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
EOF

    log "✅ Standard SSE MCP server created"
}

# Install requirements for the SSE server
install_requirements() {
    log "Installing requirements for SSE server..."

    # Create requirements file
    cat > "$PROJECT_ROOT/standard_mcp_requirements.txt" << 'EOF'
fastapi==0.104.1
uvicorn==0.24.0
aiohttp==3.8.6
python-multipart==0.0.6
EOF

    # Install using your existing mem0 venv if available, or system pip
    if [ -d "$PROJECT_ROOT/mem0/.venv" ]; then
        log_info "Using mem0 virtual environment"
        source "$PROJECT_ROOT/mem0/.venv/bin/activate"
        pip install -r "$PROJECT_ROOT/standard_mcp_requirements.txt"
    else
        log_info "Installing to system Python"
        pip install -r "$PROJECT_ROOT/standard_mcp_requirements.txt"
    fi

    log "✅ Requirements installed"
}

# Start the standard MCP server
start_mcp_server() {
    log "Starting standard mem0 MCP server..."

    # Set environment variables
    export MEM0_API_URL="$MEM0_API_URL"
    export OPENMEMORY_API_URL="http://localhost:8765"
    export HOST="0.0.0.0"
    export PORT="$MCP_PORT"

    log "🚀 Starting MCP server on port $MCP_PORT..."
    log_info "SSE Endpoint: http://localhost:$MCP_PORT/sse"
    log_info "Connected to your local mem0 API at: $MEM0_API_URL"

    # Activate virtual environment if available
    if [ -d "$PROJECT_ROOT/mem0/.venv" ]; then
        source "$PROJECT_ROOT/mem0/.venv/bin/activate"
    fi

    # Start the server
    cd "$PROJECT_ROOT"
    python standard_mem0_mcp_server.py
}

# Display configuration information
show_config_info() {
    log_info "MCP Client Configuration:"
    cat << EOF

🔧 For Cursor (mcp.json):
{
  "mem0": {
    "url": "http://localhost:$MCP_PORT/sse",
    "type": "sse"
  }
}

🔧 For Claude Desktop (claude_desktop_config.json):
{
  "mcpServers": {
    "mem0": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:$MCP_PORT/sse"]
    }
  }
}

🔧 For Windsurf:
{
  "mcpServers": {
    "mem0": {
      "serverUrl": "http://localhost:$MCP_PORT/sse"
    }
  }
}

📊 Endpoints:
- Health: http://localhost:$MCP_PORT/health
- SSE: http://localhost:$MCP_PORT/sse
- Tools: http://localhost:$MCP_PORT/tools/call

EOF
}

# Main execution
main() {
    log "🚀 Starting Modified Standard mem0 MCP Server Setup"
    echo "============================================================="
    log_info "This uses your existing mem0 setup with standard SSE endpoints"

    # Load environment variables
    if [ -f "$PROJECT_ROOT/.env" ]; then
        source "$PROJECT_ROOT/.env"
    fi

    # Step 1: Check services
    check_services

    # Step 2: Create SSE server
    create_standard_sse_server

    # Step 3: Install requirements
    install_requirements

    # Step 4: Show configuration info
    show_config_info

    # Step 5: Start MCP server
    start_mcp_server
}

# Handle script arguments
case "${1:-start}" in
    start)
        main
        ;;
    check)
        check_services
        ;;
    config)
        show_config_info
        ;;
    *)
        echo "Usage: $0 {start|check|config}"
        echo "  start  - Full startup (default)"
        echo "  check  - Check services only"
        echo "  config - Show configuration info"
        exit 1
        ;;
esac
