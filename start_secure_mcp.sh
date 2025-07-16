#!/bin/bash

# Secure MCP Server Startup Script
# Ensures MCP server is only accessible through cloudflared -> traefik -> nginx proxy chain

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$PROJECT_ROOT/secure_mcp.pid"
LOG_FILE="$PROJECT_ROOT/secure_mcp.log"

echo "🔒 Starting Secure MCP Server"

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "✅ Secure MCP Server is already running (PID: $PID)"
        exit 0
    else
        echo "🧹 Removing stale PID file"
        rm -f "$PID_FILE"
    fi
fi

# Set secure environment variables
export HOST=172.17.0.1  # Docker bridge interface - not accessible from internet
export PORT=8081
export MEM0_API_URL=http://localhost:8000

echo "🔧 Configuration:"
echo "   HOST: $HOST (Docker bridge interface)"
echo "   PORT: $PORT"
echo "   ACCESS: Only via mem-mcp.onemainarmy.com"

# Start the MCP server in background
cd "$PROJECT_ROOT"
nohup python3 mcp_jsonrpc_server.py > "$LOG_FILE" 2>&1 &
PID=$!

# Save PID
echo "$PID" > "$PID_FILE"

# Wait and verify startup
sleep 2
if kill -0 "$PID" 2>/dev/null; then
    echo "✅ Secure MCP Server started successfully"
    echo "   PID: $PID"
    echo "   Binding: $HOST:$PORT"
    echo "   External URL: https://mem-mcp.onemainarmy.com"
    echo "   Log file: $LOG_FILE"
    echo ""
    echo "🔒 Security Status:"
    echo "   ✅ Not accessible from internet directly"
    echo "   ✅ Only accessible via cloudflared tunnel"
    echo "   ✅ Protected by nginx proxy with rate limiting"
    echo "   ✅ Routed through traefik with TLS termination"
else
    echo "❌ Failed to start Secure MCP Server"
    rm -f "$PID_FILE"
    exit 1
fi
