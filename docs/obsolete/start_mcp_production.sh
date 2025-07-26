#!/bin/bash
# Production MCP Server Startup Script
# Ensures proper binding to all interfaces for Docker bridge access

set -e

echo "🚀 Starting Production MCP Server"
echo "================================="

# Kill any existing MCP server processes
echo "Stopping existing MCP server processes..."
pkill -f secure_mcp_server.py || true
pkill -f standard_mem0_mcp_server.py || true

# Wait for processes to stop
sleep 2

# Load production environment
if [ -f .env.mcp.production ]; then
    echo "Loading production environment..."
    set -a  # Automatically export all variables
    source .env.mcp.production
    set +a  # Turn off automatic export
else
    echo "❌ Production environment file not found: .env.mcp.production"
    exit 1
fi

# Override HOST to ensure binding to all interfaces
export HOST=0.0.0.0
export PORT=8081

# Verify required services are running
echo "Checking required services..."
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ mem0 API is not running on port 8000"
    echo "Start with: docker compose up -d mem0 postgres-mem0 neo4j-mem0"
    exit 1
fi

if ! docker ps | grep -q "openmemory-mcp"; then
    echo "❌ openmemory-mcp container is not running"
    echo "Start with: docker compose up -d openmemory-mcp"
    exit 1
fi

echo "✅ All required services are running"

# Start the secure MCP server
echo "Starting secure MCP server on $HOST:$PORT..."
python3 secure_mcp_server.py > mcp_server_production.log 2>&1 &
MCP_PID=$!

# Wait for server to start
sleep 3

# Verify server is running and accessible
if netstat -tlnp | grep -q "0.0.0.0:$PORT"; then
    echo "✅ MCP server is running on all interfaces (0.0.0.0:$PORT)"
else
    echo "❌ MCP server failed to bind to all interfaces"
    exit 1
fi

# Test local connectivity
if curl -s http://localhost:$PORT/health > /dev/null; then
    echo "✅ Local connectivity verified"
else
    echo "❌ Local connectivity test failed"
    exit 1
fi

# Test Docker bridge connectivity
if curl -s http://172.17.0.1:$PORT/health > /dev/null; then
    echo "✅ Docker bridge connectivity verified"
else
    echo "❌ Docker bridge connectivity test failed"
    exit 1
fi

# Test external connectivity
if curl -s https://mem-mcp.onemainarmy.com/health > /dev/null; then
    echo "✅ External connectivity verified"
else
    echo "❌ External connectivity test failed"
    exit 1
fi

echo ""
echo "🎉 Production MCP Server Started Successfully!"
echo "============================================="
echo "Process ID: $MCP_PID"
echo "Log file: mcp_server_production.log"
echo "Local URL: http://localhost:$PORT"
echo "External URL: https://mem-mcp.onemainarmy.com"
echo "API Key: $(cat mcp_production_api_key.txt)"
echo ""
echo "To stop the server: pkill -f secure_mcp_server.py"
echo "To view logs: tail -f mcp_server_production.log"
