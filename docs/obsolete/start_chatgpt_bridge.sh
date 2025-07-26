#!/bin/bash

# Start ChatGPT MCP Bridge Service
# This script manages the mcp_jsonrpc_server.py that ChatGPT uses

set -e

PROJECT_ROOT="/home/drj/projects/mem0-stack"
PID_FILE="$PROJECT_ROOT/chatgpt_bridge.pid"
LOG_FILE="$PROJECT_ROOT/chatgpt_bridge.log"

cd "$PROJECT_ROOT"

# Function to start the bridge
start_bridge() {
    echo "🚀 Starting ChatGPT MCP Bridge..."

    # Check if already running
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "✅ ChatGPT MCP Bridge is already running (PID: $PID)"
            return 0
        else
            echo "🧹 Removing stale PID file..."
            rm -f "$PID_FILE"
        fi
    fi

    # Set environment variables
    export MEM0_API_URL="http://localhost:8000"
    export HOST="0.0.0.0"
    export PORT="8081"

    # Start the bridge in background
    nohup python3 mcp_jsonrpc_server.py > "$LOG_FILE" 2>&1 &
    PID=$!

    # Save PID
    echo "$PID" > "$PID_FILE"

    # Wait a moment and check if it started successfully
    sleep 2
    if kill -0 "$PID" 2>/dev/null; then
        echo "✅ ChatGPT MCP Bridge started successfully (PID: $PID)"
        echo "📋 Listening on: http://localhost:8081"
        echo "🌐 External URL: https://mem-mcp.onemainarmy.com"
        echo "📄 Log file: $LOG_FILE"
        return 0
    else
        echo "❌ Failed to start ChatGPT MCP Bridge"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Function to stop the bridge
stop_bridge() {
    echo "🛑 Stopping ChatGPT MCP Bridge..."

    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            rm -f "$PID_FILE"
            echo "✅ ChatGPT MCP Bridge stopped"
        else
            echo "⚠️  Bridge was not running"
            rm -f "$PID_FILE"
        fi
    else
        echo "⚠️  No PID file found"
    fi
}

# Function to check status
check_status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "✅ ChatGPT MCP Bridge is running (PID: $PID)"
            echo "🔗 Testing endpoint..."
            if curl -s http://localhost:8081/health > /dev/null 2>&1; then
                echo "✅ Local endpoint responding"
            else
                echo "⚠️  Local endpoint not responding"
            fi

            if curl -s https://mem-mcp.onemainarmy.com/health > /dev/null 2>&1; then
                echo "✅ External endpoint responding"
            else
                echo "⚠️  External endpoint not responding"
            fi
            return 0
        else
            echo "❌ ChatGPT MCP Bridge is not running"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        echo "❌ ChatGPT MCP Bridge is not running"
        return 1
    fi
}

# Function to restart the bridge
restart_bridge() {
    stop_bridge
    sleep 1
    start_bridge
}

# Function to show logs
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo "📄 ChatGPT MCP Bridge logs:"
        tail -f "$LOG_FILE"
    else
        echo "❌ No log file found"
    fi
}

# Main script logic
case "${1:-start}" in
    start)
        start_bridge
        ;;
    stop)
        stop_bridge
        ;;
    restart)
        restart_bridge
        ;;
    status)
        check_status
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the ChatGPT MCP Bridge"
        echo "  stop    - Stop the ChatGPT MCP Bridge"
        echo "  restart - Restart the ChatGPT MCP Bridge"
        echo "  status  - Check if the bridge is running"
        echo "  logs    - Show bridge logs"
        exit 1
        ;;
esac
