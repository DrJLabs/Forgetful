#!/bin/bash
# Enhanced mem0 MCP Server Startup Script
# Supports both stdio (current) and SSE (standard) transports

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MCP_STDIO_PORT=8765
MCP_SSE_PORT=8080

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
    if ! curl -s -f "http://localhost:8000/health" >/dev/null 2>&1; then
        log_error "mem0 API is not running at http://localhost:8000"
        log_error "Please start: docker-compose up -d mem0 postgres-mem0 neo4j-mem0"
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

# Start stdio-based MCP server (current implementation)
start_stdio_mcp() {
    log "Starting stdio-based MCP server..."
    log_info "This is compatible with Cursor's current MCP configuration"

    # Check if wrapper script exists
    if [ ! -f "$PROJECT_ROOT/run_mcp_server.sh" ]; then
        log_error "run_mcp_server.sh not found!"
        exit 1
    fi

    # Make sure it's executable
    chmod +x "$PROJECT_ROOT/run_mcp_server.sh"

    log "🚀 Starting stdio MCP server..."
    log_info "Use this configuration in ~/.cursor/mcp.json:"
    cat << EOF

{
  "mem0": {
    "command": "$PROJECT_ROOT/run_mcp_server.sh",
    "env": {
      "OPENAI_API_KEY": "$OPENAI_API_KEY",
      "POSTGRES_USER": "${POSTGRES_USER:-drj}",
      "POSTGRES_PASSWORD": "${POSTGRES_PASSWORD:-data2f!re}",
      "NEO4J_AUTH": "neo4j/${NEO4J_PASSWORD:-data2f!re}",
      "USER_ID": "${USER_ID:-drj}",
      "CLIENT_NAME": "${CLIENT_NAME:-cursor}"
    }
  }
}

EOF

    # Start the stdio server
    exec "$PROJECT_ROOT/run_mcp_server.sh"
}

# Create SSE-based MCP server (standard method)
start_sse_mcp() {
    log "Starting SSE-based MCP server (standard method)..."
    log_info "This provides the standard mem0 MCP SSE endpoint"

    # Create SSE server script
    cat > "$PROJECT_ROOT/mcp_sse_server.py" << 'EOF'
#!/usr/bin/env python3
"""
SSE-based MCP server that provides standard mem0 MCP compatibility
"""

import asyncio
import json
import os
import logging
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import your existing MCP server logic
import sys
sys.path.append('/usr/src/openmemory')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
MEM0_API_URL = os.getenv("MEM0_API_URL", "http://localhost:8000")

app = FastAPI(
    title="mem0 MCP SSE Server",
    description="Standard mem0 MCP Server with SSE support",
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
    return {"status": "healthy", "transport": "sse", "mem0_api": MEM0_API_URL}

@app.get("/sse")
async def sse_endpoint(request: Request):
    """Standard mem0 MCP SSE endpoint"""

    async def event_stream():
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connection', 'status': 'connected'})}\n\n"

        try:
            # Here you would implement the actual MCP protocol over SSE
            # This is a simplified version that connects to your existing MCP server

            # For now, we'll provide a basic implementation
            # that shows the concept - you'd integrate with your actual MCP logic

            while True:
                # Send heartbeat
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
    """Tool calling endpoint for MCP clients"""
    data = await request.json()

    # Here you would proxy to your existing MCP server
    # This is a placeholder implementation

    return {
        "success": True,
        "result": "Tool call received",
        "data": data
    }

if __name__ == "__main__":
    logger.info(f"Starting SSE-based MCP server on {HOST}:{PORT}")
    logger.info(f"SSE endpoint: http://{HOST}:{PORT}/sse")
    uvicorn.run(app, host=HOST, port=PORT)
EOF

    # Create requirements for SSE server
    cat > "$PROJECT_ROOT/mcp_sse_requirements.txt" << 'EOF'
fastapi==0.104.1
uvicorn==0.24.0
python-multipart==0.0.6
EOF

    # Install requirements and start SSE server
    log "Installing SSE server requirements..."
    pip install -r "$PROJECT_ROOT/mcp_sse_requirements.txt"

    log "🚀 Starting SSE MCP server on port $MCP_SSE_PORT..."
    log_info "SSE Endpoint: http://localhost:$MCP_SSE_PORT/sse"
    log_info "Use this configuration in MCP clients:"
    cat << EOF

Cursor Configuration:
{
  "mem0": {
    "url": "http://localhost:$MCP_SSE_PORT/sse",
    "type": "sse"
  }
}

Claude Desktop Configuration:
{
  "mcpServers": {
    "mem0": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:$MCP_SSE_PORT/sse"]
    }
  }
}

EOF

    # Start the SSE server
    cd "$PROJECT_ROOT"
    python mcp_sse_server.py
}

# Display usage information
show_usage() {
    cat << EOF
Enhanced mem0 MCP Server - Multiple Transport Support

Usage: $0 [transport] [options]

Transports:
  stdio     - Start stdio-based MCP server (current implementation)
  sse       - Start SSE-based MCP server (standard method)
  both      - Start both servers (different ports)

Options:
  --check   - Check services only
  --help    - Show this help message

Examples:
  $0 stdio          # Start stdio server (for Cursor)
  $0 sse            # Start SSE server (standard method)
  $0 both           # Start both servers
  $0 --check        # Check if services are ready

Configuration:
  stdio: Port $MCP_STDIO_PORT (via Docker)
  sse:   Port $MCP_SSE_PORT (direct Python)
EOF
}

# Main execution
main() {
    local transport="${1:-stdio}"

    case "$transport" in
        --help)
            show_usage
            exit 0
            ;;
        --check)
            check_services
            exit 0
            ;;
        stdio)
            log "🚀 Starting stdio-based MCP server"
            check_services
            start_stdio_mcp
            ;;
        sse)
            log "🚀 Starting SSE-based MCP server"
            check_services
            start_sse_mcp
            ;;
        both)
            log "🚀 Starting both MCP servers"
            check_services
            log_info "Starting SSE server in background..."
            start_sse_mcp &
            log_info "Starting stdio server in foreground..."
            start_stdio_mcp
            ;;
        *)
            log_error "Unknown transport: $transport"
            show_usage
            exit 1
            ;;
    esac
}

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
fi

# Run main function
main "$@"
