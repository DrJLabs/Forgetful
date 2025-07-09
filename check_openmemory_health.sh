#!/bin/bash
# OpenMemory Health Check Script
# Usage: ./check_openmemory_health.sh

echo "🔍 OpenMemory Health Check"
echo "=========================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check UI
echo "1. Checking OpenMemory UI (Port 3000)..."
if curl -s http://localhost:3000 >/dev/null 2>&1; then
    echo -e "   ${GREEN}✅ UI is accessible${NC}"
    UI_STATUS="UP"
else
    echo -e "   ${RED}❌ UI is not accessible${NC}"
    UI_STATUS="DOWN"
fi

# Check OpenMemory MCP API
echo "2. Checking OpenMemory MCP API (Port 8765)..."
if curl -s http://localhost:8765/api/v1/memories/?user_id=test >/dev/null 2>&1; then
    echo -e "   ${GREEN}✅ OpenMemory MCP API is responding${NC}"
    MCP_STATUS="UP"
else
    echo -e "   ${RED}❌ OpenMemory MCP API is not responding${NC}"
    MCP_STATUS="DOWN"
fi

# Check Main Mem0 API
echo "3. Checking Main Mem0 API (Port 8000)..."
if curl -s http://localhost:8000/memories?user_id=test >/dev/null 2>&1; then
    echo -e "   ${GREEN}✅ Main Mem0 API is responding${NC}"
    MEM0_STATUS="UP"
else
    echo -e "   ${RED}❌ Main Mem0 API is not responding${NC}"
    MEM0_STATUS="DOWN"
fi

# Check Docker containers
echo "4. Checking Docker containers..."
CONTAINERS=$(docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(mem0|openmemory)" | grep -v "NAMES")
if [ -n "$CONTAINERS" ]; then
    echo -e "   ${GREEN}✅ Containers are running${NC}"
    echo "$CONTAINERS" | while read line; do
        echo "      $line"
    done
    CONTAINERS_STATUS="UP"
else
    echo -e "   ${RED}❌ Some containers are not running${NC}"
    CONTAINERS_STATUS="DOWN"
fi

# Check database connections
echo "5. Checking Database connections..."
if docker exec postgres-mem0 pg_isready -q 2>/dev/null; then
    echo -e "   ${GREEN}✅ PostgreSQL is healthy${NC}"
    DB_STATUS="UP"
else
    echo -e "   ${RED}❌ PostgreSQL is not healthy${NC}"
    DB_STATUS="DOWN"
fi

if docker exec neo4j-mem0 wget -q -O /dev/null http://localhost:7474/ 2>/dev/null; then
    echo -e "   ${GREEN}✅ Neo4j is healthy${NC}"
    GRAPH_STATUS="UP"
else
    echo -e "   ${RED}❌ Neo4j is not healthy${NC}"
    GRAPH_STATUS="DOWN"
fi

echo "=========================="
echo "📊 SUMMARY"
echo "=========================="
echo "UI Status:          $UI_STATUS"
echo "OpenMemory MCP:     $MCP_STATUS"
echo "Main Mem0 API:      $MEM0_STATUS"
echo "Containers:         $CONTAINERS_STATUS"
echo "PostgreSQL:         $DB_STATUS"
echo "Neo4j:             $GRAPH_STATUS"

# Overall health
if [ "$UI_STATUS" == "UP" ] && [ "$MEM0_STATUS" == "UP" ] && [ "$MCP_STATUS" == "UP" ]; then
    echo -e "\n${GREEN}🎉 System is HEALTHY${NC}"
    exit 0
elif [ "$UI_STATUS" == "UP" ] && [ "$MEM0_STATUS" == "UP" ]; then
    echo -e "\n${YELLOW}⚠️  System is PARTIALLY FUNCTIONAL (OpenMemory MCP down)${NC}"
    exit 1
else
    echo -e "\n${RED}🚨 System has CRITICAL ISSUES${NC}"
    exit 2
fi 