#!/bin/bash

# BMad Service Validation Shell Script
# Validates that mem0 and Context7 MCP servers are accessible before BMad operations

set -e

echo "🔍 BMad Service Validation"
echo "========================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Service URLs
MEM0_URL="http://localhost:8000"
CONTEXT7_URL="http://localhost:8765"

# Function to check if a service is accessible
check_service() {
    local service_name=$1
    local url=$2
    local endpoint=$3
    
    echo -n "  Checking ${service_name}... "
    
    if curl -s -f --connect-timeout 5 "$endpoint" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Accessible${NC}"
        return 0
    else
        echo -e "${RED}❌ Not accessible${NC}"
        return 1
    fi
}

# Check mem0 service
echo "📁 mem0 Memory System:"
MEM0_STATUS=0
check_service "mem0 API" "$MEM0_URL" "${MEM0_URL}/docs" || MEM0_STATUS=1

# Check Context7 service
echo "📚 Context7 MCP Server:"
CONTEXT7_STATUS=0
check_service "Context7 MCP" "$CONTEXT7_URL" "${CONTEXT7_URL}/api/v1/config/" || CONTEXT7_STATUS=1

echo ""
echo "🎯 Overall Status:"

if [ $MEM0_STATUS -eq 0 ] && [ $CONTEXT7_STATUS -eq 0 ]; then
    echo -e "${GREEN}✅ All services accessible - BMad operations can proceed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some services not accessible - BMad operations should not proceed${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  Required Actions:${NC}"
    
    if [ $MEM0_STATUS -ne 0 ]; then
        echo "  🚀 Start mem0 services:"
        echo "     docker-compose up -d mem0 postgres-mem0 neo4j-mem0"
    fi
    
    if [ $CONTEXT7_STATUS -ne 0 ]; then
        echo "  🚀 Start Context7 MCP server:"
        echo "     docker-compose up -d openmemory-mcp"
    fi
    
    echo ""
    echo "  🔄 Then run this script again to verify services are ready."
    exit 1
fi 
