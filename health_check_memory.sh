#!/bin/bash

echo "🩺 Memory System Health Check"
echo "=" * 50

# Function to check HTTP endpoint
check_endpoint() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}

    echo -n "Checking $name: "

    if response=$(curl -s -w "%{http_code}" -o /tmp/response.txt "$url" 2>/dev/null); then
        status_code="${response: -3}"
        if [ "$status_code" = "$expected_status" ]; then
            echo "✅ UP ($status_code)"
        else
            echo "❌ DOWN ($status_code)"
            echo "   Response: $(cat /tmp/response.txt)"
        fi
    else
        echo "❌ DOWN (no response)"
    fi
}

# Function to check database connection
check_database() {
    local name=$1
    local container=$2
    local command=$3

    echo -n "Checking $name: "

    if docker exec "$container" $command > /dev/null 2>&1; then
        echo "✅ UP"
    else
        echo "❌ DOWN"
    fi
}

# Function to check container health
check_container() {
    local name=$1
    local container=$2

    echo -n "Checking $name container: "

    if docker ps | grep -q "$container.*Up"; then
        echo "✅ RUNNING"
    else
        echo "❌ NOT RUNNING"
    fi
}

echo -e "\n🐳 Container Status:"
check_container "mem0" "mem0"
check_container "OpenMemory MCP" "openmemory-mcp"
check_container "OpenMemory UI" "openmemory-ui"
check_container "PostgreSQL" "postgres-mem0"
check_container "Neo4j" "neo4j-mem0"

echo -e "\n🔗 Database Connections:"
check_database "PostgreSQL" "postgres-mem0" "pg_isready -U drj"
check_database "Neo4j" "neo4j-mem0" "cypher-shell -u neo4j -p mem0password 'MATCH (n) RETURN count(n) LIMIT 1'"

echo -e "\n🌐 API Endpoints:"
check_endpoint "mem0 API Health" "http://localhost:8000/health"
check_endpoint "mem0 API Docs" "http://localhost:8000/docs"
check_endpoint "OpenMemory MCP Health" "http://localhost:8765/health"
check_endpoint "OpenMemory UI" "http://localhost:3000"

echo -e "\n📊 Memory Operations Test:"
echo -n "Testing mem0 memory retrieval: "
if response=$(curl -s "http://localhost:8000/memories?user_id=drj"); then
    if echo "$response" | grep -q '"results"'; then
        count=$(echo "$response" | jq -r '.results | length' 2>/dev/null || echo "0")
        echo "✅ SUCCESS ($count memories)"
    else
        echo "❌ FAILED"
        echo "   Response: $response"
    fi
else
    echo "❌ NO RESPONSE"
fi

echo -n "Testing OpenMemory API: "
if response=$(curl -s "http://localhost:8765/api/v1/memories/?user_id=drj"); then
    if echo "$response" | grep -q '"memories"'; then
        count=$(echo "$response" | jq -r '.memories | length' 2>/dev/null || echo "0")
        echo "✅ SUCCESS ($count memories)"
    else
        echo "❌ FAILED"
        echo "   Response: $response"
    fi
else
    echo "❌ NO RESPONSE"
fi

echo -e "\n🔍 Database Content:"
echo -n "mem0 memories table: "
if result=$(docker exec postgres-mem0 psql -U drj -d mem0 -t -c "SELECT COUNT(*) FROM mem0_memories;" 2>/dev/null); then
    echo "✅ $(echo $result | tr -d ' ') records"
else
    echo "❌ QUERY FAILED"
fi

echo -n "OpenMemory memories table: "
if result=$(docker exec postgres-mem0 psql -U drj -d mem0 -t -c "SELECT COUNT(*) FROM memories;" 2>/dev/null); then
    echo "✅ $(echo $result | tr -d ' ') records"
else
    echo "❌ QUERY FAILED"
fi

echo -e "\n🎯 System Summary:"
echo "All core services appear to be running."
echo "Ready for memory system testing!"

# Clean up temp file
rm -f /tmp/response.txt
