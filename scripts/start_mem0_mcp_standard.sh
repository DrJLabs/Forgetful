#!/bin/bash
# Standard mem0 MCP Server Startup Script
# This script starts the standard mem0 MCP server pointing to your local mem0 instance

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
MCP_PORT=8080
MEM0_API_URL="http://localhost:8000"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
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

    # Check PostgreSQL
    if ! docker exec postgres-mem0 pg_isready -U ${POSTGRES_USER:-drj} >/dev/null 2>&1; then
        log_error "PostgreSQL is not ready"
        exit 1
    fi

    # Check Neo4j
    if ! docker exec neo4j-mem0 wget -q -O /dev/null http://localhost:7474/ >/dev/null 2>&1; then
        log_error "Neo4j is not ready"
        exit 1
    fi

    log "✅ All required services are running"
}

# Clone and setup standard mem0 MCP server
setup_standard_mcp() {
    log "Setting up standard mem0 MCP server..."

    cd "$PROJECT_ROOT"

    # Clone the standard mem0 MCP repository if not exists
    if [ ! -d "mem0-mcp-standard" ]; then
        log "Cloning standard mem0 MCP repository..."
        git clone https://github.com/mem0ai/mem0-mcp.git mem0-mcp-standard
    fi

    cd mem0-mcp-standard

    # Create virtual environment if not exists
    if [ ! -d "venv" ]; then
        log "Creating virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment and install dependencies
    source venv/bin/activate
    pip install -r requirements.txt

    log "✅ Standard mem0 MCP server setup complete"
}

# Create configuration file for local mem0 instance
create_local_config() {
    log "Creating configuration for local mem0 instance..."

    # Create .env file pointing to local services
    cat > "$PROJECT_ROOT/mem0-mcp-standard/.env" << EOF
# Local mem0 instance configuration
MEM0_API_URL=http://localhost:8000
MCP_PORT=8080

# Database configuration (pointing to local instances)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mem0
POSTGRES_USER=${POSTGRES_USER:-drj}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-data2f!re}

NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=${NEO4J_PASSWORD:-data2f!re}

# OpenAI configuration
OPENAI_API_KEY=${OPENAI_API_KEY}

# MCP Server configuration
HOST=0.0.0.0
PORT=8080
EOF

    log "✅ Local configuration created"
}

# Start the standard MCP server
start_mcp_server() {
    log "Starting standard mem0 MCP server..."

    cd "$PROJECT_ROOT/mem0-mcp-standard"
    source venv/bin/activate

    # Start the MCP server
    log "🚀 Starting MCP server on port $MCP_PORT..."
    log "SSE Endpoint will be available at: http://localhost:$MCP_PORT/sse"

    # Run the server with proper configuration
    python main.py
}

# Main execution
main() {
    log "🚀 Starting Standard mem0 MCP Server Setup"
    echo "==============================================="

    # Load environment variables
    if [ -f "$PROJECT_ROOT/.env" ]; then
        source "$PROJECT_ROOT/.env"
    fi

    # Step 1: Check services
    check_services

    # Step 2: Setup standard MCP server
    setup_standard_mcp

    # Step 3: Create local configuration
    create_local_config

    # Step 4: Start MCP server
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
    setup)
        setup_standard_mcp
        create_local_config
        ;;
    *)
        echo "Usage: $0 {start|check|setup}"
        echo "  start  - Full startup (default)"
        echo "  check  - Check services only"
        echo "  setup  - Setup only (no start)"
        exit 1
        ;;
esac
